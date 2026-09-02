# Changelog

## 0.3.0

- Add a restricted local Home Assistant broker for Doover device apps.
- Add configuration for a scoped bridge credential.
- Support selected sensor readings, binary sensors, and light controls through the Home Assistant Bridge Doover app.

## 0.2.1

- Use `https://data.doover.com/api` and `wss://data.doover.com/gateway` as the default Doover endpoints.

## 0.2.0

- Accept Docker Hub credentials in the Home Assistant configuration.
- Build the installable app from a public bootstrap image, then pull the private Doover services by pinned digest at startup.
- Run the Device Agent and App Controller as managed sibling containers and remove their temporary Docker login state.

## 0.1.0

- Run the Doover Device Agent and App Controller in one Home Assistant app.
- Accept Raspberry Pi provisioning IDs, endpoints, a device token, or OAuth client credentials.
- Preserve Device Agent token rotations across app restarts.
- Enable remote Doover app deployments through the host Docker API.
- Restrict the Device Agent API to host loopback and disable host-wide Docker pruning.
- Use current Home Assistant app metadata and document the required protection-mode setting.
