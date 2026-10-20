# Development

How to set up a checkout, which commands work today, and how pinned
dependencies are maintained. Architecture and safety intent live in
[DESIGN.md](DESIGN.md); provisioning decisions in
[ADR 0001](adr/0001-toolchain-provisioning.md).

## Setup

Supported development hosts: Linux x86_64 and aarch64. Prerequisites are
`bash`, `git`, `curl`, `tar`, `xz`, `unzip`, `sha256sum`, `make`, a native
C/C++ compiler, and any `python3` 3.10+ (used only to read the lock file
before the pinned interpreter exists).

```bash
git clone --recurse-submodules <repository-url> robot
cd robot
./tools/bootstrap.sh            # or a subset: python, web, firmware
make doctor
```

Bootstrap installs only what `tools/toolchain.lock.json` pins, into `.tools/`
(tool archives, verified by SHA-256), `.venv/` (hashed Python lock), and
`web/node_modules/` (`npm ci`). It never resolves dependencies. Re-running it
is cheap; it recreates `.venv/` whenever the lock changes. The Makefile puts
`.tools/bin` first on `PATH`, and `make doctor` checks the tools that the
Makefile would actually use, so a native setup with matching system tools also
passes.

Offline builds need a prefilled `.tools/downloads/` (the archives named in the
lock), a pip wheel cache for `host/requirements-dev.lock`, and an npm cache for
`web/package-lock.json`.

To reproduce CI locally:

```bash
docker build --file tools/Dockerfile.ci --tag robot-ci tools
docker run --rm --volume "$PWD:/work" robot-ci bash -c './tools/bootstrap.sh && make doctor lint host-test web-test firmware-test firmware'
```

Optional git hooks: `.venv/bin/pre-commit install` (local hooks only; they run
the same `make lint-*` targets).

## Target status

Targets that belong to a later milestone exit with status 2 and say which
milestone implements them. None of them pretends to pass.

| Target | Status | Notes |
| --- | --- | --- |
| `make doctor` | Works | Tools, submodules, Python and npm installs, CI pins |
| `make lint` | Works | ruff, mypy `--strict`, clang-format, prettier, boundary checks |
| `make format` | Works | Rewrites Python, C, and web sources |
| `make host-test` | Works | CLI behavior and boundary-checker tests |
| `make web-test` | Works | Strict `tsc`; Vitest reports no browser-logic tests yet |
| `make web-build` | Works | Builds `web/dist/` |
| `make firmware-test` | Works | Native Unity harness smoke test in `build/native-tests/` |
| `make firmware BOARD=pico PROFILE=uncommissioned` | Works | Builds `toolchain_smoke.uf2` only; module images arrive in milestone 3 |
| `make gen`, `make gen-check`, `make protocol-test` | Milestone 2 | Schema, generator, golden vectors |
| `make test` | Fails until milestone 2 | Runs every implemented check first, then the pending protocol targets |
| `make flash` | Milestone 3 | Explicit module UID and profile |
| `make package` | Milestones 2–5 | Needs protocol major, profile identity, and packaged UI |
| `make deploy` | Milestone 6 | Installer and deployment procedure |
| `.venv/bin/robot-host --sim` | Milestone 4 | Exits 2 with an explanation |

CI (`.github/workflows/`) runs the working targets per component inside the CI
container. `release.yml` runs `make test` and `make package` and therefore
fails by design until those are implemented.

## Repository layout today

Only directories with real content exist; the full intended layout is in
[DESIGN.md §9](DESIGN.md#9-repository-structure). Directories such as
`protocol/`, `firmware/common/`, `firmware/modules/`, `host/src/robot_host/*/`,
and `deploy/` are created by the milestone that implements them.

| Path | Contents |
| --- | --- |
| `firmware/external/` | Pinned submodules: Pico SDK 2.2.0 (recursive), picotool 2.2.0, Unity v2.6.1 |
| `firmware/platform/pico/` | `toolchain_smoke` bring-up image (configures no GPIO) |
| `firmware/profiles/` | Profile contract; `uncommissioned` profile (no hardware values) |
| `firmware/tests/` | Separate native CMake project using Unity |
| `host/` | `robot-host` package, CLI entry point, locks |
| `web/` | Vite + TypeScript operator UI shell |
| `tools/` | Bootstrap, doctor, boundary checker, CI Dockerfile, toolchain lock |

## Dependency maintenance

Dependency updates are deliberate changes, never picked up during deployment.

- **Tool archives** (Arm, CMake, Ninja, Node.js, CPython): edit version, URL,
  and SHA-256 in `tools/toolchain.lock.json`, taking the checksum from the
  publisher's checksum file. Re-run bootstrap and `make doctor`.
- **Submodules**: check out the new commit inside the submodule, `git add` it,
  and update `submodules` in the lock. `make doctor` fails if the superproject
  gitlink, the checkout, and the lock disagree.
- **Python**: edit ranges in `host/pyproject.toml`, move `python.exclude_newer`
  in the lock if newer releases are wanted, then `make lock-python` (requires
  the uv version recorded in the lock) and `./tools/bootstrap.sh python`.
- **npm**: edit exact versions in `web/package.json`, then `make lock-web`.
- **CI container**: update the digest and apt snapshot in both
  `tools/Dockerfile.ci` and the lock; `make doctor` checks they match.
- **GitHub Actions**: pin by full commit SHA with the tag in a comment.

Record the rationale in the commit message, or in an ADR when the change
affects a supported platform or boundary (DESIGN.md §4.4). Run the affected
tests; firmware toolchain changes also need the affected cross-builds.
