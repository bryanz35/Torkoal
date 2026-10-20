add_executable(toolchain_smoke toolchain_smoke.c)
target_link_libraries(toolchain_smoke PRIVATE pico_stdlib)
# SDK sources compile inside this target, so keep strict warnings on ours.
set_source_files_properties(toolchain_smoke.c PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Werror")
# No debug output may share the binary CDC link (DESIGN §6.1); this image has none.
pico_enable_stdio_usb(toolchain_smoke 0)
pico_enable_stdio_uart(toolchain_smoke 0)
pico_add_extra_outputs(toolchain_smoke)
