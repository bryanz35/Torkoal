# Modular robot

A Raspberry Pi coordinates self-contained Raspberry Pi Pico modules — a
differential-drive base and a claw — over USB. The Pi handles operator access
and coordination; each Pico owns its sensors, actuator control, hard limits,
and local failure response. A physical E-stop removes actuator power
independently of all software.

**Status:** milestone 1 of 6 (repository skeleton and reproducible tools). There
is no robot behavior yet: no protocol, module firmware, host control, or
operator UI. Nothing here has been validated on hardware.

## Quick start

```bash
git clone --recurse-submodules <repository-url> robot
cd robot
./tools/bootstrap.sh
make doctor
make lint host-test web-test firmware-test
make firmware BOARD=pico PROFILE=uncommissioned
```

## Documentation

- [docs/DESIGN.md](docs/DESIGN.md) — architecture, safety contract, protocol,
  and milestones
- [docs/development.md](docs/development.md) — setup, command status, and
  dependency maintenance
- [docs/adr/](docs/adr/) — architecture decision records

## Layout

| Path | Purpose |
| --- | --- |
| `firmware/` | Pico firmware (C11, Pico SDK) and native unit tests |
| `host/` | Raspberry Pi coordinator (Python 3.12) |
| `web/` | Browser operator interface (TypeScript, Vite) |
| `tools/` | Bootstrap, doctor, checks, toolchain lock, CI container |
| `docs/` | Design, development guide, ADRs |
