"""Portfolio profile JSON API: holding names, colors and total cost."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

CONFIG_FILE = Path(__file__).resolve().parents[1] / "trade" / "portfolio.json"
_write_lock = threading.Lock()


class HoldingProfile(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str = ""
    color: str = "#d03050"
    rise_pct: float = Field(default=5, ge=0, le=100)
    fall_pct: float = Field(default=5, ge=0, le=100)


class GoldPerShare(BaseModel):
    value: float = Field(gt=0, lt=1)


class PropertyProfile(BaseModel):
    asset: str = Field(min_length=1, max_length=64)
    color: str = "#d03050"


def _read_config() -> dict:
    if not CONFIG_FILE.is_file():
        return {"holdings": {}, "plans": []}
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_config(config: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
def list_profiles() -> list[dict]:
    config = _read_config()
    holdings = config.get("holdings", {})
    return [
        {"code": k, "name": v.get("name", ""), "color": v.get("color", "#d03050"), "rise_pct": v.get("rise_pct", 5), "fall_pct": v.get("fall_pct", 5)}
        for k, v in holdings.items()
    ]


@router.post("")
def save_profile(profile: HoldingProfile) -> dict:
    with _write_lock:
        config = _read_config()
        config.setdefault("holdings", {})[profile.code] = {
            "name": profile.name.strip(),
            "color": profile.color,
            "rise_pct": profile.rise_pct,
            "fall_pct": profile.fall_pct,
        }
        _write_config(config)
    return {"code": profile.code, "name": profile.name.strip(), "color": profile.color}


@router.get("/total_cost")
def get_total_cost() -> dict:
    config = _read_config()
    return {"total_cost": config.get("total_cost", 0)}


@router.post("/total_cost")
def set_total_cost(body: dict) -> dict:
    with _write_lock:
        config = _read_config()
        config["total_cost"] = float(body.get("total_cost", 0))
        _write_config(config)
    return {"total_cost": config["total_cost"]}


@router.get("/gold_per_share")
def get_gold_per_share() -> dict:
    config = _read_config()
    return {"value": config.get("gold_per_share", 0.00951)}


@router.post("/gold_per_share")
def set_gold_per_share(body: GoldPerShare) -> dict:
    with _write_lock:
        config = _read_config()
        config["gold_per_share"] = body.value
        _write_config(config)
    return {"value": body.value}


@router.delete("/{code}")
def delete_profile(code: str) -> dict:
    with _write_lock:
        config = _read_config()
        holdings = config.get("holdings", {})
        if code not in holdings:
            raise HTTPException(status_code=404, detail="profile not found")
        del holdings[code]
        _write_config(config)
    return {"code": code}


@router.get("/property")
def list_property_profiles() -> list[dict]:
    config = _read_config()
    return [
        {"asset": key, "color": value.get("color", "#d03050")}
        for key, value in config.get("properties", {}).items()
    ]


@router.post("/property")
def save_property_profile(profile: PropertyProfile) -> dict:
    with _write_lock:
        config = _read_config()
        config.setdefault("properties", {})[profile.asset] = {"color": profile.color}
        _write_config(config)
    return {"asset": profile.asset, "color": profile.color}
