"""A-share market data clients."""

from __future__ import annotations

import requests

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


def get_daily_closes(code: str) -> dict[str, float]:
    """Fetch up to 200 daily closing prices from Sina."""
    market = "sh" if code[0] in "569" else "sz"
    response = requests.get(
        "https://quotes.sina.cn/cn/api/json_v2.php/"
        "CN_MarketDataService.getKLineData",
        params={"symbol": f"{market}{code}", "scale": 240, "datalen": 200},
        headers={"Referer": "https://finance.sina.com.cn"},
        timeout=15,
    )
    response.raise_for_status()
    return {
        item["day"][:10].replace("-", ""): float(item["close"])
        for item in response.json() or []
    }


def compute_daily_market_value(trades, repo_codes: set[str]) -> dict[str, dict[str, float]]:
    """Compute close value by date and code from normalized trades."""
    if trades.empty:
        return {}

    securities = trades[~trades["code"].isin(repo_codes)].copy()
    securities["date"] = securities["datetime"].str.split(" ").str[0]
    trade_dates = set(securities["date"])
    close_by_code = {}
    for code in securities["code"].unique():
        try:
            close_by_code[code] = get_daily_closes(code)
        except requests.RequestException:
            close_by_code[code] = {}
    first_trade_date = min(trade_dates)
    all_close_dates = {
        date for closes in close_by_code.values() for date in closes
    }
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

        closes = close_by_code.get(code, {})
        shares = 0
        for date in dates:
            shares = daily_shares.get(date, shares)
            result[date][code] = round(shares * closes.get(date, 0), 2)

    return result
