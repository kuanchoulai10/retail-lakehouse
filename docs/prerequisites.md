# Prerequisites

This page lists the macOS host requirements and tools needed before running `task onboard`. Once they're installed, head to [Deployment](deployment.md) to bring the stack up.

## Hardware

This project is developed and tested on a Mac mini (2024) with the following specifications. They define the comfortable working envelope, not a hard floor — but the colima VM defaults (`CPU=9`, `MEMORY=28`, `DISK_SIZE=120`) assume a machine in this ballpark.

- Apple M4 chip
- 10-core CPU
- 10-core GPU
- 16-core Neural Engine
- 32 GB RAM
- 512 GB SSD

## Install required tools

Every tool below is checked by `task onboard` as a precondition; the bootstrap aborts early if anything is missing. Install them all in one go with [Homebrew](https://brew.sh/):

```bash
brew install \
  colima docker kubectl minikube helm sops git \
  python@3.13 uv jsonnet jsonnet-bundler gettext \
  openjdk@21 node
```

A few entries warrant a one-liner so the names line up with the binaries the preconditions check for:

- `gettext` provides the `envsubst` binary used for templating Kubernetes manifests.
- `openjdk@21` provides `keytool`, used to build Java truststores for Trino.
- `jsonnet-bundler` provides the `jb` binary for vendoring jsonnet libraries.
- `node` provides `npm`, used by the docs and commit-lint toolchains.

After installing, make sure `docker` is using the colima context once colima is started later (`docker context ls`).

## Next step

Tools installed? Continue to [Deployment](deployment.md).
