from __future__ import annotations

import unittest

from api.amarket import _parse_quote_line


class ParseQuoteLineTests(unittest.TestCase):
    def test_accepts_standard_record_without_optional_extra_field(self) -> None:
        line = (
            'var hq_str_sz159142="双创AI,1.173,1.158,1.223,1.225,1.173,'
            '1.221,1.225,65013101,78101659.718,600,1.221,300,1.220,'
            '41000,1.219,29600,1.218,129900,1.216,23300,1.225,77700,'
            '1.226,67000,1.227,124500,1.228,28800,1.229,'
            '2026-08-04,11:30:00,00";'
        )

        quote = _parse_quote_line(line)

        self.assertIsNotNone(quote)
        assert quote is not None
        self.assertEqual(quote["code"], "159142")
        self.assertEqual(quote["price"], 1.223)
        self.assertEqual(quote["status"], "00")
        self.assertNotIn("extra", quote)


if __name__ == "__main__":
    unittest.main()
