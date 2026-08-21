"""Asset snapshot CSV API."""

from __future__ import annotations

import csv
import os
import re
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

PROPERTY_FILE = Path(__file__).resolve().parent.parent / "trade" / "property.csv"
_property_write_lock = threading.Lock()
router = APIRouter(tags=["properties"])


def _property_number(value: str) -> float:
    text = (value or "").replace(",", "").strip()
    if not text:
        return 0.0
    return sum(float(part) for part in re.findall(r"[-+]?\d+(?:\.\d+)?", text))


def _property_date(value: str) -> str:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value.strip()


def _read_properties() -> dict:
    if not PROPERTY_FILE.exists():
        return {"assets": [], "rows": []}
    with PROPERTY_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        assets = [name.strip() for name in (reader.fieldnames or [])[1:] if name]
        rows = []
        for raw in reader:
            values = {asset: round(_property_number(raw.get(asset, "")), 2) for asset in assets}
            rows.append({
                "date": _property_date(raw.get("日期", "")),
                "values": values,
                "total": round(sum(values.values()), 2),
            })
    rows.sort(key=lambda row: row["date"], reverse=True)
    return {"assets": assets, "rows": rows}


@router.get("/api/properties")
def properties() -> dict:
    return _read_properties()


@router.put("/api/properties")
def save_properties(payload: dict) -> dict:
    assets = [
        str(asset).strip()
        for asset in payload.get("assets", [])
        if str(asset).strip() and str(asset).strip() != "日期"
    ]
    if not assets:
        raise ValueError("assets cannot be empty")

    rows = []
    for raw in payload.get("rows", []):
        date = _property_date(str(raw.get("date", "")))
        if not date:
            raise ValueError("date cannot be empty")
        values = {
            asset: round(_property_number(str(raw.get("values", {}).get(asset, 0) or 0)), 2)
            for asset in assets
        }
        rows.append({
            "date": date,
            "values": values,
            "total": round(sum(values.values()), 2),
        })
    rows.sort(key=lambda row: row["date"], reverse=True)

    with _property_write_lock:
        PROPERTY_FILE.parent.mkdir(parents=True, exist_ok=True)
        original_stat = PROPERTY_FILE.stat() if PROPERTY_FILE.exists() else None
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8-sig", newline="", dir=PROPERTY_FILE.parent, delete=False
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=["日期", *assets])
            writer.writeheader()
            for row in sorted(rows, key=lambda item: item["date"]):
                writer.writerow({"日期": row["date"], **row["values"]})
            temp_name = handle.name
        if original_stat:
            os.chown(temp_name, original_stat.st_uid, original_stat.st_gid)
            os.chmod(temp_name, original_stat.st_mode & 0o7777)
        os.replace(temp_name, PROPERTY_FILE)
    return {"assets": assets, "rows": rows}
