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

mkdir -p "${TEST_DIR}/data"

# These single-quoted strings are the source of generated stand-in commands.
# shellcheck disable=SC2016
printf '%s\n' '#!/bin/sh' 'printf configured > "${CONFIGURE_MARKER}"' > "${TEST_DIR}/configure"
# shellcheck disable=SC2016
printf '%s\n' '#!/bin/sh' 'printf prepared > "${PREPARE_MARKER}"' > "${TEST_DIR}/prepare"
# shellcheck disable=SC2016
printf '%s\n' '#!/bin/sh' 'printf started > "${START_MARKER}"' > "${TEST_DIR}/start"
printf '%s\n' '#!/bin/sh' 'exit 1' > "${TEST_DIR}/bridge"

# shellcheck disable=SC2016
printf '%s\n' \
    '#!/bin/sh' \
    'printf "%s\n" "$*" >> "${DOCKER_LOG}"' \
    'case "$*" in' \
    '  *"io.doover.home-assistant.managed"*"doover-device-agent"*) printf "true\n" ;;' \
    '  *"io.doover.home-assistant.managed"*"doover-app-controller"*) printf "true\n" ;;' \
    '  *"io.doover.home-assistant.managed"*"doover-device-loopback-proxy"*) printf "true\n" ;;' \
    '  *"inspect --format {{.State.Running}} doover-device-agent"*) printf "true\n" ;;' \
    '  *"inspect --format {{.State.Running}} doover-app-controller"*) printf "true\n" ;;' \
    '  *"inspect --format {{.State.Running}} doover-device-loopback-proxy"*) printf "true\n" ;;' \
    'esac' > "${TEST_DIR}/docker"

chmod 0755 "${TEST_DIR}/configure" "${TEST_DIR}/prepare" \
    "${TEST_DIR}/start" "${TEST_DIR}/bridge" "${TEST_DIR}/docker"

CONFIGURE_MARKER="${TEST_DIR}/configure.marker" \
PREPARE_MARKER="${TEST_DIR}/prepare.marker" \
START_MARKER="${TEST_DIR}/start.marker" \
DOCKER_LOG="${TEST_DIR}/docker.log" \
CONFIGURE_BIN="${TEST_DIR}/configure" \
PREPARE_BIN="${TEST_DIR}/prepare" \
START_SERVICES_BIN="${TEST_DIR}/start" \
BRIDGE_BIN="${TEST_DIR}/bridge" \
DOCKER_BIN="${TEST_DIR}/docker" \
REQUIRE_DOCKER_SOCKET=0 \
DATA_DIR="${TEST_DIR}/data" \
    "${REPO_ROOT}/doover_device/rootfs/run.sh" > "${TEST_DIR}/entrypoint.log" 2>&1 &
ENTRYPOINT_PID=$!

attempt=0
while [ "${attempt}" -lt 20 ]; do
    if [ -f "${TEST_DIR}/configure.marker" ] &&
        [ -f "${TEST_DIR}/prepare.marker" ] &&
        [ -f "${TEST_DIR}/start.marker" ]; then
        break
    fi
    attempt=$((attempt + 1))
    sleep 0.1
done

test -f "${TEST_DIR}/configure.marker"
test -f "${TEST_DIR}/prepare.marker"
test -f "${TEST_DIR}/start.marker"

kill -TERM "${ENTRYPOINT_PID}"
wait "${ENTRYPOINT_PID}"
ENTRYPOINT_PID=""

grep -q -- 'stop --time 15 doover-app-controller' "${TEST_DIR}/docker.log"
grep -q -- 'stop --time 15 doover-device-agent' "${TEST_DIR}/docker.log"
grep -q -- 'stop --time 15 doover-device-loopback-proxy' "${TEST_DIR}/docker.log"
grep -q -- 'rm -f doover-app-controller' "${TEST_DIR}/docker.log"
grep -q -- 'rm -f doover-device-agent' "${TEST_DIR}/docker.log"
grep -q -- 'rm -f doover-device-loopback-proxy' "${TEST_DIR}/docker.log"
grep -q 'Stopping Doover services' "${TEST_DIR}/entrypoint.log"

printf 'entrypoint lifecycle: ok\n'
