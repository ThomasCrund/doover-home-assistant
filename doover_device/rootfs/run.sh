#!/bin/sh
set -u

CONFIGURE_BIN="${CONFIGURE_BIN:-/usr/local/bin/configure-doover}"
PREPARE_BIN="${PREPARE_BIN:-/usr/local/bin/prepare-doover-runtime}"
START_SERVICES_BIN="${START_SERVICES_BIN:-/usr/local/bin/start-doover-services}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
DOCKER_SOCKET="${DOCKER_SOCKET:-/run/docker.sock}"
REQUIRE_DOCKER_SOCKET="${REQUIRE_DOCKER_SOCKET:-1}"
DATA_DIR="${DATA_DIR:-/data}"

DDA_NAME="doover-device-agent"
CONTROLLER_NAME="doover-app-controller"
PROXY_NAME="doover-device-loopback-proxy"
BRIDGE_PROXY_NAME="doover-home-assistant-bridge-proxy"
BRIDGE_BIN="${BRIDGE_BIN:-/usr/local/bin/home-assistant-bridge-broker}"
OPTIONS_PATH="${OPTIONS_PATH:-${DATA_DIR}/options.json}"
BRIDGE_PID=""

log() {
    printf '[doover] %s\n' "$*"
}

container_is_running() {
    [ "$("${DOCKER_BIN}" inspect --format '{{.State.Running}}' "$1" 2>/dev/null)" = "true" ]
}

remove_managed_container() {
    container_name="$1"
    managed=$(
        "${DOCKER_BIN}" inspect \
            --format '{{index .Config.Labels "io.doover.home-assistant.managed"}}' \
            "${container_name}" 2>/dev/null
    )
    if [ "${managed}" = "true" ]; then
        "${DOCKER_BIN}" stop --time 15 "${container_name}" >/dev/null 2>&1 || true
        "${DOCKER_BIN}" rm -f "${container_name}" >/dev/null 2>&1 || true
    fi
}

# shellcheck disable=SC2317,SC2329  # Called by the TERM and INT traps.
stop_services() {
    trap - TERM INT
    log "Stopping Doover services"
    remove_managed_container "${CONTROLLER_NAME}"
    remove_managed_container "${DDA_NAME}"
    remove_managed_container "${PROXY_NAME}"
    remove_managed_container "${BRIDGE_PROXY_NAME}"
    if [ -n "${BRIDGE_PID}" ]; then
        kill -TERM "${BRIDGE_PID}" >/dev/null 2>&1 || true
        wait "${BRIDGE_PID}" 2>/dev/null || true
    fi
    exit 0
}

trap stop_services TERM INT

if [ "${REQUIRE_DOCKER_SOCKET}" = "1" ] && [ ! -S "${DOCKER_SOCKET}" ]; then
    log "Docker socket not found at ${DOCKER_SOCKET}. Turn off protection mode and restart the app."
    exit 1
fi

mkdir -p "${DATA_DIR}/agent" "${DATA_DIR}/app_controller"
export AGENT_CONFIG_PATH="${AGENT_CONFIG_PATH:-${DATA_DIR}/agent/config.json}"
export DATA_DIR DOCKER_BIN
export DOCKER_HOST="unix://${DOCKER_SOCKET}"

"${CONFIGURE_BIN}" || exit $?
"${PREPARE_BIN}" || exit $?
BRIDGE_ENABLED=0
if "${BRIDGE_BIN}" --options "${OPTIONS_PATH}" --check-enabled; then
    BRIDGE_ENABLED=1
    log "Starting restricted Home Assistant bridge"
    "${BRIDGE_BIN}" --options "${OPTIONS_PATH}" &
    BRIDGE_PID=$!
fi
export BRIDGE_ENABLED
if ! "${START_SERVICES_BIN}"; then
    if [ -n "${BRIDGE_PID}" ]; then
        kill -TERM "${BRIDGE_PID}" >/dev/null 2>&1 || true
        wait "${BRIDGE_PID}" 2>/dev/null || true
    fi
    exit 1
fi

while container_is_running "${DDA_NAME}" &&
    container_is_running "${CONTROLLER_NAME}" &&
    container_is_running "${PROXY_NAME}" &&
    { [ "${BRIDGE_ENABLED}" = "0" ] ||
        { container_is_running "${BRIDGE_PROXY_NAME}" && kill -0 "${BRIDGE_PID}" 2>/dev/null; }; }; do
    sleep 2
done

if ! container_is_running "${DDA_NAME}"; then
    log "Device Agent stopped unexpectedly"
elif ! container_is_running "${CONTROLLER_NAME}"; then
    log "App Controller stopped unexpectedly"
elif [ "${BRIDGE_ENABLED}" = "1" ] && ! kill -0 "${BRIDGE_PID}" 2>/dev/null; then
    log "Home Assistant bridge stopped unexpectedly"
elif [ "${BRIDGE_ENABLED}" = "1" ] && ! container_is_running "${BRIDGE_PROXY_NAME}"; then
    log "Home Assistant bridge proxy stopped unexpectedly"
else
    log "Device Agent loopback proxy stopped unexpectedly"
fi

remove_managed_container "${CONTROLLER_NAME}"
remove_managed_container "${DDA_NAME}"
remove_managed_container "${PROXY_NAME}"
remove_managed_container "${BRIDGE_PROXY_NAME}"
if [ -n "${BRIDGE_PID}" ]; then
    kill -TERM "${BRIDGE_PID}" >/dev/null 2>&1 || true
    wait "${BRIDGE_PID}" 2>/dev/null || true
fi
exit 1
