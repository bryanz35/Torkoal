# Native unit tests for portable firmware code (docs/DESIGN.md §10.1).
#
# A separate project from the cross-build: it uses the host compiler and must
# never see the Pico SDK or the Arm toolchain. Build with `make firmware-test`.
cmake_minimum_required(VERSION 3.20)
project(robot_firmware_native_tests C)

if(CMAKE_C_COMPILER MATCHES "arm-none-eabi" OR DEFINED PICO_SDK_PATH)
    message(FATAL_ERROR "native tests must use the host compiler, not the Pico cross toolchain")
endif()

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

set(UNITY_DIR "${CMAKE_CURRENT_LIST_DIR}/../external/unity")
add_library(unity STATIC "${UNITY_DIR}/src/unity.c")
target_include_directories(unity SYSTEM PUBLIC "${UNITY_DIR}/src")

enable_testing()

function(robot_native_test name)
    add_executable(${name} ${name}.c)
    target_compile_options(${name} PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(${name} PRIVATE unity)
    add_test(NAME ${name} COMMAND ${name})
endfunction()

robot_native_test(test_native_harness)
