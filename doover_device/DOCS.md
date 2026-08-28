# Doover Device app

## Install the app

Create the device in Doover with the **Raspberry Pi** device type before you configure this app. Keep the provisioning data open while you complete these steps.

1. Add `https://github.com/ThomasCrund/doover-home-assistant` as a repository in the Home Assistant app store.
2. Install **Doover Device**.
3. Open the **Info** tab and turn off **Protection mode**. The App Controller cannot use the host Docker API while protection mode is on.
4. Open the **Configuration** tab.
5. Enter a **Docker Hub username** that has access to the private Doover images.
6. Create a read-only Docker Hub personal access token and enter it as the **Docker Hub access token**. Do not enter the account password.
7. Copy the `AGENT_ID` value to **Agent ID**.
8. Copy the `ORGANISATION_ID` value to **Organisation ID**.
9. Configure one Doover device credential method.
10. Copy `DATA_API` and `DATA_WSS` from the provisioning data. Keep the defaults only when they match.
11. Save the configuration and start the app.

The app signs in to Docker Hub, pulls the two digest-pinned Doover images, and removes its temporary Docker CLI login file. The log then shows `Starting Doover Device Agent` and `Starting Doover App Controller`. The device becomes online in Doover after the Device Agent authenticates.

## Choose a credential method

Use the device auth token when the provisioning data contains `AUTH_TOKEN`. Copy it to **Device auth token**, and leave the OAuth fields blank.

If the provisioning data does not contain a device auth token, leave **Device auth token** blank. Copy `CLIENT_ID` and `CLIENT_SECRET` to the two OAuth fields.

The Device Agent can rotate a device auth token. The app stores the rotated token in `/data/agent/config.json` and keeps it across restarts and backups. When you replace **Device auth token** in the Home Assistant configuration, the new value replaces the stored token on the next start.

## Deploy Doover apps

Assign apps to the Raspberry Pi device in Doover after the device comes online. The App Controller downloads each deployment and creates its containers through the host Docker daemon.

Deployed containers are Docker containers, not separate Home Assistant apps. Check deployment and health status in Doover. The **Doover Device** log also records pulls, starts, and failures.

Stopping **Doover Device** removes its managed Device Agent, App Controller, and loopback proxy containers. It does not remove app containers that the App Controller already deployed. Delete those deployments in Doover before you uninstall the app. If the device is offline, remove the deployed containers through the host Docker daemon.

## Network ports

Doover app containers connect to the Device Agent at `127.0.0.1:50051`. The Home Assistant app itself stays on a private container network. A small managed proxy exposes port `50051` only on the Home Assistant host's loopback interface, so other machines on the LAN cannot call the Device Agent API.

Port `50051` must be free on host loopback. The app will stop with an error instead of exposing the Device Agent more broadly when it cannot start the proxy.

The three managed service containers are removed during normal shutdown and replaced on every start. An abrupt host power loss or forced removal of the Home Assistant app can leave them running or stopped. Starting **Doover Device** again removes and replaces them. If you uninstall the app after a forced shutdown, remove containers labelled `io.doover.home-assistant.managed=true` through the host Docker daemon.

## Security and platform limits

The App Controller needs full Docker API operations to create, update, and remove deployed app containers. You must turn off protection mode after installation. The app also runs without an AppArmor profile. A deployed app can request host mounts or elevated container privileges. Review every app assigned to this device, and only install this Home Assistant app on a host and network that you trust.

Home Assistant stores the Docker Hub username and access token in the app configuration and includes them in app backups. Use a dedicated, read-only token and restrict the Docker Hub account to the required Doover repositories. The token is sent to `docker login` through standard input, is not written to the app log or command arguments, and its temporary Docker CLI configuration is deleted after each pull.

The upstream App Controller includes automatic host-wide Docker pruning for traditional standalone devices. This app disables that operation because the Docker daemon also owns Home Assistant apps and data. Deployment operations still have full Docker access, but the controller does not invoke `docker system prune`.

The app supports `aarch64` and `amd64`. Raspberry Pi installations must run a 64-bit Home Assistant system. Home Assistant Container installations cannot run Home Assistant apps.

## Persistent data

Home Assistant stores the Device Agent state, App Controller deployment records, and configured secrets in the app's `/data` directory. Include the app in Home Assistant backups to preserve the current device token and deployment state. Protect those backups because they contain the Doover and Docker Hub credentials.
