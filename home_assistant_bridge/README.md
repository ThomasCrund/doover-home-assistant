# Home Assistant Bridge

This Doover device app shows selected Home Assistant entities in Doover. It supports numeric sensors, text sensors, binary sensors, and lights. Each light has **Turn On**, **Turn Off**, and **Toggle** controls.

The app connects to the restricted broker in the **Doover Device** Home Assistant app at `127.0.0.1:49192`. It cannot call the Home Assistant API directly.

## Configure Home Assistant

1. Update the **Doover Device** Home Assistant app to a version that includes the bridge.
2. Generate a bridge credential with at least 32 characters. For example:

   ```sh
   openssl rand -hex 32
   ```

3. Open the **Doover Device** configuration.
4. Turn on **Enable Home Assistant bridge**.
5. Enter the generated value in **Home Assistant bridge credential**.
6. Save the configuration, and restart **Doover Device**.

The app log shows `Starting restricted Home Assistant bridge` and `Starting Home Assistant bridge proxy on 127.0.0.1:49192`.

## Configure the Doover app

Assign **Home Assistant Bridge** to the same Doover Raspberry Pi device. Enter the same bridge credential, and add at least one entity.

Use these configuration groups:

- **Numeric Sensors** accepts `sensor.*` entities whose state is a number. Set the display units and decimal places in Doover.
- **Text Sensors** accepts `sensor.*` entities whose state is text.
- **Binary Sensors** accepts `binary_sensor.*` entities. Home Assistant states `on` and `off` become Boolean values.
- **Lights** accepts `light.*` entities. Doover shows the current on or off state and the three light controls.

Set **Polling Interval** to the number of seconds between state reads. The default is 2 seconds, and the minimum is 1 second.

After the deployment starts, open the device in Doover. **Bridge Connected** becomes true, and each configured entity shows **Available**. If Home Assistant reports `unknown`, `unavailable`, or a non-numeric state for a numeric sensor, **Available** becomes false for that entity.

## Find entity IDs

In Home Assistant, open **Developer Tools**, then open **States**. Copy the entity ID exactly, including the domain before the period. Examples include `sensor.lounge_temperature`, `binary_sensor.front_door`, and `light.lounge`.

## Security limits

The bridge broker keeps `SUPERVISOR_TOKEN` inside the Home Assistant app. The Doover deployment stores the separate bridge credential. That credential authorizes only these local operations:

- Read `sensor.*`, `binary_sensor.*`, and `light.*` states.
- Call `light.turn_on`, `light.turn_off`, and `light.toggle` for a `light.*` entity.

The broker removes Home Assistant attributes except `friendly_name`, `unit_of_measurement`, `device_class`, and `icon`. It listens through a managed proxy on host loopback, so another computer on the LAN cannot connect to port `49192`.

The bridge credential authorizes the supported operations for every `sensor.*`, `binary_sensor.*`, and `light.*` entity on this Home Assistant host. The entity lists restrict what the Doover app displays and controls, but they are not a broker access-control list. Treat every local container that holds the bridge credential as trusted to control all lights on the host.

Use a different bridge credential for each Home Assistant host. Home Assistant and Doover store the bridge credential in their configuration and backups.

## Develop and publish the app

Install the development environment and export the generated schema:

```sh
uv sync --all-groups
uv run export-config
uv run export-ui
uv run pytest
```

Set `organisation_id` in `doover_config.json` to the owning Doover organisation. The first publish registers the globally unique application name; later publishes update the same application. Publish the multi-architecture image and release with the Doover CLI:

```sh
doover app publish --build --tag 0.1.0
```
