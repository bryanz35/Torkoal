# Hardware profiles

A profile is the compiled source of truth for one physical build: pin
assignments, enable polarity, electrical safe defaults, PWM frequency,
encoder direction and count definition, ADC conversion, physical dimensions,
gains, hard limits, and power/E-stop input behavior (`docs/DESIGN.md` §7.3).
Runtime YAML may only tighten operational limits below these bounds.

Each profile lives in `firmware/profiles/<name>/` and is selected with
`make firmware PROFILE=<name>`. Today a profile contains only `profile.cmake`,
which must set `ROBOT_PROFILE_COMMISSIONED`. The full profile contract (C
header layout, profile ID and revision reported in `Identity`) arrives with
milestone 3.

| Profile | Commissioned | Purpose |
| --- | --- | --- |
| `uncommissioned` | No | Builds and simulates; must refuse physical Arm |

## Adding a commissioned profile

Do not invent values. Every number must come from the actual hardware:
datasheets, measured calibration, and bench results. A commissioned profile
needs a reviewed entry in `docs/wiring.md`, a completed acceptance record
(`docs/acceptance.md`), and the hardware gates of `docs/DESIGN.md` §13
resolved. Counts-per-revolution must state whether quadrature multiplication
is included and whether the count is motor-side or wheel-side.
