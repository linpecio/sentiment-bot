import asyncio
from datetime import datetime, timezone

from bot.config import load_watchlist
from bot.data.stub import StubProvider
from bot.market_hours import is_open, next_open
from bot.report import AssetSentiment, analyse, format_report, rank
from bot.sentiment import LexiconScorer

WL = load_watchlist()


def test_watchlist_loads():
    assert WL.assets and "US" in WL.locations
    assert {"Equity", "FX"} <= set(WL.asset_classes())


def test_us_market_hours():
    us = WL.locations["US"]
    assert is_open(us, datetime(2026, 11, 11, 15, 0, tzinfo=timezone.utc))      # Wed 10:00 ET
    assert not is_open(us, datetime(2026, 11, 11, 13, 0, tzinfo=timezone.utc))  # 08:00 ET
    assert not is_open(us, datetime(2026, 11, 14, 15, 0, tzinfo=timezone.utc))  # Saturday
    nxt = next_open(us, datetime(2026, 11, 13, 22, 0, tzinfo=timezone.utc))      # Fri evening
    assert nxt.weekday() == 0 and nxt.hour == 9 and nxt.minute == 30


def test_rank_open_first_then_abs_move():
    a = WL.assets
    rows = [AssetSentiment(a[0], False, 9.0, 0, 0, None),
            AssetSentiment(a[1], True, -3.0, 0, 0, None),
            AssetSentiment(a[2], True, 1.0, 0, 0, None)]
    assert [r.pct_change for r in rank(rows)] == [-3.0, 1.0, 9.0]


def test_lexicon_scores():
    s = asyncio.run(LexiconScorer().score(["Apple beats estimates", "Probe warns of weak sales", "Flat day"]))
    assert s[0] > 0 and s[1] < 0 and s[2] == 0


def test_end_to_end_with_stub():
    now = datetime(2026, 11, 11, 15, 0, tzinfo=timezone.utc)
    rows = asyncio.run(analyse(WL, StubProvider(), LexiconScorer(), now=now))
    assert len(rows) == len(WL.assets)
    text = format_report(rows, WL, "Test", now)
    assert "biggest movers first" in text
    fx = asyncio.run(analyse(WL, StubProvider(), LexiconScorer(), "FX", now=now))
    assert {r.asset.asset_class for r in fx} == {"FX"}
