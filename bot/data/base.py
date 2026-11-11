"""Interfaces the bot uses for prices and news. Swap stub <-> IBKR here."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from ..config import Asset


@dataclass(frozen=True)
class Quote:
    symbol: str
    last: float
    prev_close: float

    @property
    def pct_change(self) -> float:
        return 0.0 if not self.prev_close else (self.last / self.prev_close - 1) * 100


@dataclass(frozen=True)
class Headline:
    symbol: str
    time: datetime
    provider: str
    text: str


class DataProvider(ABC):
    async def connect(self) -> None:  # optional
        return None

    async def close(self) -> None:  # optional
        return None

    @abstractmethod
    async def get_quote(self, asset: Asset) -> Quote | None: ...

    @abstractmethod
    async def get_headlines(self, asset: Asset, limit: int) -> list[Headline]: ...
