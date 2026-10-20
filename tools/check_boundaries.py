"""Enforce the include/import dependency rules of docs/DESIGN.md §4.3.

Firmware:
- Only firmware/platform/ and firmware/hal/ may include Pico SDK headers.
- A module under firmware/modules/<name>/ may not include another module.

Host (robot_host):
- api/ never imports transports, links, or module drivers; it submits events.
- control/ and modules/ never import transports or serial libraries.
- Only transport/ imports serial libraries.

Directories that do not exist yet are simply skipped, so the rules apply as
soon as code arrives. Exit status is 1 when any violation is found.
"""

import argparse
import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', re.MULTILINE)

# Include prefixes that belong to the Pico SDK or its bundled libraries.
SDK_INCLUDE_PREFIXES = (
    "pico/",
    "pico.h",
    "hardware/",
    "boards/",
    "tusb",
    "class/",
    "cyw43",
    "lwip/",
    "btstack",
    "mbedtls/",
)
SDK_ALLOWED_DIRS = ("platform", "hal", "external")

SERIAL_MODULES = ("serial", "serial_asyncio")
HOST_FORBIDDEN_IMPORTS: dict[str, tuple[str, ...]] = {
    "api": ("robot_host.transport", "robot_host.link", "robot_host.modules", *SERIAL_MODULES),
    "control": ("robot_host.transport", *SERIAL_MODULES),
    "modules": ("robot_host.transport", *SERIAL_MODULES),
}


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check_firmware(repo_root: Path) -> Iterator[Violation]:
    firmware = repo_root / "firmware"
    if not firmware.is_dir():
        return
    for path in sorted(firmware.rglob("*")):
        if path.suffix not in (".c", ".h") or not path.is_file():
            continue
        rel = path.relative_to(firmware)
        top = rel.parts[0]
        if top == "external":
            continue
        text = path.read_text(encoding="utf-8")
        for match in INCLUDE_RE.finditer(text):
            header = match.group(1)
            line = _line_of(text, match.start())
            if top not in SDK_ALLOWED_DIRS and header.startswith(SDK_INCLUDE_PREFIXES):
                yield Violation(
                    path.relative_to(repo_root),
                    line,
                    f"SDK header <{header}> outside firmware/platform or firmware/hal",
                )
            if top == "modules" and len(rel.parts) > 2:
                own = rel.parts[1]
                for other in _module_names(firmware) - {own}:
                    if f"modules/{other}/" in header or header.startswith(f"../{other}/"):
                        yield Violation(
                            path.relative_to(repo_root),
                            line,
                            f"module '{own}' includes module '{other}' ({header})",
                        )


def _module_names(firmware: Path) -> set[str]:
    modules = firmware / "modules"
    return {p.name for p in modules.iterdir() if p.is_dir()} if modules.is_dir() else set()


def _imported_modules(tree: ast.Module, package: str) -> Iterator[tuple[int, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - node.level + 1]
                name = ".".join([*base, node.module] if node.module else base)
            else:
                name = node.module or ""
            yield node.lineno, name
            # `from robot_host import transport` imports a subpackage too.
            for alias in node.names:
                yield node.lineno, f"{name}.{alias.name}"


def _matches(name: str, forbidden: str) -> bool:
    return name == forbidden or name.startswith(forbidden + ".")


def check_host(repo_root: Path) -> Iterator[Violation]:
    src = repo_root / "host" / "src"
    package_root = src / "robot_host"
    if not package_root.is_dir():
        return
    for path in sorted(package_root.rglob("*.py")):
        rel = path.relative_to(src)
        parts = rel.with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        package = ".".join(parts if path.name == "__init__.py" else parts[:-1])
        layer = rel.parts[1] if len(rel.parts) > 2 else None
        forbidden = HOST_FORBIDDEN_IMPORTS.get(layer or "", ())
        allow_serial = layer == "transport"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line, name in _imported_modules(tree, package):
            for rule in forbidden:
                if _matches(name, rule):
                    yield Violation(
                        path.relative_to(repo_root), line, f"robot_host.{layer} imports {name}"
                    )
            if (
                not allow_serial
                and not forbidden
                and any(_matches(name, s) for s in SERIAL_MODULES)
            ):
                yield Violation(
                    path.relative_to(repo_root),
                    line,
                    f"{name} imported outside robot_host.transport",
                )


def check(repo_root: Path) -> list[Violation]:
    return [*check_firmware(repo_root), *check_host(repo_root)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check firmware/host dependency boundaries.")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent, help="repository root"
    )
    args = parser.parse_args(argv)
    violations = check(args.root)
    for violation in violations:
        print(violation, file=sys.stderr)
    if violations:
        print(f"check_boundaries: {len(violations)} violation(s)", file=sys.stderr)
        return 1
    print("check_boundaries: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
