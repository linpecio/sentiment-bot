"""Claude headline scorer: one API call per batch of headlines, -1 (bearish) to +1 (bullish).

Needs ANTHROPIC_API_KEY. Falls back to the keyword scorer if the API call fails,
so a report is never lost because of a network or billing problem.
"""
from __future__ import annotations

import json
import logging

from .base import SentimentScorer
from .lexicon import LexiconScorer

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5-5"

SYSTEM = (
    "You score financial news headlines for a market-sentiment report. For each numbered "
    "headline, give the likely short-term effect on the price of the asset it is about: "
    "-1 = clearly bearish, 0 = neutral or no price relevance, +1 = clearly bullish. Use the "
    "full range and weigh mixed news (e.g. beats estimates but cuts guidance) honestly."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"i": {"type": "integer"}, "score": {"type": "number"}},
                "required": ["i", "score"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["scores"],
    "additionalProperties": False,
}


class ClaudeScorer(SentimentScorer):
    def __init__(self, model: str = DEFAULT_MODEL, effort: str = "low", client=None):
        if client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError as e:
                raise RuntimeError("SCORER=claude needs `pip install anthropic`") from e
            client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY
        self.client, self.model, self.effort = client, model, effort
        self.fallback = LexiconScorer()
        self._cache: dict[str, float] = {}  # same headline is never scored twice

    async def score(self, texts: list[str]) -> list[float]:
        todo = list(dict.fromkeys(t for t in texts if t not in self._cache))
        if todo:
            try:
                for t, s in zip(todo, await self._ask(todo)):
                    self._cache[t] = s
            except Exception:  # noqa: BLE001 - never lose a report to a scoring error
                log.exception("Claude scoring failed; using keyword scorer for this batch")
                return await self.fallback.score(texts)
        return [self._cache[t] for t in texts]

    async def _ask(self, texts: list[str]) -> list[float]:
        numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(texts))
        resp = await self.client.beta.messages.create(
            model=self.model,
            max_tokens=4000,
            system=SYSTEM,
            messages=[{"role": "user", "content": numbered}],
            output_config={"effort": self.effort,
                           "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError("Claude declined to score this batch")
        text = next(b.text for b in resp.content if b.type == "text")
        by_index = {int(x["i"]): float(x["score"]) for x in json.loads(text)["scores"]}
        return [max(-1.0, min(1.0, by_index.get(i, 0.0))) for i in range(len(texts))]
