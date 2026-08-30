from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "doover_device"
    / "rootfs"
    / "usr"
    / "local"
    / "bin"
    / "configure-doover"
)
SPEC = importlib.util.spec_from_loader(
    "configure_doover", SourceFileLoader("configure_doover", str(MODULE_PATH))
)
assert SPEC and SPEC.loader
configure_doover = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(configure_doover)


def valid_options(**changes):
    options = {
        "dockerhub_username": "doover-device",
        "dockerhub_token": "registry-token",
        "agent_id": "123456789",
        "organisation_id": "987654321",
        "auth_token": "device-token-a",
        "client_id": "",
        "client_secret": "",
        "data_api": "https://data.doover.com/api",
        "data_wss": "wss://data.doover.com/gateway",
        "data_static_ips": "",
        "debug": False,
    }
    options.update(changes)
    return options


class ConfigureDooverTests(unittest.TestCase):
    def build(self, options=None, existing=None):
        return configure_doover.build_config(options or valid_options(), existing or {})

    def test_builds_provisioned_device_config(self):
        config = self.build()

        self.assertEqual(config["agent_id"], "123456789")
        self.assertEqual(config["organisation_id"], "987654321")
        self.assertEqual(config["auth_token"], "device-token-a")
        self.assertEqual(config["data_api"], "https://data.doover.com/api")
        self.assertEqual(config["data_wss"], "wss://data.doover.com/gateway")
        self.assertEqual(config["port"], 50051)
        self.assertFalse(config["run_web_server"])
        self.assertNotIn("data_static_ips", config)
        self.assertEqual(
            config[configure_doover.CONFIGURED_AUTH_DIGEST_KEY],
            configure_doover._configured_auth_digest("device-token-a", "", ""),
        )

    def test_accepts_oauth_credentials_without_device_token(self):
        config = self.build(
            valid_options(
                auth_token="",
                client_id="oauth-client",
                client_secret="oauth-secret",
            )
        )

        self.assertEqual(config["auth_token"], "")
        self.assertEqual(config["client_id"], "oauth-client")
        self.assertEqual(config["client_secret"], "oauth-secret")

    def test_preserves_a_rotated_token_when_the_option_did_not_change(self):
        configured_token = "device-token-a"
        config = self.build(
            valid_options(auth_token=configured_token),
            {
                "auth_token": "rotated-device-token",
                configure_doover.CONFIGURED_AUTH_DIGEST_KEY: (
                    configure_doover._configured_auth_digest(configured_token, "", "")
                ),
            },
        )

        self.assertEqual(config["auth_token"], "rotated-device-token")

    def test_uses_a_new_token_when_the_option_changes(self):
        config = self.build(
            valid_options(auth_token="device-token-b"),
            {
                "auth_token": "rotated-device-token",
                configure_doover.CONFIGURED_AUTH_DIGEST_KEY: (
                    configure_doover._configured_auth_digest("device-token-a", "", "")
                ),
            },
        )

        self.assertEqual(config["auth_token"], "device-token-b")

    def test_preserves_an_oauth_token_until_the_client_credentials_change(self):
        original_options = valid_options(
            auth_token="",
            client_id="oauth-client",
            client_secret="oauth-secret-a",
        )
        existing = {
            "auth_token": "oauth-access-token",
            configure_doover.CONFIGURED_AUTH_DIGEST_KEY: (
                configure_doover._configured_auth_digest(
                    "", "oauth-client", "oauth-secret-a"
                )
            ),
        }

        unchanged = self.build(original_options, existing)
        changed = self.build(
            valid_options(
                auth_token="",
                client_id="oauth-client",
                client_secret="oauth-secret-b",
            ),
            existing,
        )

        self.assertEqual(unchanged["auth_token"], "oauth-access-token")
        self.assertEqual(changed["auth_token"], "")

    def test_rejects_incomplete_credentials(self):
        invalid_options = [
            valid_options(auth_token="", client_id="", client_secret=""),
            valid_options(auth_token="", client_id="oauth-client", client_secret=""),
            valid_options(auth_token="", client_id="", client_secret="oauth-secret"),
        ]

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(configure_doover.ConfigurationError):
                    self.build(options)

    def test_rejects_invalid_ids_endpoints_and_static_ips(self):
        invalid_options = [
            valid_options(agent_id="pi-one"),
            valid_options(organisation_id=""),
            valid_options(data_api="ftp://data.doover.com"),
            valid_options(data_wss="https://data.doover.com/gateway"),
            valid_options(data_static_ips="15.197.66.194 not-an-ip"),
            valid_options(debug="false"),
        ]

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(configure_doover.ConfigurationError):
                    self.build(options)

    def test_parses_static_ip_list(self):
        config = self.build(
            valid_options(data_static_ips="15.197.66.194, 99.83.217.163")
        )

        self.assertEqual(
            config["data_static_ips"], ["15.197.66.194", "99.83.217.163"]
        )


if __name__ == "__main__":
    unittest.main()
