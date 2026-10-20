# CLAUDE.md

Software for a modular robot: a Raspberry Pi host coordinates Raspberry Pi
Pico modules (differential drive, claw) over USB. Read
[docs/DESIGN.md](docs/DESIGN.md) — the implementation brief and source of truth
for architecture and safety intent — and the applicable ADRs in
[docs/adr/](docs/adr/) before changing architecture, protocol, or safety
behavior. Setup, target status, and dependency maintenance are in
[docs/development.md](docs/development.md).

## Current milestone

Milestone 1 (skeleton and reproducible tools) is in place. The next milestone
is 2: protocol schema, generated codecs and docs, framing, sessions, tickets,
actions, and the portable safety state machine (DESIGN.md §12).

## Commands

```bash
./tools/bootstrap.sh     # pinned tools into .tools/, .venv/, web/node_modules/
make doctor              # verify the toolchain against tools/toolchain.lock.json
make lint                # ruff, mypy --strict, clang-format, prettier, boundaries
make host-test web-test firmware-test
make firmware BOARD=pico PROFILE=uncommissioned
make test                # everything; fails until milestone 2 targets exist
```

## Rules

- Implement the current milestone; do not add future transport/framework stubs
  merely because they are mentioned.
- Keep composition, domain logic, platform I/O, and presentation separate.
  Respect the include/import rules (DESIGN.md §4.3, `tools/check_boundaries.py`).
- Edit schema/profile/config at its defined source of truth. Never hand-edit
  generated codecs or protocol docs.
- Use explicit units, state/event names, and bounded ownership. No blocking
  work in control callbacks or host ticks.
- Do not invent hardware values. An uncommissioned profile must remain unable
  to arm.
- Add tests for changed behavior and safety invariants; avoid tests that only
  mirror private implementation.
- Run `make test` and affected firmware builds. Report hardware checks as
  pending until actually performed.
- Protocol/safety/platform changes update the appropriate ADR, docs, migration
  notes, and acceptance evidence.
- Never turn a failed test into a passing stub, weaken a safety guard to finish
  a milestone, or claim a measured bound without measurements.
- Unimplemented targets and modes exit nonzero with the milestone that
  implements them; keep it that way until they are real.
- Dependencies change only through `tools/toolchain.lock.json`, the Python and
  npm lock files, and submodule commits (see docs/development.md).
