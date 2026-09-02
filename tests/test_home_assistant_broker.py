from __future__ import annotations

import importlib.util
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "doover_device"
    / "rootfs"
    / "usr"
    / "local"
    / "bin"
    / "home-assistant-bridge-broker"
)
SPEC = importlib.util.spec_from_loader(
    "home_assistant_bridge_broker",
    SourceFileLoader("home_assistant_bridge_broker", str(MODULE_PATH)),
)
assert SPEC and SPEC.loader
broker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(broker)


class FakeHomeAssistantHandler(BaseHTTPRequestHandler):
    states = [
        {
            "entity_id": "sensor.lounge_temperature",
            "state": "21.5",
            "last_changed": "2026-09-02T00:00:00+00:00",
            "last_updated": "2026-09-02T00:00:01+00:00",
            "attributes": {
                "friendly_name": "Lounge Temperature",
                "unit_of_measurement": "°C",
                "secret_attribute": "must-not-leave-broker",
            },
        },
        {
            "entity_id": "light.lounge",
            "state": "off",
            "last_changed": "2026-09-02T00:00:00+00:00",
            "last_updated": "2026-09-02T00:00:01+00:00",
            "attributes": {"friendly_name": "Lounge Light", "brightness": 200},
        },
    ]
    commands: list[tuple[str, dict]] = []

    def log_message(self, *_args):
        pass

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.headers.get("Authorization") != "Bearer supervisor-secret":
            self._json(401, {"error": "unauthorized"})
            return
        if self.path == "/api/states":
            self._json(200, self.states)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        self.commands.append((self.path, payload))
        self._json(200, [])


class RunningServer:
    def __init__(self, server):
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self.server

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class HomeAssistantBrokerTests(unittest.TestCase):
    token = "bridge-credential-with-more-than-32-characters"

    def setUp(self):
        FakeHomeAssistantHandler.commands = []
        self.ha_server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHomeAssistantHandler)
        ha_port = self.ha_server.server_address[1]
        ha_client = broker.HomeAssistantClient(
            f"http://127.0.0.1:{ha_port}/api", "supervisor-secret"
        )
        self.bridge_server = broker.BridgeServer(
            ("127.0.0.1", 0), self.token, ha_client
        )
        self.ha_context = RunningServer(self.ha_server)
        self.bridge_context = RunningServer(self.bridge_server)
        self.ha_context.__enter__()
        self.bridge_context.__enter__()
        self.bridge_url = f"http://127.0.0.1:{self.bridge_server.server_address[1]}"

    def tearDown(self):
        self.bridge_context.__exit__()
        self.ha_context.__exit__()

    def post(self, path, payload, token=None):
        request = urllib.request.Request(
            f"{self.bridge_url}{path}",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {token if token is not None else self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read())

    def assert_http_error(self, expected_status, path, payload, token=None):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.post(path, payload, token)
        self.assertEqual(raised.exception.code, expected_status)
        raised.exception.close()

    def test_returns_only_requested_entities_and_safe_attributes(self):
        status, response = self.post(
            "/v1/entities/query",
            {"entity_ids": ["sensor.lounge_temperature", "light.lounge"]},
        )

        self.assertEqual(status, 200)
        self.assertEqual(
            [item["entity_id"] for item in response["entities"]],
            ["sensor.lounge_temperature", "light.lounge"],
        )
        self.assertNotIn("secret_attribute", response["entities"][0]["attributes"])
        self.assertNotIn("brightness", response["entities"][1]["attributes"])

    def test_translates_only_supported_light_commands(self):
        _status, response = self.post(
            "/v1/commands", {"entity_id": "light.lounge", "command": "turn_on"}
        )

        self.assertEqual(response, {"entity_id": "light.lounge", "command": "turn_on"})
        self.assertEqual(
            FakeHomeAssistantHandler.commands,
            [("/api/services/light/turn_on", {"entity_id": "light.lounge"})],
        )
        self.assert_http_error(
            403,
            "/v1/commands",
            {"entity_id": "light.lounge", "command": "remove_config_entry"},
        )
        self.assert_http_error(
            403,
            "/v1/commands",
            {"entity_id": "sensor.lounge_temperature", "command": "turn_on"},
        )

    def test_rejects_wrong_credential_and_unsupported_entity_domain(self):
        self.assert_http_error(
            401,
            "/v1/entities/query",
            {"entity_ids": ["sensor.lounge_temperature"]},
            token="wrong-token",
        )
        self.assert_http_error(
            400,
            "/v1/entities/query",
            {"entity_ids": ["automation.open_the_door"]},
        )
        self.assert_http_error(
            400,
            "/v1/entities/query",
            {"entity_ids": ["sensor.lounge_temperature"] * 101},
        )

    def test_validates_bridge_configuration(self):
        self.assertFalse(broker.bridge_is_enabled({}))
        self.assertTrue(
            broker.bridge_is_enabled({"homeassistant_bridge_enabled": True})
        )
        with self.assertRaises(RuntimeError):
            broker.validate_bridge_token("short")


if __name__ == "__main__":
    unittest.main()
