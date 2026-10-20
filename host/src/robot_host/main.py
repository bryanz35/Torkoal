"""Process entry point: composition and lifecycle only (docs/DESIGN.md §9).

Milestone 1 provides the command-line surface. Each operating mode exits
nonzero with an explanation until the milestone that implements it, so no
caller can mistake the scaffold for a running coordinator.
"""

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version

# Distinct from argparse's usage error (also 2) only by its message; callers
# should treat any nonzero status as "not running".
EXIT_NOT_IMPLEMENTED = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="robot-host",
        description="Coordinate robot modules and serve the operator interface.",
    )
    parser.add_argument(
        "--sim",
        action="store_true",
        help="run against simulated modules on loopback only (milestone 4)",
    )
    parser.add_argument("--version", action="version", version=version("robot-host"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.sim:
        reason = "simulation mode is not implemented yet (milestone 4: host core and simulation)"
    else:
        reason = "hardware mode is not implemented yet (milestones 4-6)"
    print(f"robot-host: {reason}", file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":
    sys.exit(main())
