#!/bin/sh
set -u

DDA_BIN="${DDA_BIN:-/bin/dda-agent}"
APP_CONTROLLER_BIN="${APP_CONTROLLER_BIN:-doover-app-run-home-assistant}"
CONFIGURE_BIN="${CONFIGURE_BIN:-/usr/local/bin/configure-doover}"
PROXY_BIN="${PROXY_BIN:-/usr/local/bin/start-doover-loopback-proxy}"
DOCKER_SOCKET="${DOCKER_SOCKET:-/run/docker.sock}"
REQUIRE_DOCKER_SOCKET="${REQUIRE_DOCKER_SOCKET:-1}"
REQUIRE_LOOPBACK_PROXY="${REQUIRE_LOOPBACK_PROXY:-1}"
DATA_DIR="${DATA_DIR:-/data}"
PROXY_NAME="doover-device-loopback-proxy"

log() {
    printf '[doover] %s\n' "$*"
}

if [ "${REQUIRE_DOCKER_SOCKET}" = "1" ] && [ ! -S "${DOCKER_SOCKET}" ]; then
    log "Docker socket not found at ${DOCKER_SOCKET}. Check docker_api and protected mode."
    exit 1
fi

mkdir -p "${DATA_DIR}/agent" "${DATA_DIR}/app_controller"

"${CONFIGURE_BIN}"
status=$?
if [ "${status}" -ne 0 ]; then
    exit "${status}"
fi

export CONFIG_FP="${AGENT_CONFIG_PATH:-${DATA_DIR}/agent/config.json}"
export DOCKER_HOST="unix://${DOCKER_SOCKET}"
export APP_KEY="doover-app-controller"
export HEALTHCHECK_PORT="49191"

DDA_PID=""
CONTROLLER_PID=""

# shellcheck disable=SC2317,SC2329  # Called by the TERM and INT traps.
stop_services() {
    trap - TERM INT
    log "Stopping Doover services"
    if [ -n "${CONTROLLER_PID}" ]; then
        kill -TERM "${CONTROLLER_PID}" 2>/dev/null || true
        wait "${CONTROLLER_PID}" 2>/dev/null || true
    fi
    if [ -n "${DDA_PID}" ]; then
        kill -TERM "${DDA_PID}" 2>/dev/null || true
        wait "${DDA_PID}" 2>/dev/null || true
    fi
    if [ "${REQUIRE_LOOPBACK_PROXY}" = "1" ]; then
        docker rm -f "${PROXY_NAME}" >/dev/null 2>&1 || true
    fi
    exit 0
}

trap stop_services TERM INT

log "Starting Doover Device Agent"
"${DDA_BIN}" &
DDA_PID=$!

ready=0
attempt=0
while [ "${attempt}" -lt 60 ]; do
    if ! kill -0 "${DDA_PID}" 2>/dev/null; then
        wait "${DDA_PID}" 2>/dev/null
        status=$?
        log "Device Agent exited during startup with status ${status}"
        exit 1
    fi
    if "${DDA_BIN}" healthcheck >/dev/null 2>&1; then
        ready=1
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done

if [ "${ready}" -ne 1 ]; then
    log "Device Agent did not become healthy within 60 seconds"
    kill -TERM "${DDA_PID}" 2>/dev/null || true
    wait "${DDA_PID}" 2>/dev/null || true
    exit 1
fi

if [ "${REQUIRE_LOOPBACK_PROXY}" = "1" ]; then
    log "Starting host-loopback proxy on 127.0.0.1:50051"
    if ! "${PROXY_BIN}"; then
        log "Could not start the Device Agent loopback proxy"
        kill -TERM "${DDA_PID}" 2>/dev/null || true
        wait "${DDA_PID}" 2>/dev/null || true
        exit 1
    fi
fi

log "Starting Doover App Controller"
"${APP_CONTROLLER_BIN}" &
CONTROLLER_PID=$!

proxy_is_running() {
    [ "${REQUIRE_LOOPBACK_PROXY}" != "1" ] ||
        [ "$(docker inspect --format '{{.State.Running}}' "${PROXY_NAME}" 2>/dev/null)" = "true" ]
}

while kill -0 "${DDA_PID}" 2>/dev/null &&
    kill -0 "${CONTROLLER_PID}" 2>/dev/null &&
    proxy_is_running; do
    sleep 2
done

if ! kill -0 "${DDA_PID}" 2>/dev/null; then
    wait "${DDA_PID}" 2>/dev/null
    status=$?
    log "Device Agent exited with status ${status}"
elif ! kill -0 "${CONTROLLER_PID}" 2>/dev/null; then
    wait "${CONTROLLER_PID}" 2>/dev/null
    status=$?
    log "App Controller exited with status ${status}"
else
    log "Device Agent loopback proxy stopped unexpectedly"
fi

kill -TERM "${CONTROLLER_PID}" 2>/dev/null || true
kill -TERM "${DDA_PID}" 2>/dev/null || true
wait "${CONTROLLER_PID}" 2>/dev/null || true
wait "${DDA_PID}" 2>/dev/null || true
if [ "${REQUIRE_LOOPBACK_PROXY}" = "1" ]; then
    docker rm -f "${PROXY_NAME}" >/dev/null 2>&1 || true
fi
exit 1
