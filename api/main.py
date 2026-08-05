"""HTTP API for Galaxy portfolio data."""

from __future__ import annotations

from typing import Annotated

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from api.amarket import compute_daily_market_value, get_quotes
from api.galaxy import REPO_CODES, compute_holdings, load_trades
from api.plan import router as plan_router

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


@app.get("/api/daily_market_value")
def daily_market_value() -> dict[str, dict[str, float]]:
    return compute_daily_market_value(load_trades(), REPO_CODES)
