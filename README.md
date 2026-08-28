# Doover for Home Assistant

This repository contains Home Assistant apps and Doover device apps. The first Home Assistant app is `doover_device`, which registers the Home Assistant host as a Doover Raspberry Pi device.

The app runs two Doover services:

- The Device Agent connects the host to Doover and provides its gRPC API only on host loopback port `50051`.
- The App Controller receives deployments from Doover and runs their containers on the Home Assistant host.

See [the Doover Device app instructions](doover_device/DOCS.md) for installation and configuration.

## Repository layout

```text
doover_device/       Home Assistant app
scripts/verify.sh    Local verification entry point
tests/               Configuration, metadata, and process lifecycle tests
repository.yaml      Home Assistant app repository metadata
```

## Verify a change

Run:

```sh
scripts/verify.sh
```

The script checks configuration rendering, token-rotation persistence, Home Assistant metadata, the loopback proxy contract, disabled host-wide pruning, shell code, and the two-process lifecycle.

To verify the target images, build both supported architectures:

```sh
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg BUILD_VERSION=0.1.0 \
  --build-arg BUILD_ARCH=multiarch \
  --output type=cacheonly \
  doover_device
```

The Dockerfile starts the real Device Agent and App Controller without cloud access during the build. The build fails if either service does not become healthy.
