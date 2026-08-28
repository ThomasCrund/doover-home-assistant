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

The script checks configuration rendering, credential-safe image pulls, token-rotation persistence, Home Assistant metadata, the managed-container and loopback proxy contracts, disabled host-wide pruning, and shell code.

To verify the target images, build both supported architectures:

```sh
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg BUILD_VERSION=0.2.0 \
  --build-arg BUILD_ARCH=multiarch \
  --output type=cacheonly \
  doover_device
```

The build uses only a public bootstrap image. At runtime, the app uses the configured Docker Hub access token to pull the digest-pinned private Device Agent and App Controller images.
