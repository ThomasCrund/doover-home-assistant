# Changelog

## 0.1.0

- Run the Doover Device Agent and App Controller in one Home Assistant app.
- Accept Raspberry Pi provisioning IDs, endpoints, a device token, or OAuth client credentials.
- Preserve Device Agent token rotations across app restarts.
- Enable remote Doover app deployments through the host Docker API.
- Restrict the Device Agent API to host loopback and disable host-wide Docker pruning.
- Use current Home Assistant app metadata and document the required protection-mode setting.
