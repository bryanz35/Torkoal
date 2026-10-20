# Cross-build for Pico module firmware (docs/DESIGN.md §7, §10.1).
#
# Configure through `make firmware BOARD=<board> PROFILE=<profile>`, which
# selects build/firmware/<board>/<profile>/ and the pinned picotool. Native
# unit tests are a separate project in tests/ and never share this build.
cmake_minimum_required(VERSION 3.13...3.31)

# Always use the pinned submodule; never an SDK from the environment or the
# network.
set(PICO_SDK_PATH "${CMAKE_CURRENT_LIST_DIR}/external/pico-sdk")
if(PICO_SDK_FETCH_FROM_GIT OR DEFINED ENV{PICO_SDK_FETCH_FROM_GIT})
    message(FATAL_ERROR "PICO_SDK_FETCH_FROM_GIT is not allowed; the SDK is a pinned submodule")
endif()

# Without a prebuilt picotool the SDK downloads one, bypassing the pins in
# tools/toolchain.lock.json. tools/bootstrap.sh builds the pinned submodule.
if(NOT picotool_DIR)
    message(FATAL_ERROR "picotool_DIR is not set; run ./tools/bootstrap.sh firmware and build "
                        "with `make firmware`")
endif()

set(ROBOT_SUPPORTED_BOARDS pico)
if(NOT PICO_BOARD IN_LIST ROBOT_SUPPORTED_BOARDS)
    message(FATAL_ERROR "PICO_BOARD='${PICO_BOARD}' is not a supported v1 target "
                        "(supported: ${ROBOT_SUPPORTED_BOARDS}; see docs/DESIGN.md §2)")
endif()

include(pico_sdk_import.cmake)

project(robot_firmware C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

pico_sdk_init()

# Each profile directory owns its physical calibration and hard bounds
# (profiles/README.md). Every profile must declare whether it is commissioned.
set(ROBOT_PROFILE "" CACHE STRING "Hardware profile directory under firmware/profiles/")
set(ROBOT_PROFILE_DIR "${CMAKE_CURRENT_LIST_DIR}/profiles/${ROBOT_PROFILE}")
if(NOT ROBOT_PROFILE OR NOT EXISTS "${ROBOT_PROFILE_DIR}/profile.cmake")
    message(FATAL_ERROR "ROBOT_PROFILE='${ROBOT_PROFILE}' has no profiles/<name>/profile.cmake")
endif()
unset(ROBOT_PROFILE_COMMISSIONED)
include("${ROBOT_PROFILE_DIR}/profile.cmake")
if(NOT DEFINED ROBOT_PROFILE_COMMISSIONED)
    message(FATAL_ERROR "profile '${ROBOT_PROFILE}' must set ROBOT_PROFILE_COMMISSIONED")
endif()
message(STATUS "Robot profile: ${ROBOT_PROFILE} (commissioned: ${ROBOT_PROFILE_COMMISSIONED})")

add_subdirectory(platform/pico)
