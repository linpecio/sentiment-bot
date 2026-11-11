"""Claude scorer and IBKR provider, tested with fake clients (no network)."""
import asyncio
import json
import math
from datetime import datetime, timezone
from types import SimpleNamespace as NS

from bot.config import load_watchlist
from bot.data.ibkr import IBKRProvider
from bot.report import analyse
from bot.sentiment import make_scorer
from bot.sentiment.claude import ClaudeScorer

WL = load_watchlist()


class FakeClaude:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail
        self.beta = NS(messages=NS(create=self.create))

    async def create(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise ConnectionError("down")
        lines = kw["messages"][0]["content"].splitlines()
        scores = [{"i": i, "score": 0.8 if "beats" in l else -0.7 if "cuts" in l else 0.0}
                  for i, l in enumerate(lines)]
        return NS(stop_reason="end_turn",
                  content=[NS(type="text", text=json.dumps({"scores": scores}))])


def test_claude_scores_batches_and_caches():
    fake = FakeClaude()
    s = ClaudeScorer(client=fake)
    out = asyncio.run(s.score(["Apple beats estimates", "Shell cuts guidance", "Flat day"]))
    assert out == [0.8, -0.7, 0.0]
    assert fake.calls[0]["output_config"]["format"]["type"] == "json_schema"
    asyncio.run(s.score(["Apple beats estimates"]))  # cached: no second call
    assert len(fake.calls) == 1


def test_claude_falls_back_to_keywords_on_error():
    out = asyncio.run(ClaudeScorer(client=FakeClaude(fail=True)).score(["Apple beats estimates"]))
    assert out[0] > 0


def test_report_uses_one_scoring_call():
    from bot.data.stub import StubProvider
    fake = FakeClaude()
    now = datetime(2026, 11, 11, 15, 0, tzinfo=timezone.utc)
    rows = asyncio.run(analyse(WL, StubProvider(), ClaudeScorer(client=fake), now=now))
    assert len(rows) == len(WL.assets) and len(fake.calls) == 1


def test_make_scorer_default_is_lexicon():
    assert type(make_scorer()).__name__ == "LexiconScorer"


class FakeIB:
    def __init__(self):
        self.news_args = None

    def isConnected(self):
        return True

    def reqMarketDataType(self, t):
        self.mdt = t

    async def qualifyContractsAsync(self, c):
        c.conId = 123
        return [c]

    async def reqTickersAsync(self, c):
        fx = c.secType == "CASH"
        return [NS(last=math.nan if fx else 105.0, close=100.0,
                   marketPrice=lambda: 1.1 if fx else 105.0, midpoint=lambda: 1.1)]

    async def reqHistoricalNewsAsync(self, conId, providers, start, end, n):
        self.news_args = (conId, providers, n)
        return [NS(time=end, providerCode="BRFG", articleId="1",
                   headline="{A:800015:L:en:K:n/a:C:0.9}Apple beats estimates")]


def test_ibkr_quotes_and_news():
    ib = FakeIB()
    p = IBKRProvider(ib=ib)
    asyncio.run(p.connect())
    aapl = next(a for a in WL.assets if a.symbol == "AAPL")
    eur = next(a for a in WL.assets if a.symbol == "EUR.USD")
    q = asyncio.run(p.get_quote(aapl))
    assert round(q.pct_change, 2) == 5.0
    assert asyncio.run(p.get_quote(eur)).last == 1.1  # FX has no last trade: midpoint
    heads = asyncio.run(p.get_headlines(aapl, 5))
    assert heads[0].text == "Apple beats estimates"
    assert ib.news_args == (123, "BRFG+BRFUPDN+DJNL", 5)


def test_ibkr_errors_do_not_break_report():
    class Broken(FakeIB):
        async def reqTickersAsync(self, c):
            raise TimeoutError

        async def reqHistoricalNewsAsync(self, *a):
            raise TimeoutError

    p = IBKRProvider(ib=Broken())
    aapl = WL.assets[2]
    assert asyncio.run(p.get_quote(aapl)) is None
    assert asyncio.run(p.get_headlines(aapl, 5)) == []
