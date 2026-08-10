"""Portfolio profile CSV API for holding names and colors."""

from __future__ import annotations

import csv
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

PROFILE_FILE = Path(__file__).resolve().parents[1] / "trade" / "portfolio.csv"
PROFILE_FIELDS = ("代码", "名称", "颜色")
PROFILE_KEYS = ("code", "name", "color")

import threading

_write_lock = threading.Lock()
router = APIRouter(prefix="/api/profile", tags=["profile"])


class HoldingProfile(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str = ""
    color: str = "#d03050"


def _read_profiles() -> list[dict]:
    if not PROFILE_FILE.is_file():
        return []
    with PROFILE_FILE.open("r", encoding="utf-8", newline="") as stream:
        return [
            dict(zip(PROFILE_KEYS, (row.get(field, "") for field in PROFILE_FIELDS)))
            for row in csv.DictReader(stream)
        ]


def _write_profiles(profiles: list[dict]) -> None:
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PROFILE_FILE.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PROFILE_FIELDS)
        writer.writeheader()
        writer.writerows(
            {field: p.get(key, "") for field, key in zip(PROFILE_FIELDS, PROFILE_KEYS)}
            for p in profiles
        )


@router.get("")
def list_profiles() -> list[dict]:
    return _read_profiles()


@router.post("")
def save_profile(profile: HoldingProfile) -> dict:
    saved = {
        "code": profile.code,
        "name": profile.name.strip(),
        "color": profile.color,
    }
    with _write_lock:
        profiles = [item for item in _read_profiles() if item.get("code") != profile.code]
        profiles.append(saved)
        _write_profiles(profiles)
    return saved


@router.delete("/{code}")
def delete_profile(code: str) -> dict:
    profiles = _read_profiles()
    remaining = [item for item in profiles if item.get("code") != code]
    if len(remaining) == len(profiles):
        raise HTTPException(status_code=404, detail="profile not found")
    _write_profiles(remaining)
    return {"code": code}
