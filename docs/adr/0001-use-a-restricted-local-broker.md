# Use a restricted local broker for Home Assistant access

The Doover bridge app communicates with a broker inside the Home Assistant app instead of storing a Home Assistant long-lived access token in its deployment configuration. The broker keeps the Supervisor credential local, exposes only selected entity reads and light on/off/toggle commands on host loopback, and authenticates the bridge app with a separate bridge credential. This adds one local component and requires the same scoped credential in both configurations, but prevents a remotely stored app credential from becoming a general Home Assistant credential.

## Considered Options

- A direct Home Assistant REST connection was rejected because its long-lived token inherits the permissions of a Home Assistant user and would be stored with the Doover deployment.
- A custom Home Assistant integration was rejected because it creates a second installation and lifecycle path alongside the existing Home Assistant app.

## Consequences

The bridge broker is the only component allowed to call the Home Assistant API. New readable domains or commands must be added explicitly at this boundary. The initial bridge uses bounded polling so reconnection and failure behavior remain simple; a later WebSocket implementation can preserve the same local API.
