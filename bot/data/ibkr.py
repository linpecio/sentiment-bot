"""IBKR provider (not wired in yet).

Plan (see research/ibkr-sentiment-costs.md):
- Connect to TWS / IB Gateway with ib_async (pip install ib_async).
- Quotes: reqMktData snapshot -> last and close (prev close) for % move.
- News: reqHistoricalNews(conId, providers, start, end, n) on a schedule
  around market open, using free feeds BRFG+BRFUPDN+DJNL (+BZ if paid).
- Stay under 100 market data lines and API pacing limits.
"""
from __future__ import annotations

from ..config import Asset
from .base import DataProvider, Headline, Quote


class IBKRProvider(DataProvider):
    def __init__(self, host: str = "127.0.0.1", port: int = 4001, client_id: int = 17,
                 news_providers: str = "BRFG+BRFUPDN+DJNL"):
        self.host, self.port, self.client_id = host, port, client_id
        self.news_providers = news_providers
        self.ib = None

    async def connect(self) -> None:
        try:
            from ib_async import IB
        except ImportError as e:
            raise RuntimeError("DATA_PROVIDER=ibkr needs `pip install ib_async`") from e
        self.ib = IB()
        await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)

    async def close(self) -> None:
        if self.ib:
            self.ib.disconnect()

    async def get_quote(self, asset: Asset) -> Quote | None:
        raise NotImplementedError("IBKR quotes: next step")

    async def get_headlines(self, asset: Asset, limit: int) -> list[Headline]:
        raise NotImplementedError("IBKR news: next step")
