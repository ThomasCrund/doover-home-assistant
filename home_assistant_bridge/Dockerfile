# syntax=docker/dockerfile:1

FROM spaneng/doover_device_base@sha256:ac1bb745bfaeeabc940582580dba4ce9104730ca8d19c17602cd1729654e8b41

LABEL com.doover.app="true"
LABEL com.doover.managed="true"

USER root
WORKDIR /app
COPY . /app
RUN python3 -m pip install --no-cache-dir --requirement /app/requirements.lock \
    && python3 -m pip install --no-cache-dir --no-deps /app

ENV HOME=/tmp
USER nobody
HEALTHCHECK --interval=30s --timeout=2s --start-period=5s \
    CMD curl -fsS "http://127.0.0.1:${HEALTHCHECK_PORT}" || exit 1
CMD ["doover-app-run"]
