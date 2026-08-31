"""A-share market data clients."""

from __future__ import annotations

import csv
import datetime as dt
import os
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import requests


def normalize_date(value: str) -> str:
    value = value.split(" ", 1)[0].replace("-", "")
    if len(value) != 8:
        return value
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


SINA_FIELDS = (
    "name",
    "open",
    "previous_close",
    "price",
    "high",
    "low",
    "bid",
    "ask",
    "volume",
    "amount",
    "bid_1_volume",
    "bid_1_price",
    "bid_2_volume",
    "bid_2_price",
    "bid_3_volume",
    "bid_3_price",
    "bid_4_volume",
    "bid_4_price",
    "bid_5_volume",
    "bid_5_price",
    "ask_1_volume",
    "ask_1_price",
    "ask_2_volume",
    "ask_2_price",
    "ask_3_volume",
    "ask_3_price",
    "ask_4_volume",
    "ask_4_price",
    "ask_5_volume",
    "ask_5_price",
    "date",
    "time",
    "status",
    "extra",
)
VOLUME_FIELDS = {
    "volume",
    *(f"{side}_{level}_volume" for side in ("bid", "ask") for level in range(1, 6)),
}
PRICE_FIELDS = {
    "open",
    "previous_close",
    "price",
    "high",
    "low",
    "bid",
    "ask",
    "amount",
    *(f"{side}_{level}_price" for side in ("bid", "ask") for level in range(1, 6)),
}


REQUIRED_SINA_FIELDS = len(SINA_FIELDS) - 1


def _parse_quote_line(line: str) -> dict | None:
    variable, separator, raw = line.partition("=")
    if not separator:
        return None

    values = raw.strip().removesuffix(";").strip('"').split(",")
    if len(values) < REQUIRED_SINA_FIELDS or not values[0]:
        return None

    symbol = variable.removeprefix("var hq_str_")
    quote: dict[str, object] = {"code": symbol[2:], "symbol": symbol}
    for field, value in zip(SINA_FIELDS, values, strict=False):
        if field in VOLUME_FIELDS:
            quote[field] = int(value) if value else 0
        elif field in PRICE_FIELDS:
            quote[field] = float(value) if value else 0.0
        else:
            quote[field] = value
    return quote


def get_quotes(codes: list[str]) -> list[dict]:
    """Fetch and parse Sina real-time quotes for A-share security codes."""
    symbols = [f"{'sh' if code[0] in '569' else 'sz'}{code}" for code in codes]
    response = requests.get(
        f"https://hq.sinajs.cn/list={','.join(symbols)}",
        headers={"Referer": "https://finance.sina.com.cn"},
        timeout=10,
    )
    response.raise_for_status()

    return [
        quote
        for line in response.content.decode("gbk").splitlines()
        if (quote := _parse_quote_line(line))
    ]


CLOSE_CACHE_CSV_FILE = Path(__file__).resolve().parents[1] / "trade" / "daily_close_prices.csv"
_cache_lock = threading.Lock()


def _read_close_cache() -> dict[str, dict[str, float]]:
    if CLOSE_CACHE_CSV_FILE.is_file():
        with CLOSE_CACHE_CSV_FILE.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            codes = [code for code in (reader.fieldnames or [])[1:] if code]
        return {
            code: {row["date"]: float(row[code]) for row in rows if row.get(code)}
            for code in codes
        }
    return {}


def _write_close_cache(cache: dict[str, dict[str, float]]) -> None:
    CLOSE_CACHE_CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    codes = sorted(cache)
    dates = sorted({date for values in cache.values() for date in values})
    temp = CLOSE_CACHE_CSV_FILE.with_suffix(".csv.tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", *codes])
        writer.writeheader()
        for date in dates:
            writer.writerow({"date": date, **{code: cache[code].get(date, "") for code in codes}})
    os.replace(temp, CLOSE_CACHE_CSV_FILE)


def _get_daily_closes_tencent(code: str) -> dict[str, float]:
    """Fetch daily closes from Tencent."""
    market = "sh" if code[0] in "569" else "sz"
    symbol = f"{market}{code}"
    response = requests.get(
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        params={"param": f"{symbol},day,,,320,qfq"},
        headers={"Referer": "https://gu.qq.com", "User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    response.raise_for_status()
    data = (response.json().get("data") or {}).get(symbol) or {}
    rows = data.get("qfqday") or data.get("day") or []
    return {normalize_date(row[0]): float(row[2]) for row in rows if len(row) >= 3}


def _get_daily_closes_eastmoney(code: str) -> dict[str, float]:
    """Fallback daily closes from Eastmoney."""
    market = "1" if code[0] in "569" else "0"
    response = requests.get(
        "http://push2his.eastmoney.com/api/qt/stock/kline/get",
        params={
            "secid": f"{market}.{code}",
            "fields1": "f1,f2,f3",
            "fields2": "f51,f52,f53,f54,f55,f56",
            "klt": "101", "fqt": "1", "beg": "19900101", "end": "20991231",
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    response.raise_for_status()
    rows = ((response.json().get("data") or {}).get("klines") or [])
    return {normalize_date(fields[0]): float(fields[2]) for row in rows if len(fields := row.split(",")) >= 3}


def get_daily_closes(code: str) -> dict[str, float]:
    """Fetch daily closes, keeping Tencent as primary and Eastmoney as fallback."""
    errors = []
    for fetcher in (_get_daily_closes_tencent, _get_daily_closes_eastmoney):
        for attempt in range(2):
            try:
                result = fetcher(code)
                if result:
                    return result
            except requests.RequestException as error:
                errors.append(error)
                if attempt == 0:
                    time.sleep(0.5)
    raise errors[-1] if errors else requests.RequestException(f"failed to fetch closes for {code}")


def _cache_updated_today() -> bool:
    return (
        CLOSE_CACHE_CSV_FILE.is_file()
        and dt.datetime.fromtimestamp(CLOSE_CACHE_CSV_FILE.stat().st_mtime).date() == dt.date.today()
    )


def _ensure_close_cache(codes: list[str]) -> dict[str, dict[str, float]]:
    """Load CSV and refresh it at most once per calendar day."""
    with _cache_lock:
        cache = _read_close_cache()
        if _cache_updated_today() and all(code in cache and cache[code] for code in codes):
            return cache
        changed = False
        for code in codes:
            try:
                fetched = get_daily_closes(code)
            except requests.RequestException:
                continue
            if fetched:
                cache[code] = {**cache.get(code, {}), **fetched}
                changed = True
        if changed or not CLOSE_CACHE_CSV_FILE.is_file():
            _write_close_cache(cache)
        return cache


def compute_daily_close_prices(codes: list[str]) -> dict[str, dict[str, float]]:
    """Return persisted closes, refreshing the CSV at most once per day."""
    cache = _ensure_close_cache(codes)
    return {
        date: {code: cache[code][date] for code in codes if date in cache.get(code, {})}
        for date in sorted({date for code in codes for date in cache.get(code, {})})
    }


def compute_daily_market_value(trades, repo_codes: set[str]) -> dict[str, dict[str, float]]:
    """Compute close value by date and code from normalized trades."""
    if trades.empty:
        return {}

    securities = trades[~trades["code"].isin(repo_codes)].copy()
    securities["date"] = securities["datetime"].map(normalize_date)
    trade_dates = set(securities["date"])
    close_by_date = compute_daily_close_prices(securities["code"].unique().tolist())
    first_trade_date = min(trade_dates)
    all_close_dates = set(close_by_date)
    dates = sorted((trade_dates | all_close_dates) - {
        date for date in all_close_dates if date < first_trade_date
    })
    result = {date: {} for date in dates}

    for code, code_trades in securities.groupby("code"):
        shares = 0
        daily_shares = {}
        for trade in code_trades.sort_values("datetime").itertuples(index=False):
            shares += trade.quantity if trade.side == "买入" else -trade.quantity
            daily_shares[trade.date] = shares

        shares = 0
        for date in dates:
            shares = daily_shares.get(date, shares)
            result[date][code] = round(shares * close_by_date.get(date, {}).get(code, 0), 2)

    return result
