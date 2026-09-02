from __future__ import annotations

import asyncio
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


APP_SRC = Path(__file__).parents[1] / "home_assistant_bridge" / "src"
sys.path.insert(0, str(APP_SRC))

from home_assistant_bridge import bridge_client  # noqa: E402
from home_assistant_bridge.model import reading_value, specs_from_config  # noqa: E402


class Value:
    def __init__(self, value):
        self.value = value


def entity(entity_id, display_name="", precision=2, units=""):
    return SimpleNamespace(
        entity_id=Value(entity_id),
        display_name=Value(display_name),
        precision=Value(precision),
        units=Value(units),
    )


def config(**groups):
    defaults = {
        "numeric_sensors": [],
        "text_sensors": [],
        "binary_sensors": [],
        "lights": [],
    }
    defaults.update(groups)
    return SimpleNamespace(
        **{name: SimpleNamespace(elements=value) for name, value in defaults.items()}
    )


class ClientHandler(BaseHTTPRequestHandler):
    received = []

    def log_message(self, *_args):
        pass

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.received.append((self.path, self.headers["Authorization"], body))
        response = json.dumps(
            {"entities": [], "missing": body.get("entity_ids", [])}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


class BridgeAppCoreTests(unittest.TestCase):
    def test_builds_typed_unique_entity_specs(self):
        specs = specs_from_config(
            config(
                numeric_sensors=[entity("sensor.temperature", "Temperature", 1, "°C")],
                binary_sensors=[entity("binary_sensor.front_door")],
                lights=[entity("light.lounge", "Lounge")],
            )
        )

        self.assertEqual([item.kind for item in specs], ["number", "boolean", "light"])
        self.assertEqual(specs[0].value_tag, "sensor_temperature_value")
        self.assertEqual(specs[0].precision, 1)
        with self.assertRaises(ValueError):
            specs_from_config(
                config(
                    numeric_sensors=[entity("sensor.temperature")],
                    text_sensors=[entity("sensor.temperature")],
                )
            )

    def test_parses_home_assistant_states_without_publishing_invalid_numbers(self):
        number = specs_from_config(
            config(numeric_sensors=[entity("sensor.temperature")])
        )[0]
        light = specs_from_config(config(lights=[entity("light.lounge")]))[0]

        self.assertEqual(reading_value(number, "21.50"), (True, 21.5))
        self.assertEqual(reading_value(number, "unavailable"), (False, None))
        self.assertEqual(reading_value(number, "not-a-number"), (False, None))
        self.assertEqual(reading_value(light, "on"), (True, True))
        self.assertEqual(reading_value(light, "off"), (True, False))

    def test_client_posts_credential_and_selected_ids_to_loopback_broker(self):
        ClientHandler.received = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), ClientHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}"
        token = "bridge-credential-with-more-than-32-characters"
        try:
            with mock.patch.object(bridge_client, "BRIDGE_URL", url):
                client = bridge_client.BridgeClient(token)
                asyncio.run(client.query_entities(["sensor.temperature"]))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

        self.assertEqual(
            ClientHandler.received,
            [
                (
                    "/v1/entities/query",
                    f"Bearer {token}",
                    {"entity_ids": ["sensor.temperature"]},
                )
            ],
        )

    def test_client_rejects_short_credentials(self):
        with self.assertRaises(ValueError):
            bridge_client.BridgeClient("short")


if __name__ == "__main__":
    unittest.main()
