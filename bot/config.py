"""Load the static watchlist (locations + assets) from YAML."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
DEFAULT_PATH = CONFIG_DIR / "watchlist.yaml"
# Edits made from Telegram are saved here (git-ignored), so they survive restarts
# and are not overwritten when you download a new version of the code.
LOCAL_PATH = CONFIG_DIR / "watchlist.local.yaml"


@dataclass(frozen=True)
class Location:
    code: str
    name: str
    tz: ZoneInfo
    open: time
    close: time
    weekdays: tuple[int, ...]


@dataclass(frozen=True)
class Asset:
    symbol: str
    name: str
    asset_class: str
    location: str
    ibkr: dict = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class Settings:
    report_offset_minutes: int = 15
    headlines_per_asset: int = 10
    top_n: int = 10


@dataclass(frozen=True)
class Watchlist:
    locations: dict[str, Location]
    assets: list[Asset]
    settings: Settings

    def asset_classes(self) -> list[str]:
        return sorted({a.asset_class for a in self.assets})


def _parse_time(s: str) -> time:
    h, m = str(s).split(":")
    return time(int(h), int(m))


def active_path() -> Path:
    return LOCAL_PATH if LOCAL_PATH.exists() else DEFAULT_PATH


def read_raw(path: str | Path | None = None) -> dict:
    return yaml.safe_load(Path(path or active_path()).read_text())


def load_watchlist(path: str | Path | None = None) -> Watchlist:
    return parse_watchlist(read_raw(path))


def parse_watchlist(raw: dict) -> Watchlist:
    locations = {
        code: Location(
            code=code,
            name=v.get("name", code),
            tz=ZoneInfo(v["timezone"]),
            open=_parse_time(v["open"]),
            close=_parse_time(v["close"]),
            weekdays=tuple(v.get("weekdays", [0, 1, 2, 3, 4])),
        )
        for code, v in raw["locations"].items()
    }
    assets = []
    for a in raw.get("assets") or []:
        if a["location"] not in locations:
            raise ValueError(f"Asset {a['symbol']} uses unknown location {a['location']!r}")
        assets.append(Asset(str(a["symbol"]), a.get("name", a["symbol"]),
                            a["asset_class"], a["location"], a.get("ibkr", {})))
    settings = Settings(**(raw.get("settings") or {}))
    return Watchlist(locations, assets, settings)
