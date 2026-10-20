"""Verify the local toolchain against tools/toolchain.lock.json (DESIGN §10.1).

Runs on any Python 3.10+ with only the standard library, before or after
bootstrap. Tools are resolved with .tools/bin first on PATH, exactly as the
Makefile resolves them, so a native setup passes only when the tools it would
actually use match the pins. Exit status is 1 when anything required fails.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = REPO_ROOT / "tools" / "toolchain.lock.json"
COMPONENTS = ("python", "web", "firmware")
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


@dataclass(frozen=True)
class Result:
    ok: bool
    name: str
    detail: str


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = f"{REPO_ROOT / '.tools' / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    return env


def _run(command: list[str]) -> tuple[bool, str]:
    executable = command[0]
    if "/" in executable:
        executable = str(REPO_ROOT / executable)
    elif shutil.which(executable, path=_env()["PATH"]) is None:
        return False, "not found"
    try:
        proc = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            env=_env(),
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, output


def check_commands(name: str, checks: list[dict[str, object]]) -> Iterator[Result]:
    for spec in checks:
        command = [str(part) for part in spec["command"]]  # type: ignore[attr-defined]
        expect = str(spec["expect"])
        ran, output = _run(command)
        first_line = output.splitlines()[0] if output else "no output"
        label = f"{name}: {' '.join(command)}"
        if ran and expect in output:
            yield Result(True, label, first_line)
        else:
            yield Result(False, label, f"expected '{expect}', got '{first_line}'")


def check_submodules(lock: dict[str, object]) -> Iterator[Result]:
    submodules: dict[str, dict[str, str]] = lock["submodules"]  # type: ignore[assignment]
    for path, pin in submodules.items():
        label = f"submodule {path}"
        ran, head = _run(["git", "-C", str(REPO_ROOT / path), "rev-parse", "HEAD"])
        _, staged = _run(["git", "-C", str(REPO_ROOT), "ls-files", "--stage", "--", path])
        recorded = staged.split()[1] if staged.startswith("160000") else "missing"
        if not ran:
            yield Result(False, label, "not checked out; run ./tools/bootstrap.sh")
        elif recorded != pin["commit"]:
            yield Result(
                False, label, f"superproject records {recorded}, lock pins {pin['commit']}"
            )
        elif head != pin["commit"]:
            yield Result(False, label, f"checked out {head}, lock pins {pin['commit']}")
        else:
            yield Result(True, label, f"{pin['version']} ({head[:12]})")


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def check_python_packages(lock: dict[str, object]) -> Iterator[Result]:
    locks: dict[str, str] = lock["python"]["locks"]  # type: ignore[index]
    dev_lock = REPO_ROOT / locks["dev"]
    pinned: dict[str, str] = {}
    conditional: set[str] = set()
    for line in dev_lock.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)\s*(;)?", line)
        if match:
            name = _normalize(match.group(1))
            pinned[name] = match.group(2)
            if match.group(3):
                conditional.add(name)

    label = f"python packages ({locks['dev']})"
    script = (
        "import importlib.metadata as m, json;"
        "print(json.dumps({d.metadata['Name']: d.version for d in m.distributions()}))"
    )
    ran, output = _run([str(VENV_PYTHON.relative_to(REPO_ROOT)), "-c", script])
    if not ran:
        yield Result(False, label, ".venv missing; run ./tools/bootstrap.sh python")
        return
    installed = {_normalize(k): v for k, v in json.loads(output).items()}
    problems = [
        f"{name} {installed[name]} != {version}"
        for name, version in pinned.items()
        if name in installed and installed[name] != version
    ]
    # A pin with an environment marker may legitimately be absent here.
    missing = [name for name in pinned if name not in installed and name not in conditional]
    extra = sorted(set(installed) - set(pinned) - {"pip", "robot-host"})
    problems += [f"{name} missing" for name in missing]
    problems += [f"{name} not in lock" for name in extra]
    if "robot-host" not in installed:
        problems.append("robot-host not installed")
    if problems:
        yield Result(False, label, "; ".join(problems))
    else:
        yield Result(True, label, f"{len(pinned)} pinned packages match")


def check_web_packages(lock: dict[str, object]) -> Iterator[Result]:
    lockfile = REPO_ROOT / lock["web"]["lockfile"]  # type: ignore[index]
    hidden = lockfile.parent / "node_modules" / ".package-lock.json"
    label = f"web packages ({lockfile.relative_to(REPO_ROOT)})"
    if not lockfile.is_file():
        yield Result(False, label, "lockfile missing; run make lock-web")
        return
    if not hidden.is_file():
        yield Result(False, label, "node_modules missing; run ./tools/bootstrap.sh web")
        return
    wanted = json.loads(lockfile.read_text(encoding="utf-8"))["packages"]
    have = json.loads(hidden.read_text(encoding="utf-8"))["packages"]
    problems = [
        f"{path} {have.get(path, {}).get('version', 'missing')} != {meta.get('version')}"
        for path, meta in wanted.items()
        if path
        and not meta.get("optional")
        and have.get(path, {}).get("version") != meta.get("version")
    ]
    if problems:
        yield Result(False, label, "; ".join(problems[:5]) + (" ..." if len(problems) > 5 else ""))
    else:
        yield Result(True, label, f"{len(have)} installed packages match")


def check_ci_container(lock: dict[str, object]) -> Iterator[Result]:
    ci: dict[str, str] = lock["ci_container"]  # type: ignore[assignment]
    dockerfile = (REPO_ROOT / ci["dockerfile"]).read_text(encoding="utf-8")
    label = f"ci container ({ci['dockerfile']})"
    missing = [value for value in (ci["base_image"], ci["apt_snapshot"]) if value not in dockerfile]
    if missing:
        yield Result(False, label, f"Dockerfile does not reference {', '.join(missing)}")
    else:
        yield Result(True, label, ci["base_image"].split("@")[1][:19])


def check_native_compiler() -> Iterator[Result]:
    ran, output = _run(["cc", "--version"])
    first_line = output.splitlines()[0] if output else "not found"
    yield Result(ran, "native C compiler (unpinned)", first_line)


def collect(lock: dict[str, object], components: tuple[str, ...]) -> Iterator[Result]:
    yield from check_ci_container(lock)
    tools: dict[str, dict[str, object]] = {
        **lock["tools"],  # type: ignore[dict-item]
        **lock["built_tools"],  # type: ignore[dict-item]
    }
    for name, spec in tools.items():
        if spec["component"] in components:
            yield from check_commands(name, spec["checks"])  # type: ignore[arg-type]
    if "python" in components:
        yield from check_python_packages(lock)
    if "web" in components:
        yield from check_web_packages(lock)
    if "firmware" in components:
        yield from check_submodules(lock)
        yield from check_native_compiler()


def lock_tool_note(lock: dict[str, object]) -> str:
    tool: dict[str, str] = lock["python"]["lock_tool"]  # type: ignore[index]
    ran, output = _run([tool["name"], "--version"])
    found = output.split()[1] if ran and len(output.split()) > 1 else "not found"
    return f"note: regenerating Python locks needs {tool['name']} {tool['version']} (found {found})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the pinned toolchain.")
    parser.add_argument(
        "--component",
        action="append",
        choices=COMPONENTS,
        help="limit checks to a bootstrap component (repeatable; default: all)",
    )
    args = parser.parse_args(argv)
    components = tuple(args.component or COMPONENTS)
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    failures = 0
    for result in collect(lock, components):
        failures += not result.ok
        print(f"{'ok  ' if result.ok else 'FAIL'}  {result.name}: {result.detail}")
    if "python" in components:
        print(lock_tool_note(lock))
    if failures:
        print(f"doctor: {failures} check(s) failed; see docs/development.md", file=sys.stderr)
        return 1
    print("doctor: toolchain matches tools/toolchain.lock.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
