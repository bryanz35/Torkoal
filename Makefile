# Developer and CI command interface (docs/DESIGN.md §10.1).
#
# Run ./tools/bootstrap.sh first. Targets owned by a later milestone exit
# nonzero with an explanation instead of pretending to pass; the status table
# lives in docs/development.md.

SHELL := bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help
.DELETE_ON_ERROR:
MAKEFLAGS += --no-builtin-rules --no-print-directory

# Pinned tools from tools/bootstrap.sh take precedence over system tools.
export PATH := $(CURDIR)/.tools/bin:$(PATH)

VENV := $(CURDIR)/.venv
PY := $(VENV)/bin/python
LOCK := tools/toolchain.lock.json
lock_get = $(shell python3 -c 'import json,sys; v=json.load(open("$(LOCK)")); [v := v[k] for k in sys.argv[1:]]; print(v)' $(1))

BOARD ?= pico
PROFILE ?= uncommissioned
SUPPORTED_BOARDS := pico
FIRMWARE_BUILD := build/firmware/$(BOARD)/$(PROFILE)
NATIVE_BUILD := build/native-tests
PICOTOOL_DIR := $(CURDIR)/.tools/picotool/picotool
NATIVE_CC ?= cc

PYTHON_PATHS := host/src host/tests tools
C_SOURCES = $(shell find firmware -path firmware/external -prune -o \( -name '*.c' -o -name '*.h' \) -print | sort)

# $(call pending,<milestone and reason>)
define pending
	@echo "make $@: not implemented yet ($(1))." >&2
	@echo "See the target status table in docs/development.md." >&2
	@exit 2
endef

.PHONY: help
help:
	@echo "Setup:     ./tools/bootstrap.sh [python] [web] [firmware]; then make doctor"
	@echo ""
	@echo "  doctor          verify pinned tools, submodules, and dependency locks"
	@echo "  test            all hardware-free checks (fails while protocol targets are pending)"
	@echo "  lint            read-only style, typing, and boundary checks"
	@echo "  format          rewrite Python, C, and web sources in place"
	@echo "  host-test       Python host tests"
	@echo "  web-test        strict TypeScript check and browser-logic tests"
	@echo "  web-build       production build of the operator UI into web/dist"
	@echo "  firmware-test   native C unit tests (no cross compiler)"
	@echo "  firmware        cross-build UF2s: BOARD=$(BOARD) PROFILE=$(PROFILE)"
	@echo "  gen, gen-check, protocol-test   protocol generation (milestone 2)"
	@echo "  package, flash, deploy          release and hardware (milestones 3-6)"
	@echo "  lock-python, lock-web           regenerate dependency locks (maintainers)"
	@echo "  clean           remove build outputs"

# --- Environment guards --------------------------------------------------------

.PHONY: require-python require-web require-firmware
require-python:
	@test -x "$(PY)" || { echo "error: .venv missing; run ./tools/bootstrap.sh python" >&2; exit 1; }
require-web:
	@test -d web/node_modules || { echo "error: web/node_modules missing; run ./tools/bootstrap.sh web" >&2; exit 1; }
require-firmware:
	@test -f "$(PICOTOOL_DIR)/picotoolConfig.cmake" || { echo "error: firmware tools missing; run ./tools/bootstrap.sh firmware" >&2; exit 1; }

.PHONY: doctor
doctor:
	@python3 tools/doctor.py

# --- Protocol (milestone 2) ----------------------------------------------------

.PHONY: gen gen-check protocol-test
gen gen-check protocol-test:
	$(call pending,milestone 2 adds protocol/messages.yaml and its generator)

# --- Style ---------------------------------------------------------------------

.PHONY: format format-python format-c format-web
format: format-python format-c format-web
format-python: require-python
	$(PY) -m ruff format $(PYTHON_PATHS)
	$(PY) -m ruff check --fix $(PYTHON_PATHS)
format-c: require-python
	$(VENV)/bin/clang-format -i $(C_SOURCES)
format-web: require-web
	cd web && npm run --silent format

.PHONY: lint lint-python lint-c lint-web lint-boundaries
lint: lint-python lint-c lint-web lint-boundaries
lint-python: require-python
	$(PY) -m ruff format --check $(PYTHON_PATHS)
	$(PY) -m ruff check $(PYTHON_PATHS)
	$(PY) -m mypy --config-file host/pyproject.toml $(PYTHON_PATHS)
lint-c: require-python
	$(VENV)/bin/clang-format --dry-run -Werror $(C_SOURCES)
lint-web: require-web
	cd web && npm run --silent format:check
lint-boundaries: require-python
	$(PY) tools/check_boundaries.py

# --- Tests ---------------------------------------------------------------------

.PHONY: host-test web-test web-build firmware-test
host-test: require-python
	$(PY) -m pytest -c host/pyproject.toml --rootdir=. host/tests tools/tests

web-test: require-web
	cd web && npm run --silent typecheck && npm test

web-build: require-web
	cd web && npm run --silent build

# Native tests use the host compiler in their own build tree; CC/CFLAGS from
# a cross-compiling shell must not leak in.
firmware-test: require-firmware
	env -u CC -u CFLAGS cmake -S firmware/tests -B $(NATIVE_BUILD) -G Ninja \
		-DCMAKE_C_COMPILER=$(NATIVE_CC) -DCMAKE_BUILD_TYPE=Debug >/dev/null
	cmake --build $(NATIVE_BUILD)
	ctest --test-dir $(NATIVE_BUILD) --output-on-failure

# Implemented checks run first so their results are visible before the
# pending protocol targets fail.
.PHONY: test
test: lint host-test web-test firmware-test gen-check protocol-test

# --- Firmware cross-build --------------------------------------------------------

.PHONY: firmware
firmware: require-firmware require-python
	@if [[ " $(SUPPORTED_BOARDS) " != *" $(BOARD) "* ]]; then \
		echo "error: BOARD=$(BOARD) is not supported (supported: $(SUPPORTED_BOARDS))" >&2; exit 1; fi
	@test -f firmware/profiles/$(PROFILE)/profile.cmake || { \
		echo "error: PROFILE=$(PROFILE) has no firmware/profiles/$(PROFILE)/profile.cmake" >&2; exit 1; }
	cmake -S firmware -B $(FIRMWARE_BUILD) -G Ninja -DCMAKE_BUILD_TYPE=Release \
		-DPICO_BOARD=$(BOARD) -DROBOT_PROFILE=$(PROFILE) -Dpicotool_DIR=$(PICOTOOL_DIR) \
		-DPython3_EXECUTABLE=$(PY)
	cmake --build $(FIRMWARE_BUILD)
	@echo "UF2 images:" && find $(FIRMWARE_BUILD) -name '*.uf2' -not -path '*/_deps/*' | sort

# --- Release and hardware (later milestones) -------------------------------------

.PHONY: package flash deploy
package:
	$(call pending,the release manifest needs the protocol major from milestone 2 and profile identity from milestone 3; packaged UI assets arrive in milestone 5)
flash:
	$(call pending,milestone 3 adds tools/flash.py with explicit MODULE/UID/PROFILE selection)
deploy:
	$(call pending,milestone 6 adds the installer and deployment procedure)

# --- Dependency locks (maintainers) ------------------------------------------------

UV_VERSION = $(call lock_get,python lock_tool version)
EXCLUDE_NEWER = $(call lock_get,python exclude_newer)
UV_COMPILE = uv pip compile host/pyproject.toml --universal --python-version 3.12 \
	--generate-hashes --exclude-newer $(EXCLUDE_NEWER) --custom-compile-command "make lock-python" --quiet

.PHONY: lock-python lock-web
lock-python:
	@uv --version | grep -qF "uv $(UV_VERSION)" || { \
		echo "error: lock-python needs uv $(UV_VERSION) (tools/toolchain.lock.json)" >&2; exit 1; }
	$(UV_COMPILE) -o host/requirements.lock
	$(UV_COMPILE) --group host/pyproject.toml:dev -o host/requirements-dev.lock
	@echo "Re-run ./tools/bootstrap.sh python to install the new lock."

lock-web:
	@test -x .tools/bin/npm || { echo "error: pinned Node missing; run ./tools/bootstrap.sh web" >&2; exit 1; }
	cd web && rm -rf node_modules package-lock.json && npm install --ignore-scripts --no-audit --no-fund

.PHONY: clean
clean:
	rm -rf build dist web/dist
