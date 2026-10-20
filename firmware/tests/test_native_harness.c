// Harness smoke test (milestone 1): proves the native Unity build runs and
// checks the platform assumptions the portable wire codecs will rely on
// (docs/DESIGN.md §6.1). Codecs serialize fields explicitly, so host
// endianness is deliberately not asserted.
#include <float.h>
#include <limits.h>
#include <stdint.h>

#include "unity.h"

void setUp(void) {
}

void tearDown(void) {
}

static void test_compiled_as_c11(void) {
    TEST_ASSERT_TRUE(__STDC_VERSION__ >= 201112L);
}

static void test_bytes_are_octets(void) {
    TEST_ASSERT_EQUAL_INT(8, CHAR_BIT);
}

static void test_float_is_ieee754_binary32(void) {
    TEST_ASSERT_EQUAL_size_t(4, sizeof(float));
    TEST_ASSERT_EQUAL_INT(2, FLT_RADIX);
    TEST_ASSERT_EQUAL_INT(24, FLT_MANT_DIG);
    TEST_ASSERT_EQUAL_INT(128, FLT_MAX_EXP);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_compiled_as_c11);
    RUN_TEST(test_bytes_are_octets);
    RUN_TEST(test_float_is_ieee754_binary32);
    return UNITY_END();
}
