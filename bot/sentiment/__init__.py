from .base import SentimentScorer
from .lexicon import LexiconScorer


def make_scorer(name: str | None = None, **kwargs) -> SentimentScorer:
    name = (name or "lexicon").lower()
    if name == "lexicon":
        return LexiconScorer()
    if name == "claude":
        from .claude import ClaudeScorer
        return ClaudeScorer(**kwargs)
    raise ValueError(f"Unknown SCORER {name!r}")


__all__ = ["SentimentScorer", "LexiconScorer", "make_scorer"]
