"""Placeholder keyword scorer. Replace with an LLM or FinBERT later."""
from __future__ import annotations

import re

from .base import SentimentScorer

POS = {"beat", "beats", "surge", "surges", "rally", "rallies", "upgrade", "upgrades",
       "record", "buyback", "growth", "gain", "gains", "jump", "jumps", "strong", "raise", "raises"}
NEG = {"miss", "misses", "probe", "cut", "cuts", "warn", "warns", "weak", "downgrade",
       "downgrades", "slowing", "fall", "falls", "drop", "drops", "lawsuit", "concerns", "plunge"}


class LexiconScorer(SentimentScorer):
    async def score(self, texts: list[str]) -> list[float]:
        out = []
        for t in texts:
            words = re.findall(r"[a-z]+", t.lower())
            p = sum(w in POS for w in words)
            n = sum(w in NEG for w in words)
            out.append(0.0 if p + n == 0 else (p - n) / (p + n))
        return out
