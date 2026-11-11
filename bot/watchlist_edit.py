"""Edit the watchlist at runtime (from Telegram) and save it to watchlist.local.yaml."""
from __future__ import annotations

import copy
import re
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from .config import LOCAL_PATH, Watchlist, parse_watchlist

_TIME = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")


class EditError(ValueError):
    """A user-facing reason an edit was refused."""


def _find(raw: dict, symbol: str) -> int | None:
    for i, a in enumerate(raw.get("assets") or []):
        if str(a["symbol"]).upper() == symbol.upper():
            return i
    return None


def _loc_code(raw: dict, code: str) -> str | None:
    return next((c for c in raw["locations"] if c.upper() == code.upper()), None)


def add_asset(raw: dict, symbol: str, location: str, asset_class: str, name: str | None = None) -> dict:
    raw = copy.deepcopy(raw)
    loc = _loc_code(raw, location)
    if loc is None:
        raise EditError(f"Unknown location {location!r}. Known: {', '.join(raw['locations'])}. "
                        "Add it first with /addlocation.")
    symbol = symbol.upper()
    if _find(raw, symbol) is not None:
        raise EditError(f"{symbol} is already in the watchlist.")
    defaults = raw["locations"][loc].get("ibkr") or {}
    if loc == "FX" or "." in symbol:
        ibkr = {"secType": "CASH", "exchange": "IDEALPRO", "currency": symbol.split(".")[-1]}
    else:
        ibkr = {"secType": "STK", "exchange": defaults.get("exchange", "SMART"),
                "currency": defaults.get("currency", "USD")}
    raw.setdefault("assets", []).append(
        {"symbol": symbol, "name": name or symbol, "asset_class": asset_class, "location": loc, "ibkr": ibkr})
    return raw


def remove_asset(raw: dict, symbol: str) -> dict:
    raw = copy.deepcopy(raw)
    i = _find(raw, symbol)
    if i is None:
        raise EditError(f"{symbol.upper()} isn't in the watchlist.")
    raw["assets"].pop(i)
    return raw


def add_location(raw: dict, code: str, timezone: str, open_: str, close: str, name: str | None = None) -> dict:
    raw = copy.deepcopy(raw)
    code = code.upper()
    if _loc_code(raw, code):
        raise EditError(f"Location {code} already exists.")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise EditError(f"Unknown timezone {timezone!r}. Use a name like Asia/Singapore or Europe/London.")
    for t in (open_, close):
        if not _TIME.match(t):
            raise EditError(f"Time {t!r} should look like 09:30.")
    open_, close = (t.zfill(5) for t in (open_, close))
    if open_ >= close:
        raise EditError("Open time must be before close time.")
    raw["locations"][code] = {"name": name or code, "timezone": timezone, "open": open_,
                              "close": close, "weekdays": [0, 1, 2, 3, 4]}
    return raw


def remove_location(raw: dict, code: str) -> dict:
    raw = copy.deepcopy(raw)
    loc = _loc_code(raw, code)
    if loc is None:
        raise EditError(f"Unknown location {code!r}.")
    used = [a["symbol"] for a in raw.get("assets") or [] if a["location"] == loc]
    if used:
        raise EditError(f"Remove these assets first: {', '.join(map(str, used))}.")
    del raw["locations"][loc]
    return raw


def save(raw: dict, path: Path = LOCAL_PATH) -> Watchlist:
    """Validate, then write atomically. Returns the parsed watchlist."""
    wl = parse_watchlist(raw)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("# Edited from Telegram. Delete this file to go back to watchlist.yaml.\n"
                   + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True))
    tmp.replace(path)
    return wl
