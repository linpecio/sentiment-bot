"""Fake data so the bot runs end to end without IBKR. Stable within a day."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from ..config import Asset
from .base import DataProvider, Headline, Quote

_TEMPLATES = [
    "{n} beats estimates as demand surges",
    "{n} shares rally after analyst upgrade",
    "{n} faces probe over accounting concerns",
    "{n} cuts guidance, warns of weak quarter",
    "{n} unchanged ahead of central bank decision",
    "{n} announces record buyback",
    "Analysts downgrade {n} citing slowing growth",
    "{n} steady as markets await data",
]


class StubProvider(DataProvider):
    def _rng(self, asset: Asset, salt: str) -> random.Random:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return random.Random(f"{asset.symbol}|{day}|{salt}")

    async def get_quote(self, asset: Asset) -> Quote:
        r = self._rng(asset, "q")
        prev = r.uniform(20, 500)
        return Quote(asset.symbol, prev * (1 + r.gauss(0, 0.02)), prev)

    async def get_headlines(self, asset: Asset, limit: int) -> list[Headline]:
        r = self._rng(asset, "h")
        now = datetime.now(timezone.utc)
        return [
            Headline(asset.symbol, now - timedelta(minutes=r.randint(1, 600)), "STUB",
                     r.choice(_TEMPLATES).format(n=asset.name))
            for _ in range(min(limit, r.randint(2, 6)))
        ]
