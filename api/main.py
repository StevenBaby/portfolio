"""HTTP API for Galaxy portfolio data."""

from __future__ import annotations

from typing import Annotated

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from api.amarket import (
    compute_daily_close_prices,
    compute_daily_market_value,
    get_quotes,
)
from api.galaxy import REPO_CODES, compute_holdings, load_trades
from api.plan import router as plan_router
from api.probe import (
    get_all_probes,
    get_cn_indices,
    get_margin_trading,
    get_hk_connect,
    get_us_market,
    get_asia_market,
    get_macro,
    get_commodities,
)

app = FastAPI(title="Galaxy Portfolio API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(plan_router)


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


@app.get("/api/daily_close_prices")
def daily_close_prices() -> dict[str, dict[str, float]]:
    codes = [
        trade["code"]
        for trade in _records(load_trades())
        if trade["code"] not in REPO_CODES
    ]
    return compute_daily_close_prices(sorted(set(codes)))


@app.get("/api/daily_market_value")
def daily_market_value() -> dict[str, dict[str, float]]:
    return compute_daily_market_value(load_trades(), REPO_CODES)


# ---- Probe 探针接口 ----


@app.get("/api/probe/all")
def probe_all() -> dict:
    """全量探针: 美股+亚太+宏观+商品"""
    return get_all_probes()


@app.get("/api/probe/us")
def probe_us() -> dict:
    """美股市场: 指数+SOXL+科技七巨头"""
    return get_us_market()


@app.get("/api/probe/cn")
def probe_cn() -> dict:
    """A股指数: 上证/深证/创业板/沪深300/中证500/科创50"""
    return get_cn_indices()


@app.get("/api/probe/margin")
def probe_margin() -> dict:
    """融资融券: 两市融资余额/融券余额"""
    return get_margin_trading()


@app.get("/api/probe/hk_connect")
def probe_hk_connect() -> dict:
    """港股通: 南向/北向成交额和净买入"""
    return get_hk_connect()


@app.get("/api/probe/asia")
def probe_asia() -> dict:
    """亚太市场: 日经/KOSPI/恒生/A50"""
    return get_asia_market()


@app.get("/api/probe/macro")
def probe_macro() -> dict:
    """宏观指标: DXY/USDCNH"""
    return get_macro()


@app.get("/api/probe/commodities")
def probe_commodities() -> dict:
    """商品: COMEX黄金/WTI/伦敦金"""
    return get_commodities()
