#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
TEST_DIR=$(mktemp -d)

cleanup() {
    rm -rf "${TEST_DIR}"
}
trap cleanup EXIT INT TERM

mkdir -p "${TEST_DIR}/data"
printf '%s\n' '#!/bin/sh' 'exit 0' > "${TEST_DIR}/docker-cli"
printf '%s\n' '#!/bin/sh' 'exit 0' > "${TEST_DIR}/docker-compose"
chmod 0755 "${TEST_DIR}/docker-cli" "${TEST_DIR}/docker-compose"

# shellcheck disable=SC2016
printf '%s\n' \
    '#!/bin/sh' \
    'printf "%s\n" "$*" >> "${DOCKER_LOG}"' \
    'if [ "$1" = "inspect" ] && [ "${2:-}" = "self" ]; then exit 0; fi' \
    'if [ "$1" = "inspect" ] && [ "$#" = "2" ]; then' \
    '  if [ "${CONFLICT:-0}" = "1" ] && [ "$2" = "doover-app-controller" ]; then exit 0; fi' \
    '  exit 1' \
    'fi' \
    'if [ "$1" = "inspect" ] && [ "${2:-}" = "--format" ]; then' \
    '  case "${3:-}" in *":="*) printf "hassio \n"; exit 0 ;; esac' \
    'fi' \
    'case "$*" in' \
    '  *"io.doover.home-assistant.managed"*"doover-app-controller"*) printf "false\n" ;;' \
    '  *"--format {{.Image}} self"*) printf "sha256:addon\n" ;;' \
    '  *"--format {{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}} doover-device-agent"*) printf "172.30.32.3 \n" ;;' \
    '  *"--format {{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}} self"*) printf "172.30.32.2 \n" ;;' \
    '  *"--format {{.State.Running}} doover-device-agent"*) printf "true\n" ;;' \
    '  *"--format {{.State.Running}} doover-app-controller"*) printf "true\n" ;;' \
    '  *"--format {{.State.Running}} doover-device-loopback-proxy"*) printf "true\n" ;;' \
    '  *"--format {{.State.Running}} doover-home-assistant-bridge-proxy"*) printf "true\n" ;;' \
    'esac' \
    'exit 0' > "${TEST_DIR}/docker"
chmod 0755 "${TEST_DIR}/docker"

DOCKER_LOG="${TEST_DIR}/docker.log" \
DOCKER_BIN="${TEST_DIR}/docker" \
DATA_DIR="${TEST_DIR}/data" \
SELF_CONTAINER_ID=self \
BRIDGE_ENABLED=1 \
STARTUP_ATTEMPTS=1 \
WRAPPER_SOURCE="${REPO_ROOT}/doover_device/rootfs/usr/local/bin/doover-app-run-home-assistant" \
DOCKER_CLI_SOURCE="${TEST_DIR}/docker-cli" \
DOCKER_COMPOSE_SOURCE="${TEST_DIR}/docker-compose" \
PROXY_BIN="${REPO_ROOT}/doover_device/rootfs/usr/local/bin/start-doover-loopback-proxy" \
    "${REPO_ROOT}/doover_device/rootfs/usr/local/bin/start-doover-services"

grep -q -- '--name doover-device-agent --network hassio --volumes-from self' "${TEST_DIR}/docker.log"
grep -q -- '--entrypoint /bin/dda-agent doover-home-assistant/device-agent:runtime' "${TEST_DIR}/docker.log"
grep -q -- 'exec doover-device-agent /bin/dda-agent healthcheck' "${TEST_DIR}/docker.log"
grep -q -- '--network host' "${TEST_DIR}/docker.log"
grep -q -- 'TCP4:172.30.32.3:50051' "${TEST_DIR}/docker.log"
grep -q -- '--name doover-home-assistant-bridge-proxy --network host' "${TEST_DIR}/docker.log"
grep -q -- 'TCP4:172.30.32.2:49192' "${TEST_DIR}/docker.log"
grep -q -- '--name doover-app-controller --network hassio --volumes-from self' "${TEST_DIR}/docker.log"
grep -q -- '--env DDA_URI=doover-device-agent:50051' "${TEST_DIR}/docker.log"
grep -q -- '--env DOCKER_HOST=unix:///run/docker.sock' "${TEST_DIR}/docker.log"
if grep -q -- '--env DOCKER_CONFIG=' "${TEST_DIR}/docker.log"; then
    printf 'managed services persisted the controller Docker config under /data\n' >&2
    exit 1
fi
grep -q -- '--env PATH=/data/runtime/bin:' "${TEST_DIR}/docker.log"
grep -q -- '--entrypoint /data/runtime/doover-app-run-home-assistant doover-home-assistant/app-controller:runtime' "${TEST_DIR}/docker.log"
grep -q -- 'exec doover-app-controller docker version' "${TEST_DIR}/docker.log"
grep -q -- 'exec doover-app-controller docker compose version' "${TEST_DIR}/docker.log"
test -x "${TEST_DIR}/data/runtime/doover-app-run-home-assistant"
test -x "${TEST_DIR}/data/runtime/bin/docker"
test -x "${TEST_DIR}/data/runtime/docker-compose"

mkdir -p "${TEST_DIR}/conflict-data"
if DOCKER_LOG="${TEST_DIR}/conflict-docker.log" \
    DOCKER_BIN="${TEST_DIR}/docker" \
    DATA_DIR="${TEST_DIR}/conflict-data" \
    SELF_CONTAINER_ID=self \
    CONFLICT=1 \
    WRAPPER_SOURCE="${REPO_ROOT}/doover_device/rootfs/usr/local/bin/doover-app-run-home-assistant" \
    DOCKER_CLI_SOURCE="${TEST_DIR}/docker-cli" \
    DOCKER_COMPOSE_SOURCE="${TEST_DIR}/docker-compose" \
    PROXY_BIN="${REPO_ROOT}/doover_device/rootfs/usr/local/bin/start-doover-loopback-proxy" \
    "${REPO_ROOT}/doover_device/rootfs/usr/local/bin/start-doover-services" \
    > "${TEST_DIR}/conflict.log" 2>&1; then
    printf 'managed services unexpectedly removed an unmanaged name conflict\n' >&2
    exit 1
fi
grep -q 'already used by an unmanaged container' "${TEST_DIR}/conflict.log"
if grep -q -- 'rm -f doover-app-controller' "${TEST_DIR}/conflict-docker.log"; then
    printf 'managed services removed an unmanaged container\n' >&2
    exit 1
fi

printf 'managed service contract: ok\n'
