# Architecture decision records

An ADR is required when changing a safety invariant, a transport or command
contract, a dependency boundary, a supported platform, or a protocol
compatibility policy (`docs/DESIGN.md` §4.4). Ordinary internal refactors do
not need one.

Name files `NNNN-short-title.md`, numbered in order, and never renumber or
delete an accepted ADR; supersede it with a new one instead.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-toolchain-provisioning.md) | Toolchain provisioning and dependency pinning | Accepted |

## Template

```markdown
# NNNN. Title

Status: Proposed | Accepted | Superseded by NNNN
Date: YYYY-MM-DD

## Context
What forces the decision, with references to docs/DESIGN.md sections.

## Decision
What we will do.

## Alternatives considered
Each option and why it was not chosen.

## Consequences
Compatibility impact, costs, and what becomes easier or harder.

## Migration and rollback
How to adopt the change, and how to undo it.

## Validation
Tests, builds, or bench evidence that show the decision holds.
```
