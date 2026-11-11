"""Build the sentiment report: open markets first, biggest absolute movers first."""
from __future__ import annotations

import asyncio
import html
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import Asset, Watchlist
from .data import DataProvider
from .market_hours import is_open, next_open
from .sentiment import SentimentScorer


@dataclass
class AssetSentiment:
    asset: Asset
    market_open: bool
    pct_change: float | None
    sentiment: float | None  # -1..+1, None if no headlines
    headline_count: int
    top_headline: str | None


def _matches(asset: Asset, flt: str | None) -> bool:
    if not flt:
        return True
    f = flt.lower()
    return f in (asset.asset_class.lower(), asset.location.lower(), asset.symbol.lower())


async def analyse(wl: Watchlist, provider: DataProvider, scorer: SentimentScorer,
                  flt: str | None = None, now: datetime | None = None) -> list[AssetSentiment]:
    now = now or datetime.now(timezone.utc)
    assets = [a for a in wl.assets if _matches(a, flt)]

    async def one(a: Asset) -> AssetSentiment:
        quote, heads = await asyncio.gather(
            provider.get_quote(a), provider.get_headlines(a, wl.settings.headlines_per_asset))
        scores = await scorer.score([h.text for h in heads]) if heads else []
        top = max(zip(scores, heads), key=lambda x: abs(x[0]))[1].text if heads else None
        return AssetSentiment(
            asset=a, market_open=is_open(wl.locations[a.location], now),
            pct_change=quote.pct_change if quote else None,
            sentiment=sum(scores) / len(scores) if scores else None,
            headline_count=len(heads), top_headline=top)

    results = await asyncio.gather(*(one(a) for a in assets))
    return rank(results)


def rank(rows: list[AssetSentiment]) -> list[AssetSentiment]:
    """Open markets first, then by absolute % move (heavy movers first)."""
    return sorted(rows, key=lambda r: (not r.market_open, -abs(r.pct_change or 0.0)))


def _label(s: float | None) -> str:
    if s is None:
        return "⚪ no news"
    if s >= 0.2:
        return f"🟢 bullish {s:+.2f}"
    if s <= -0.2:
        return f"🔴 bearish {s:+.2f}"
    return f"🟡 neutral {s:+.2f}"


def format_report(rows: list[AssetSentiment], wl: Watchlist, title: str,
                  now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    top_n = wl.settings.top_n
    open_rows = [r for r in rows if r.market_open][:top_n]
    closed = [r for r in rows if not r.market_open]
    lines = [f"<b>{html.escape(title)}</b>", f"<i>{now:%Y-%m-%d %H:%M} UTC</i>", ""]
    if open_rows:
        lines.append("<b>Open markets, biggest movers first</b>")
        for i, r in enumerate(open_rows, 1):
            chg = "n/a" if r.pct_change is None else f"{r.pct_change:+.2f}%"
            lines.append(f"{i}. <b>{html.escape(r.asset.symbol)}</b> ({html.escape(r.asset.asset_class)}, "
                         f"{r.asset.location}) {chg} · {_label(r.sentiment)}")
            if r.top_headline:
                lines.append(f"    ↳ {html.escape(r.top_headline)}")
    else:
        lines.append("No markets in your list are open right now.")
    if closed:
        opens = sorted((next_open(wl.locations[c], now), c) for c in {r.asset.location for r in closed})
        nxt = ", ".join(f"{c} {t.astimezone(timezone.utc):%a %H:%M}" for t, c in opens)
        lines += ["", f"<i>Closed: {len(closed)} assets. Next opens (UTC): {nxt}</i>"]
    return "\n".join(lines)
