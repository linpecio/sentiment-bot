from __future__ import annotations

from abc import ABC, abstractmethod


class SentimentScorer(ABC):
    """Scores a headline from -1 (bearish) to +1 (bullish)."""

    @abstractmethod
    async def score(self, texts: list[str]) -> list[float]: ...
