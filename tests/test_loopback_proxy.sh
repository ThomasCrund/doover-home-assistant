#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
TEST_DIR=$(mktemp -d)

cleanup() {
    rm -rf "${TEST_DIR}"
}
trap cleanup EXIT INT TERM

# shellcheck disable=SC2016
printf '%s\n' \
    '#!/bin/sh' \
    'printf "%s\n" "$*" >> "${DOCKER_LOG}"' \
    'if [ "$1" = "inspect" ] && [ "${2:-}" = "self" ]; then exit 0; fi' \
    'if [ "$1" = "inspect" ] && { [ "${2:-}" = "doover-device-loopback-proxy" ] || [ "${2:-}" = "doover-home-assistant-bridge-proxy" ]; }; then exit 1; fi' \
    'case "$*" in' \
    '  *"--format {{.Image}} self"*) printf "sha256:addon\n" ;;' \
    '  *"--format {{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}} doover-device-agent"*) printf "172.30.32.3 \n" ;;' \
    '  *"--format {{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}} self"*) printf "172.30.32.2 \n" ;;' \
    '  *"--format {{.State.Running}} doover-device-loopback-proxy"*) printf "true\n" ;;' \
    '  *"--format {{.State.Running}} doover-home-assistant-bridge-proxy"*) printf "true\n" ;;' \
    'esac' > "${TEST_DIR}/docker"
chmod 0755 "${TEST_DIR}/docker"

DOCKER_LOG="${TEST_DIR}/docker.log" \
DOCKER_BIN="${TEST_DIR}/docker" \
SELF_CONTAINER_ID=self \
    "${REPO_ROOT}/doover_device/rootfs/usr/local/bin/start-doover-loopback-proxy"

grep -q -- '--network host' "${TEST_DIR}/docker.log"
grep -q -- '--entrypoint /usr/bin/socat sha256:addon' "${TEST_DIR}/docker.log"
grep -q -- 'TCP4-LISTEN:50051,bind=127.0.0.1,reuseaddr,fork' "${TEST_DIR}/docker.log"
grep -q -- 'TCP4:172.30.32.3:50051' "${TEST_DIR}/docker.log"

DOCKER_LOG="${TEST_DIR}/docker.log" \
DOCKER_BIN="${TEST_DIR}/docker" \
SELF_CONTAINER_ID=self \
TARGET_CONTAINER=self \
PROXY_NAME=doover-home-assistant-bridge-proxy \
LISTEN_PORT=49192 \
TARGET_PORT=49192 \
    "${REPO_ROOT}/doover_device/rootfs/usr/local/bin/start-doover-loopback-proxy"

grep -q -- '--name doover-home-assistant-bridge-proxy --network host' "${TEST_DIR}/docker.log"
grep -q -- 'TCP4-LISTEN:49192,bind=127.0.0.1,reuseaddr,fork' "${TEST_DIR}/docker.log"
grep -q -- 'TCP4:172.30.32.2:49192' "${TEST_DIR}/docker.log"

printf 'loopback proxy contract: ok\n'
