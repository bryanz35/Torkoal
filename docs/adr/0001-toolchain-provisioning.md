# 0001. Toolchain provisioning and dependency pinning

Status: Accepted
Date: 2026-10-20

## Context

`docs/DESIGN.md` §2 selects the v1 baseline (Pico SDK 2.2.0, Arm GNU Toolchain
13.2.Rel1, Python 3.12, Node.js 22, CMake/Ninja) and requires milestone 1 to
commit exact patch versions, archive checksums, the SDK submodule commit,
Python and npm locks, and a CI container digest in `tools/toolchain.lock.json`.
It leaves the provisioning mechanics to this milestone.

## Decision

1. **Archive tools.** `tools/bootstrap.sh` downloads official release archives
   into `.tools/` and verifies each SHA-256 from the lock before unpacking:
   Arm GNU Toolchain 13.2.Rel1, CMake 3.31.12, Ninja 1.13.2, Node.js 22.23.3
   (bundling npm 10.9.9), and CPython 3.12.15 from python-build-standalone
   release 20261003. Nothing is installed system-wide. Supported development
   hosts are Linux x86_64 and aarch64.
2. **CMake 3.31.** CMake is pinned to the last 3.x series rather than 4.x to
   keep policy compatibility with the SDK and picotool CMake files.
3. **picotool.** The Pico SDK downloads picotool from the network when none is
   found, which would bypass the pins. picotool 2.2.0 is therefore a submodule
   (`firmware/external/picotool`) built by bootstrap without libusb (enough to
   produce UF2 images). The firmware CMake project refuses to configure unless
   `picotool_DIR` is set, and also forbids `PICO_SDK_FETCH_FROM_GIT`.
4. **Unity.** Unity v2.6.1 is a submodule (`firmware/external/unity`) used only
   by the native test project.
5. **Python dependencies.** `host/requirements.lock` and
   `host/requirements-dev.lock` are produced by `uv pip compile --universal
   --generate-hashes` with `--exclude-newer` set to the cutoff recorded in the
   lock file. Bootstrap installs them with `pip --require-hashes --no-deps
   --only-binary :all:`, then installs the host package editable with
   `--no-build-isolation --no-index` (hatchling is in the dev lock). uv is a
   maintainer tool for regenerating locks only; its version is recorded.
6. **PyYAML.** The baseline lists no YAML parser, but §8.3 specifies YAML
   runtime configuration validated by Pydantic. PyYAML is added as a runtime
   dependency for that purpose.
7. **npm.** `web/package-lock.json` is installed with `npm ci --ignore-scripts`.
   npm 10.9.9 crashes while resolving Vitest's optional peer set, so
   `web/.npmrc` sets `legacy-peer-deps=true`; the one required peer (vite) is a
   direct dev dependency.
8. **CI container.** `tools/Dockerfile.ci` starts from `ubuntu:24.04` pinned by
   index digest and installs OS packages from a fixed Ubuntu archive snapshot.
   The image is built in each CI job; there is no registry yet, so the digest
   recorded in the lock is the base image's. Once the image is published to a
   registry, record the published image digest and run CI on it directly.
9. **Version cutoff.** New pins prefer releases at least about two weeks old at
   lock time, to reduce exposure to compromised or quickly-yanked releases.

## Alternatives considered

- **System packages / apt toolchains.** Versions differ by distribution and
  drift with updates; rejected for reproducibility.
- **Letting the SDK fetch picotool.** Simple, but downloads at configure time
  outside the lock; rejected.
- **uv for installation.** Faster, but would make uv a required pinned tool for
  every developer; pip with hashes is sufficient and ships with the pinned
  CPython.
- **Generating npm locks with a newer npm.** Avoids the peer-set crash but makes
  the lockfile depend on a tool outside the pins; rejected.

## Consequences

- A clean checkout needs network access once (or a prefilled `.tools/downloads`
  cache and package caches) and about 3 GB of disk: roughly 0.8 GB for the
  submodules and 2.1 GB for `.tools/` (mostly the Arm toolchain and its
  downloaded archive).
- macOS and Windows hosts are not supported for native development.
- Bumping any pin is an explicit edit to `tools/toolchain.lock.json` (and the
  relevant lock file), verified by `make doctor` and CI.

## Migration and rollback

Changing a pin: edit the lock entry (version, URL, checksum or commit), update
the submodule or lock file, re-run `./tools/bootstrap.sh`, `make doctor`, and
the affected tests and builds. Rollback is reverting that commit and
re-running bootstrap; old tool directories in `.tools/` are versioned and can
be deleted.

## Validation

`make doctor` passes; `make lint host-test web-test web-build firmware-test`
pass; `make firmware BOARD=pico PROFILE=uncommissioned` produces an RP2040
UF2; the same sequence passes in the CI container from a copy of the checkout
with no `.tools/`, `.venv/`, or `node_modules/`.
