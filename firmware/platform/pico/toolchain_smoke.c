// Toolchain bring-up image (milestone 1).
//
// Proves that the pinned SDK, Arm toolchain, and picotool produce a UF2 for
// the selected board. It is not a robot module: it speaks no protocol and
// configures no GPIO, so every pin keeps its reset default (input, outputs
// disabled). It never feeds or enables the watchdog.
#include "pico/stdlib.h"

int main(void) {
    for (;;) {
        tight_loop_contents();
    }
}
