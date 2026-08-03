#!/usr/bin/env python3
"""Load broker trade exports into a normalized pandas DataFrame."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DEFAULT_TRADE_DIR = Path(__file__).resolve().parents[1] / "trade"

REPO_CODES = {"131810", "204001"}

COL_MAP = {
    "成交时间": "datetime",
    "证券代码": "code",
    "证券名称": "name",
    "操作": "side",
    "成交数量": "quantity",
    "成交均价": "price",
    "成交金额": "amount",
    "合同编号": "contract",
    "成交编号": "deal",
    "手续费": "fee",
    "印花税": "stamp",
    "其他杂费": "other",
    "发生金额": "net",
    "资金余额": "balance",
    "交易市场": "market",
    "证券中文全称": "fullname",
}

INT_COLUMNS = ("quantity", "deal")

FLOAT_COLUMNS = (
    "price",
    "amount",
    "fee",
    "stamp",
    "other",
    "net",
    "balance",
)


def parse_trade_file(path: str | Path) -> pd.DataFrame:
    """Parse one GB18030 broker export, preserving raw Chinese columns."""
    lines = Path(path).expanduser().read_text(encoding="gb18030").splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if "成交日期" in line and "证券代码" in line
        ),
        None,
    )
    if header_index is None:
        return pd.DataFrame()

    columns = [
        column.strip() for column in lines[header_index].split("\t") if column.strip()
    ]
    rows = []
    for line in lines[header_index + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("-") or stripped.startswith("保存时间"):
            continue

        fields = [field.strip() for field in line.split("\t")]
        fields.extend([""] * (len(columns) - len(fields)))
        rows.append(fields[: len(columns)])

    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df

    df["成交时间"] = pd.to_datetime(df["成交日期"] + " " + df["成交时间"])
    return df.drop(columns="成交日期")


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=COL_MAP).copy()

    for column in INT_COLUMNS:
        if column in df:
            df[column] = (
                pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)
            )

    for column in FLOAT_COLUMNS:
        if column in df:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        else:
            df[column] = pd.NA

    columns = [column for column in COL_MAP.values() if column in df]
    return df[columns]


def load_trades(trade_dir: str | Path = DEFAULT_TRADE_DIR) -> pd.DataFrame:
    """Load history and daily files, normalize, deduplicate, and sort trades."""
    directory = Path(trade_dir).expanduser()
    paths = []

    history = directory / "history.txt"
    if history.is_file():
        paths.append(history)
    paths.extend(
        path for path in sorted(directory.glob("????????.txt")) if path.stem.isdigit()
    )

    frames = []
    for path in paths:
        df = parse_trade_file(path)
        if not df.empty:
            frames.append(_normalize(df))

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    fee_mask = df["fee"].isna() & (df["amount"] > 0) & ~df["code"].isin(REPO_CODES)
    df.loc[fee_mask, "fee"] = (
        (df.loc[fee_mask, "amount"] * 0.00005).clip(lower=0.1).round(3)
    )
    df["fee"] = df["fee"].fillna(0.0)

    repo_mask = df["code"].isin(REPO_CODES)
    df.loc[repo_mask & (df["net"] < 0), "side"] = "买入"
    df.loc[repo_mask & (df["net"] >= 0), "side"] = "卖出"
    df.loc[repo_mask & df["net"].isna() & (df["amount"] > 0), "side"] = "买入"

    return (
        df.drop_duplicates(
            subset=["datetime", "code", "quantity", "price", "deal"],
            keep="first",
        )
        .sort_values("datetime", ascending=False)
        .reset_index(drop=True)
    )


def compute_holdings(df: pd.DataFrame) -> list[dict]:
    """Compute stocks holdings using net cost and moving-average realized P&L."""
    stocks = df[~df["code"].isin(REPO_CODES)].copy()
    if stocks.empty:
        return []

    holdings = []
    for code, trades in stocks.groupby("code", sort=True):
        buys = trades[trades["side"] == "买入"]
        sells = trades[trades["side"] == "卖出"]

        # 使用 .iloc[0] 的方式获取标量值，避免 Series 运算
        buy_quantity = int(buys["quantity"].sum())
        sell_quantity = int(sells["quantity"].sum())
        buy_amount = float(buys["amount"].sum())
        buy_fee = float(buys["fee"].sum())
        sell_amount = float(sells["amount"].sum())
        sell_fee = float(sells["fee"].sum())

        shares = buy_quantity - sell_quantity
        total_cost = buy_amount + buy_fee - sell_amount + sell_fee

        moving_shares = 0
        moving_cost = 0.0
        realized = 0.0

        # 关键修改：确保每行的值转换为 Python 原生类型
        for trade in trades.sort_values("datetime").itertuples(index=False):
            quantity = int(trade.quantity)  # 显式转换为 int
            amount = float(trade.amount)  # 显式转换为 float
            fee = float(trade.fee)  # 显式转换为 float

            if trade.side == "买入":
                moving_cost += fee + amount
                moving_shares += quantity
                continue

            average_cost = moving_cost / moving_shares if moving_shares else 0
            realized += amount - average_cost * quantity - fee
            moving_shares -= quantity
            moving_cost = average_cost * moving_shares
            if moving_shares == 0:
                moving_cost = 0.0

        holdings.append(
            {
                "code": code,
                "name": trades.iloc[0]["name"],
                "fullname": trades.iloc[0].get("fullname", ""),
                "shares": int(shares),
                "avg_cost": round(total_cost / shares, 4) if shares > 0 else 0,
                "total_cost": round(total_cost, 2),
                "realized": round(realized, 2),
                "buy_count": len(buys),
                "sell_count": len(sells),
            }
        )

    return holdings
