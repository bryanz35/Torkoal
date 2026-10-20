# Default profile for compilation, simulation, and CI. It describes no real
# hardware: it carries no pins, gains, calibration, or limits, and module
# firmware built with it must refuse physical Arm (docs/DESIGN.md §2, §7.3).
set(ROBOT_PROFILE_COMMISSIONED FALSE)
