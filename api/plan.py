"""Recurring investment plan API (reads/writes portfolio.json)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import json
import threading

CONFIG_FILE = Path(__file__).resolve().parents[1] / "trade" / "portfolio.json"
_write_lock = threading.Lock()
FREQUENCIES = {"每周", "每月"}

router = APIRouter(prefix="/api/plan", tags=["plan"])


class InvestmentPlan(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    amount: float = Field(gt=0)
    holdings: int = Field(default=0, ge=0)
    frequency: str
    next_date: date
    enabled: bool = True


def _read_config() -> dict:
    if not CONFIG_FILE.is_file():
        return {"holdings": {}, "plans": []}
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_config(config: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@router.get("")
def list_plans() -> list[dict]:
    config = _read_config()
    plans = config.get("plans", [])
    return [
        {
            "code": p["code"],
            "name": p.get("name", ""),
            "amount": f"{p['amount']:.2f}",
            "holdings": str(p.get("holdings", 0)),
            "frequency": p.get("frequency", ""),
            "next_date": p.get("next_date", ""),
            "enabled": "1" if p.get("enabled", True) else "0",
        }
        for p in plans
    ]


@router.post("")
def save_plan(plan: InvestmentPlan) -> dict:
    if plan.frequency not in FREQUENCIES:
        raise HTTPException(status_code=422, detail="frequency must be 每周 or 每月")
    with _write_lock:
        config = _read_config()
        plans = config.setdefault("plans", [])
        plans = [p for p in plans if p.get("code") != plan.code]
        plans.append(
            {
                "code": plan.code,
                "name": plan.name.strip(),
                "amount": plan.amount,
                "holdings": plan.holdings,
                "frequency": plan.frequency,
                "next_date": plan.next_date.isoformat(),
                "enabled": plan.enabled,
            }
        )
        config["plans"] = plans
        _write_config(config)
    return {
        "code": plan.code,
        "name": plan.name.strip(),
        "amount": f"{plan.amount:.2f}",
        "holdings": str(plan.holdings),
        "frequency": plan.frequency,
        "next_date": plan.next_date.isoformat(),
        "enabled": "1" if plan.enabled else "0",
    }


@router.delete("/{code}")
def delete_plan(code: str) -> dict:
    with _write_lock:
        config = _read_config()
        plans = config.get("plans", [])
        remaining = [p for p in plans if p.get("code") != code]
        if len(remaining) == len(plans):
            raise HTTPException(status_code=404, detail="investment plan not found")
        config["plans"] = remaining
        _write_config(config)
    return {"code": code}
