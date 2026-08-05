"""Recurring investment plan CSV API."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

PLAN_FILE = Path(__file__).resolve().parents[1] / "trade" / "plan.csv"
PLAN_FIELDS = ("代码", "名称", "金额", "周期", "下次定投", "启用")
PLAN_KEYS = ("code", "name", "amount", "frequency", "next_date", "enabled")
FREQUENCIES = {"每周", "每月"}

router = APIRouter(prefix="/api/plan", tags=["plan"])


class InvestmentPlan(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    amount: float = Field(gt=0)
    frequency: str
    next_date: date
    enabled: bool = True


def _read_plans() -> list[dict]:
    if not PLAN_FILE.is_file():
        return []
    with PLAN_FILE.open("r", encoding="utf-8", newline="") as stream:
        return [
            dict(zip(PLAN_KEYS, (row.get(field, "") for field in PLAN_FIELDS)))
            for row in csv.DictReader(stream)
        ]


def _write_plans(plans: list[dict]) -> None:
    PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PLAN_FILE.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PLAN_FIELDS)
        writer.writeheader()
        writer.writerows(
            {field: plan.get(key, "") for field, key in zip(PLAN_FIELDS, PLAN_KEYS)}
            for plan in plans
        )


@router.get("")
def list_plans() -> list[dict]:
    return _read_plans()


@router.post("")
def save_plan(plan: InvestmentPlan) -> dict:
    if plan.frequency not in FREQUENCIES:
        raise HTTPException(status_code=422, detail="frequency must be 每周 or 每月")

    saved = {
        "code": plan.code,
        "name": plan.name.strip(),
        "amount": f"{plan.amount:.2f}",
        "frequency": plan.frequency,
        "next_date": plan.next_date.isoformat(),
        "enabled": "1" if plan.enabled else "0",
    }
    plans = [item for item in _read_plans() if item.get("code") != plan.code]
    plans.append(saved)
    _write_plans(plans)
    return saved


@router.delete("/{code}")
def delete_plan(code: str) -> dict:
    plans = _read_plans()
    remaining = [item for item in plans if item.get("code") != code]
    if len(remaining) == len(plans):
        raise HTTPException(status_code=404, detail="investment plan not found")
    _write_plans(remaining)
    return {"code": code}
