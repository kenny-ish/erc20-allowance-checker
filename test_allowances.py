import unittest

from allowances import UINT160_MAX, UNLIMITED, decode_permit2, fmt, live_permit2, word


def w(n):
    return format(n, "064x")


class AllowanceTest(unittest.TestCase):
    def test_word(self):
        self.assertEqual(word("0xABCDEF"), "0" * 58 + "abcdef")

    def test_decode_permit2(self):
        self.assertEqual(decode_permit2("0x" + w(500) + w(1_800_000_000) + w(3)), (500, 1_800_000_000, 3))

    def test_fmt(self):
        self.assertEqual(fmt(2**256 - 1, 6), "UNLIMITED")
        self.assertEqual(fmt(UINT160_MAX, 6, UINT160_MAX), "UNLIMITED")
        self.assertEqual(fmt(1_250_000, 6), "1.2500")
        self.assertLess(UNLIMITED, 2**256)

    def test_permit2_liveness(self):
        self.assertTrue(live_permit2(1, 200, 100))
        self.assertFalse(live_permit2(1, 50, 100))  # expired
        self.assertFalse(live_permit2(0, 200, 100))  # zero amount


if __name__ == "__main__":
    unittest.main()
