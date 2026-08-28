from __future__ import annotations

import asyncio
import importlib.util
import logging
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "doover_device"
    / "rootfs"
    / "usr"
    / "local"
    / "bin"
    / "doover-app-run-home-assistant"
)


class UpstreamController:
    async def docker_system_prune(self):
        raise AssertionError("the upstream host-wide prune must not run")


class ControllerWrapperTests(unittest.TestCase):
    def test_overrides_host_wide_docker_pruning(self):
        controller_module = ModuleType("doover_app_controller")
        controller_module.DooverAppControllerApplication = UpstreamController
        docker_module = ModuleType("pydoover.docker")
        docker_module.run_app = lambda _app: None
        pydoover_module = ModuleType("pydoover")

        previous_modules = {
            name: sys.modules.get(name)
            for name in ("doover_app_controller", "pydoover", "pydoover.docker")
        }
        sys.modules["doover_app_controller"] = controller_module
        sys.modules["pydoover"] = pydoover_module
        sys.modules["pydoover.docker"] = docker_module
        try:
            spec = importlib.util.spec_from_loader(
                "controller_wrapper",
                SourceFileLoader("controller_wrapper", str(MODULE_PATH)),
            )
            assert spec and spec.loader
            wrapper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(wrapper)
        finally:
            for name, previous in previous_modules.items():
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous

        self.assertIsNot(
            wrapper.HomeAssistantAppController.docker_system_prune,
            UpstreamController.docker_system_prune,
        )
        with self.assertLogs(level=logging.INFO) as logs:
            asyncio.run(wrapper.HomeAssistantAppController().docker_system_prune())
        self.assertIn("disabled on Home Assistant", " ".join(logs.output))


if __name__ == "__main__":
    unittest.main()
