#!/usr/bin/env bash
# Prepare a checkout for development and CI (docs/DESIGN.md §10.1).
#
# Installs only what tools/toolchain.lock.json pins. Tool archives are
# SHA-256 verified, Python packages come from hashed lock files as prebuilt
# wheels, and npm uses `npm ci`. Nothing is resolved at install time.
# Everything lands in .tools/ and .venv/; nothing is installed system-wide.
#
# Usage: tools/bootstrap.sh [python] [web] [firmware]    (default: all three)
#
# Requires: bash, git, curl, tar, xz, unzip, sha256sum, python3 (any 3.10+,
# used only to read the lock file), and a native C/C++ compiler for picotool.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lock="$repo_root/tools/toolchain.lock.json"
tools_dir="$repo_root/.tools"
downloads="$tools_dir/downloads"
venv="$repo_root/.venv"

die() {
    echo "bootstrap: error: $*" >&2
    exit 1
}

step() {
    echo "bootstrap: $*"
}

# Print one value from the lock file. Arguments form the key path.
lock_get() {
    python3 - "$lock" "$@" <<'EOF'
import json, sys
value = json.load(open(sys.argv[1]))
for key in sys.argv[2:]:
    value = value[key]
print("" if value is None else value)
EOF
}

detect_platform() {
    case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) echo linux-x86_64 ;;
    Linux-aarch64 | Linux-arm64) echo linux-aarch64 ;;
    *) die "unsupported development host $(uname -s)-$(uname -m); supported: $(lock_get platforms)" ;;
    esac
}

# Download, verify, and unpack one archive tool into .tools/<name>-<version>,
# then link its executables into .tools/bin.
fetch_tool() {
    local name="$1"
    local version url sha bin_dir dest archive
    version="$(lock_get tools "$name" version)"
    url="$(lock_get tools "$name" archives "$platform" url)"
    sha="$(lock_get tools "$name" archives "$platform" sha256)"
    bin_dir="$(lock_get tools "$name" bin_dir)"
    dest="$tools_dir/$name-$version"
    archive="$downloads/$(basename "$url")"

    if [[ ! -f "$dest/.installed" ]]; then
        mkdir -p "$downloads"
        if [[ ! -f "$archive" ]] || ! echo "$sha  $archive" | sha256sum --check --status; then
            step "downloading $name $version"
            curl --fail --silent --show-error --location --retry 3 --output "$archive.part" "$url"
            mv "$archive.part" "$archive"
        fi
        echo "$sha  $archive" | sha256sum --check --status ||
            die "checksum mismatch for $archive; expected $sha (delete the file to retry)"

        step "unpacking $name $version"
        rm -rf "$dest"
        mkdir -p "$dest"
        case "$archive" in
        *.tar.gz | *.tar.xz) tar -xf "$archive" -C "$dest" --strip-components=1 ;;
        *.zip) unzip -q "$archive" -d "$dest" ;;
        *) die "unknown archive type: $archive" ;;
        esac
        touch "$dest/.installed"
    fi

    if [[ -n "$bin_dir" ]]; then
        mkdir -p "$tools_dir/bin"
        local exe
        for exe in "$dest/$bin_dir"/*; do
            if [[ -f "$exe" && -x "$exe" ]]; then
                ln -sfn "$exe" "$tools_dir/bin/$(basename "$exe")"
            fi
        done
    fi
    ln -sfn "$dest" "$tools_dir/$name"
}

check_submodules() {
    local path
    for path in firmware/external/pico-sdk firmware/external/picotool firmware/external/unity; do
        if [[ ! -e "$repo_root/$path/.git" ]]; then
            step "initializing submodule $path"
            git -C "$repo_root" submodule update --init --recursive -- "$path"
        fi
    done
}

setup_python() {
    fetch_tool cpython
    local python="$tools_dir/cpython/bin/python3"
    local dev_lock="$repo_root/$(lock_get python locks dev)"
    local lock_sum
    lock_sum="$(sha256sum "$dev_lock" | cut -d' ' -f1)"

    # Recreate the environment whenever the interpreter or lock changes so no
    # package outside the lock survives an upgrade.
    if [[ ! -x "$venv/bin/python" ]] ||
        [[ "$(cat "$venv/.robot-lock-sha256" 2>/dev/null)" != "$lock_sum" ]] ||
        [[ "$("$venv/bin/python" --version 2>&1)" != "Python $(lock_get tools cpython version)" ]]; then
        step "creating .venv from $(lock_get python locks dev)"
        rm -rf "$venv"
        "$python" -m venv "$venv"
        "$venv/bin/python" -m pip install --quiet --disable-pip-version-check --no-input \
            --require-hashes --no-deps --only-binary :all: -r "$dev_lock"
        echo "$lock_sum" >"$venv/.robot-lock-sha256"
    fi

    step "installing robot-host (editable)"
    "$venv/bin/python" -m pip install --quiet --disable-pip-version-check --no-input \
        --no-deps --no-build-isolation --no-index --editable "$repo_root/host"
}

setup_web() {
    fetch_tool nodejs
    local lockfile="$repo_root/$(lock_get web lockfile)"
    [[ -f "$lockfile" ]] || die "$lockfile is missing; maintainers create it with 'make lock-web'"
    step "installing web dependencies (npm ci)"
    (cd "$repo_root/web" && PATH="$tools_dir/bin:$PATH" npm ci --ignore-scripts --no-audit --no-fund --loglevel=error)
}

setup_firmware() {
    fetch_tool cmake
    fetch_tool ninja
    fetch_tool arm-gnu-toolchain

    # The Pico SDK fetches picotool from the network when it cannot find one,
    # which would bypass the pins. Build the pinned submodule instead; USB
    # support is not needed to produce UF2 images.
    local prefix="$repo_root/$(lock_get built_tools picotool install_dir)"
    local commit
    commit="$(git -C "$repo_root/firmware/external/picotool" rev-parse HEAD)"
    if [[ "$(cat "$prefix/.installed" 2>/dev/null)" != "$commit" ]]; then
        step "building picotool $(lock_get submodules firmware/external/picotool version)"
        local build="$tools_dir/build/picotool"
        rm -rf "$build" "$prefix"
        PATH="$tools_dir/bin:$PATH" cmake -S "$repo_root/firmware/external/picotool" -B "$build" \
            -G Ninja -Wno-dev \
            -DCMAKE_BUILD_TYPE=Release \
            -DPICO_SDK_PATH="$repo_root/firmware/external/pico-sdk" \
            -DPICOTOOL_NO_LIBUSB=1 \
            -DPICOTOOL_FLAT_INSTALL=1 \
            -DCMAKE_INSTALL_PREFIX="$prefix" >/dev/null
        PATH="$tools_dir/bin:$PATH" cmake --build "$build" >/dev/null
        PATH="$tools_dir/bin:$PATH" cmake --install "$build" >/dev/null
        echo "$commit" >"$prefix/.installed"
    fi
}

main() {
    local components=("$@")
    if [[ ${#components[@]} -eq 0 ]]; then
        components=(python web firmware)
    fi
    for component in "${components[@]}"; do
        case "$component" in
        python | web | firmware) ;;
        *) die "unknown component '$component'; expected python, web, or firmware" ;;
        esac
    done

    command -v python3 >/dev/null || die "python3 is required to read $lock"
    platform="$(detect_platform)"
    check_submodules

    for component in "${components[@]}"; do
        "setup_$component"
    done

    step "done; run 'make doctor' to verify"
}

main "$@"
