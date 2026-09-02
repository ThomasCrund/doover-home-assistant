def main() -> None:
    from pydoover.docker import run_app

    from .application import HomeAssistantBridgeApplication

    run_app(HomeAssistantBridgeApplication())
