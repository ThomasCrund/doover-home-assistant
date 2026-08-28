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
"${START_SERVICES_BIN}" || exit $?

while container_is_running "${DDA_NAME}" &&
    container_is_running "${CONTROLLER_NAME}" &&
    container_is_running "${PROXY_NAME}"; do
    sleep 2
done

if ! container_is_running "${DDA_NAME}"; then
    log "Device Agent stopped unexpectedly"
elif ! container_is_running "${CONTROLLER_NAME}"; then
    log "App Controller stopped unexpectedly"
else
    log "Device Agent loopback proxy stopped unexpectedly"
fi

remove_managed_container "${CONTROLLER_NAME}"
remove_managed_container "${DDA_NAME}"
remove_managed_container "${PROXY_NAME}"
exit 1
