import unittest

from marketlens_mcp.server import normalize_symbol, percent_change


class TestMarketLensHelpers(unittest.TestCase):
    def test_bare_symbol_defaults_to_nse(self):
        self.assertEqual(normalize_symbol("reliance"), "RELIANCE.NS")

    def test_explicit_bse_symbol_is_kept(self):
        self.assertEqual(normalize_symbol("tcs.bo"), "TCS.BO")

    def test_index_symbol_is_kept(self):
        self.assertEqual(normalize_symbol("^nsei"), "^NSEI")

    def test_empty_symbol_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_symbol("   ")

    def test_percentage_change(self):
        self.assertAlmostEqual(percent_change(100, 110), 10.0)
        self.assertAlmostEqual(percent_change(100, 90), -10.0)


if __name__ == "__main__":
    unittest.main()
