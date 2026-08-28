# syntax=docker/dockerfile:1

# Pin both upstream images so a local Home Assistant rebuild uses the same code.
FROM spaneng/doover-device-agent:main@sha256:e82c48e4e14d2dd1dc283a63857622f7a3a8e09d6cb9102770cc3a549bac4cf6 AS device_agent
FROM spaneng/doover-app-controller:main@sha256:c09862de054764c707514e6ce625b1c3f1165a1120e3120caf9742aabc937048

ARG BUILD_ARCH
ARG BUILD_VERSION

RUN apk add --no-cache docker-cli docker-cli-compose socat

COPY --from=device_agent /bin/dda-agent /bin/dda-agent
COPY --from=device_agent /app/static/ /app/static/
COPY rootfs /

RUN chmod 0755 /run.sh /usr/local/bin/configure-doover \
        /usr/local/bin/doover-app-run-home-assistant \
        /usr/local/bin/start-doover-loopback-proxy \
    && mkdir -p /var/lib/dds \
    && ln -s /data/app_controller /var/lib/dds/app_controller \
    && /bin/dda-agent --help >/dev/null \
    && python3 -c "import doover_app_controller"

# Exercise both real processes on each target architecture without cloud access.
RUN set -eu; \
    mkdir -p /data/app_controller /tmp/dda; \
    DATA_API="" AGENT_ID="1" ORGANISATION_ID="1" AUTH_TOKEN="smoke-token" \
        RUN_WEB_SERVER="0" CONFIG_FP="/tmp/dda/config.json" /bin/dda-agent >/tmp/dda.log 2>&1 & \
    dda_pid=$!; \
    controller_pid=""; \
    cleanup() { \
        [ -z "${controller_pid}" ] || kill -TERM "${controller_pid}" 2>/dev/null || true; \
        kill -TERM "${dda_pid}" 2>/dev/null || true; \
        wait "${controller_pid}" 2>/dev/null || true; \
        wait "${dda_pid}" 2>/dev/null || true; \
        rm -rf /data/app_controller /tmp/dda /tmp/dda.log /tmp/controller.log; \
        rmdir /data 2>/dev/null || true; \
    }; \
    trap cleanup EXIT; \
    ready=0; \
    for attempt in 1 2 3 4 5 6 7 8 9 10; do \
        if CONFIG_FP="/tmp/dda/config.json" /bin/dda-agent healthcheck >/dev/null 2>&1; then ready=1; break; fi; \
        sleep 1; \
    done; \
    [ "${ready}" -eq 1 ] || { cat /tmp/dda.log; exit 1; }; \
    APP_KEY="doover-app-controller" HEALTHCHECK_PORT="49191" DDA_URI="127.0.0.1:50051" \
        DOCKER_HOST="unix:///tmp/missing-docker.sock" doover-app-run-home-assistant >/tmp/controller.log 2>&1 & \
    controller_pid=$!; \
    ready=0; \
    for attempt in 1 2 3 4 5 6 7 8 9 10; do \
        if curl -fsS http://127.0.0.1:49191 >/dev/null 2>&1; then ready=1; break; fi; \
        sleep 1; \
    done; \
    [ "${ready}" -eq 1 ] || { cat /tmp/controller.log; exit 1; }

LABEL \
  io.hass.name="Doover Device" \
  io.hass.description="Connect this Home Assistant host to Doover as a Raspberry Pi device" \
  io.hass.type="addon" \
  io.hass.arch="${BUILD_ARCH}" \
  io.hass.version="${BUILD_VERSION}" \
  org.opencontainers.image.source="https://github.com/ThomasCrund/doover-home-assistant"

STOPSIGNAL SIGTERM
CMD ["/run.sh"]
