# Doover Home Assistant Bridge

This context connects a Home Assistant host to Doover without giving a Doover application unrestricted access to Home Assistant.

## Language

**Bridge broker**:
The privileged local adapter in the Home Assistant app. It owns the Home Assistant Supervisor credential and exposes a restricted loopback API.
_Avoid_: Proxy, gateway

**Bridge app**:
The Doover device application that mirrors selected Home Assistant entities into Doover and sends restricted commands to the bridge broker.
_Avoid_: Integration, connector

**Exposed entity**:
A Home Assistant entity selected in the bridge app configuration for display or control in Doover.
_Avoid_: Device, sensor mapping

**Entity reading**:
The current state and safe display attributes of an exposed entity.
_Avoid_: Telemetry packet, snapshot

**Bridge credential**:
A shared secret that authorizes the bridge app to call the local bridge broker. It cannot authenticate directly to Home Assistant.
_Avoid_: Home Assistant token, API key
