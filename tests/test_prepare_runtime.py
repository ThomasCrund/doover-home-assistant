from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT_PATH = (
    Path(__file__).parents[1]
    / "doover_device"
    / "rootfs"
    / "usr"
    / "local"
    / "bin"
    / "prepare-doover-runtime"
)


class PrepareRuntimeTests(unittest.TestCase):
    def test_logs_in_through_stdin_and_pulls_pinned_images(self):
        with tempfile.TemporaryDirectory() as directory:
            test_dir = Path(directory)
            options_path = test_dir / "options.json"
            docker_log = test_dir / "docker.log"
            secret_log = test_dir / "secret.log"
            options_path.write_text(
                json.dumps(
                    {
                        "dockerhub_username": "doover-device",
                        "dockerhub_token": "registry-secret",
                    }
                ),
                encoding="utf-8",
            )
            docker_bin = test_dir / "docker"
            docker_bin.write_text(
                """#!/bin/sh
printf '%s\\n' "$*" >> "${DOCKER_LOG}"
case " $* " in
    *" login "*) IFS= read -r secret; printf '%s' "${secret}" > "${SECRET_LOG}" ;;
esac
""",
                encoding="utf-8",
            )
            docker_bin.chmod(0o755)

            environment = os.environ.copy()
            environment.update(
                {
                    "DOCKER_BIN": str(docker_bin),
                    "DOCKER_LOG": str(docker_log),
                    "OPTIONS_PATH": str(options_path),
                    "SECRET_LOG": str(secret_log),
                }
            )
            result = subprocess.run(
                [str(SCRIPT_PATH)],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            calls = docker_log.read_text(encoding="utf-8")
            self.assertIn("login --username doover-device --password-stdin", calls)
            self.assertIn("pull spaneng/doover-device-agent:main@sha256:", calls)
            self.assertIn("pull spaneng/doover-app-controller:main@sha256:", calls)
            self.assertIn("doover-home-assistant/device-agent:runtime", calls)
            self.assertIn("doover-home-assistant/app-controller:runtime", calls)
            self.assertEqual(secret_log.read_text(encoding="utf-8"), "registry-secret")
            self.assertNotIn("registry-secret", calls + result.stdout + result.stderr)

            config_dir = Path(calls.split("--config ", 1)[1].split(" ", 1)[0])
            self.assertFalse(config_dir.exists())

    def test_rejects_missing_registry_credentials_before_docker_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            test_dir = Path(directory)
            options_path = test_dir / "options.json"
            docker_marker = test_dir / "docker-ran"
            options_path.write_text(
                json.dumps(
                    {
                        "dockerhub_username": "doover-device",
                        "dockerhub_token": "",
                    }
                ),
                encoding="utf-8",
            )
            docker_bin = test_dir / "docker"
            docker_bin.write_text(
                f"#!/bin/sh\ntouch '{docker_marker}'\n",
                encoding="utf-8",
            )
            docker_bin.chmod(0o755)

            environment = os.environ.copy()
            environment.update(
                {
                    "DOCKER_BIN": str(docker_bin),
                    "OPTIONS_PATH": str(options_path),
                }
            )
            result = subprocess.run(
                [str(SCRIPT_PATH)],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("dockerhub_token is required", result.stdout)
            self.assertFalse(docker_marker.exists())


if __name__ == "__main__":
    unittest.main()
