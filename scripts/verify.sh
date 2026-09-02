#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
cd "${REPO_ROOT}"
export PYTHONDONTWRITEBYTECODE=1

python3 -m unittest discover -s tests -p 'test_*.py' -v
(cd home_assistant_bridge && "${UV_BIN:-uv}" run pytest -q)
ruby tests/test_metadata.rb
shellcheck \
    doover_device/rootfs/run.sh \
    doover_device/rootfs/usr/local/bin/start-doover-services \
    doover_device/rootfs/usr/local/bin/start-doover-loopback-proxy \
    tests/test_entrypoint.sh \
    tests/test_managed_services.sh \
    tests/test_loopback_proxy.sh \
    scripts/verify.sh
tests/test_entrypoint.sh
tests/test_managed_services.sh
tests/test_loopback_proxy.sh

printf 'verification: ok\n'
