"""HTTP API for Galaxy portfolio data."""

from __future__ import annotations

import json
from typing import Annotated
import urllib.request

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from api.amarket import get_quotes
from api.galaxy import REPO_CODES, compute_holdings, load_trades

app = FastAPI(title="Galaxy Portfolio API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _records(df: pd.DataFrame) -> list[dict]:
    records = []
    for record in df.to_dict(orient="records"):
        records.append(
            {
                key: None if value is pd.NA or pd.isna(value) else value
                for key, value in record.items()
            }
        )
    return records


@app.get("/api/trades")
def trades() -> list[dict]:
    return _records(load_trades())


@app.get("/api/holdings")
def holdings() -> list[dict]:
    trades_df = load_trades()
    return compute_holdings(trades_df) if not trades_df.empty else []


@app.get("/api/quotes")
def quotes(
    codes: Annotated[str, Query(min_length=1, description="Comma-separated codes")],
) -> list[dict]:
    parsed = [code.strip() for code in codes.split(",") if code.strip()]
    return get_quotes(parsed)


def _daily_closes(code: str) -> dict[str, float]:
    market = "sh" if code[0] in "569" else "sz"
    url = (
        "https://quotes.sina.cn/cn/api/json_v2.php/"
        "CN_MarketDataService.getKLineData"
        f"?symbol={market}{code}&scale=240&datalen=200"
    )
    request = urllib.request.Request(
        url,
        headers={"Referer": "https://finance.sina.com.cn"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            klines = json.loads(response.read().decode("utf-8"))
    except Exception:
        return {}
    return {
        item["day"][:10].replace("-", ""): float(item["close"])
        for item in klines or []
    }


@app.get("/api/daily_market_value")
def daily_market_value() -> dict[str, dict[str, float]]:
    """Return daily close value for each non-repo position."""
    trades_df = load_trades()
    if trades_df.empty:
        return {}

    etfs = trades_df[~trades_df["code"].isin(REPO_CODES)].copy()
    etfs["date"] = etfs["datetime"].str.split(" ").str[0]
    dates = sorted(set(etfs["date"]))
    result = {date: {} for date in dates}

    for code, trades in etfs.groupby("code"):
        daily_shares = {}
        shares = 0
        for trade in trades.sort_values("datetime").itertuples(index=False):
            shares += trade.quantity if trade.side == "买入" else -trade.quantity
            daily_shares[trade.date] = shares

        closes = _daily_closes(code)
        shares = 0
        for date in dates:
            shares = daily_shares.get(date, shares)
            result[date][code] = round(shares * closes.get(date, 0), 2)

    return result
