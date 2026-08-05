from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from api.amarket import _parse_quote_line, compute_daily_market_value


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


class DailyMarketValueTests(unittest.TestCase):
    @patch("api.amarket.get_daily_closes")
    def test_accumulates_positions_and_excludes_repos(self, closes) -> None:
        closes.return_value = {"20260801": 4.5, "20260802": 4.6}
        trades = pd.DataFrame(
            [
                {"datetime": "20260801 09:30:00", "code": "510300", "side": "买入", "quantity": 100},
                {"datetime": "20260802 09:30:00", "code": "510300", "side": "卖出", "quantity": 40},
                {"datetime": "20260801 15:00:00", "code": "204001", "side": "买入", "quantity": 1000},
            ]
        )

        result = compute_daily_market_value(trades, {"204001"})

        self.assertEqual(
            result,
            {
                "20260801": {"510300": 450.0},
                "20260802": {"510300": 276.0},
            },
        )
        closes.assert_called_once_with("510300")


if __name__ == "__main__":
    unittest.main()
