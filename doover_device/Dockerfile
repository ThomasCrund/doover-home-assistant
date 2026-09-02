# syntax=docker/dockerfile:1

# The bootstrap must be anonymously buildable. It pulls the private, digest-pinned
# Doover services only after Home Assistant supplies Docker Hub credentials.
FROM python:3.13-alpine3.22@sha256:e81548ac35b07a3bd4805f275107592ef458b1e893c0e04d45aedaa19416cca5

ARG BUILD_ARCH
ARG BUILD_VERSION

RUN apk add --no-cache docker-cli docker-cli-compose socat

COPY rootfs /

RUN chmod 0755 /run.sh /usr/local/bin/configure-doover \
        /usr/local/bin/home-assistant-bridge-broker \
        /usr/local/bin/doover-app-run-home-assistant \
        /usr/local/bin/prepare-doover-runtime \
        /usr/local/bin/start-doover-services \
        /usr/local/bin/start-doover-loopback-proxy \
    && python3 -m py_compile \
        /usr/local/bin/configure-doover \
        /usr/local/bin/home-assistant-bridge-broker \
        /usr/local/bin/doover-app-run-home-assistant \
        /usr/local/bin/prepare-doover-runtime

LABEL \
  io.hass.name="Doover Device" \
  io.hass.description="Connect this Home Assistant host to Doover as a Raspberry Pi device" \
  io.hass.type="addon" \
  io.hass.arch="${BUILD_ARCH}" \
  io.hass.version="${BUILD_VERSION}" \
  org.opencontainers.image.source="https://github.com/ThomasCrund/doover-home-assistant"

STOPSIGNAL SIGTERM
CMD ["/run.sh"]
