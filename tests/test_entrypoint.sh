#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
TEST_DIR=$(mktemp -d)
ENTRYPOINT_PID=""

cleanup() {
    if [ -n "${ENTRYPOINT_PID}" ]; then
        kill -TERM "${ENTRYPOINT_PID}" 2>/dev/null || true
        wait "${ENTRYPOINT_PID}" 2>/dev/null || true
    fi
    rm -rf "${TEST_DIR}"
}
trap cleanup EXIT INT TERM

mkdir -p "${TEST_DIR}/data/agent" "${TEST_DIR}/data/app_controller"

printf '%s\n' \
    '{' \
    '  "agent_id": "123456789",' \
    '  "organisation_id": "987654321",' \
    '  "auth_token": "test-token",' \
    '  "client_id": "",' \
    '  "client_secret": "",' \
    '  "data_api": "https://global.data.doover.com",' \
    '  "data_wss": "wss://global.data.doover.com/gateway",' \
    '  "data_static_ips": "",' \
    '  "debug": false' \
    '}' > "${TEST_DIR}/options.json"

# The single-quoted strings are the source of the generated stand-in services.
# shellcheck disable=SC2016
printf '%s\n' \
    '#!/bin/sh' \
    'if [ "${1:-}" = "healthcheck" ]; then exit 0; fi' \
    'printf started > "${DDA_MARKER}"' \
    'trap '\''printf stopped >> "${DDA_MARKER}"; exit 0'\'' TERM INT' \
    'while :; do sleep 1; done' > "${TEST_DIR}/fake-dda"

# shellcheck disable=SC2016
printf '%s\n' \
    '#!/bin/sh' \
    'printf started > "${CONTROLLER_MARKER}"' \
    'trap '\''printf stopped >> "${CONTROLLER_MARKER}"; exit 0'\'' TERM INT' \
    'while :; do sleep 1; done' > "${TEST_DIR}/fake-controller"

chmod 0755 "${TEST_DIR}/fake-dda" "${TEST_DIR}/fake-controller"

OPTIONS_PATH="${TEST_DIR}/options.json" \
AGENT_CONFIG_PATH="${TEST_DIR}/data/agent/config.json" \
CONFIGURE_BIN="${REPO_ROOT}/doover_device/rootfs/usr/local/bin/configure-doover" \
DDA_BIN="${TEST_DIR}/fake-dda" \
APP_CONTROLLER_BIN="${TEST_DIR}/fake-controller" \
DDA_MARKER="${TEST_DIR}/dda.marker" \
CONTROLLER_MARKER="${TEST_DIR}/controller.marker" \
REQUIRE_DOCKER_SOCKET=0 \
REQUIRE_LOOPBACK_PROXY=0 \
DATA_DIR="${TEST_DIR}/data" \
    "${REPO_ROOT}/doover_device/rootfs/run.sh" > "${TEST_DIR}/entrypoint.log" 2>&1 &
ENTRYPOINT_PID=$!

attempt=0
while [ "${attempt}" -lt 20 ]; do
    if [ -f "${TEST_DIR}/dda.marker" ] && [ -f "${TEST_DIR}/controller.marker" ]; then
        break
    fi
    attempt=$((attempt + 1))
    sleep 0.1
done

test -f "${TEST_DIR}/dda.marker"
test -f "${TEST_DIR}/controller.marker"

kill -TERM "${ENTRYPOINT_PID}"
wait "${ENTRYPOINT_PID}"
ENTRYPOINT_PID=""

grep -q 'startedstopped' "${TEST_DIR}/dda.marker"
grep -q 'startedstopped' "${TEST_DIR}/controller.marker"
grep -q 'Starting Doover Device Agent' "${TEST_DIR}/entrypoint.log"
grep -q 'Starting Doover App Controller' "${TEST_DIR}/entrypoint.log"

printf 'entrypoint lifecycle: ok\n'
