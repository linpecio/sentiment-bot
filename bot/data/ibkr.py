"""IBKR provider: live quotes and news headlines through TWS / IB Gateway (ib_async).

- Quotes: snapshot ticker -> last (or midpoint for FX) and previous close.
- News: reqHistoricalNews per contract from the feeds in IBKR_NEWS_PROVIDERS
  (free: BRFG+BRFUPDN+DJNL; add +BZ if you pay for Benzinga), last NEWS_LOOKBACK_HOURS.
- One failing asset logs a warning and shows as "n/a" / "no news" instead of breaking the report.
"""
from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timedelta, timezone

from ..config import Asset
from .base import DataProvider, Headline, Quote

log = logging.getLogger(__name__)

# IBKR prefixes some headlines with a metadata block like "{A:800015:L:en:K:n/a:C:0.9}".
_META = re.compile(r"^\{[^}]*\}\s*")


def _num(x) -> float | None:
    return None if x is None or (isinstance(x, float) and math.isnan(x)) or x <= 0 else float(x)


class IBKRProvider(DataProvider):
    def __init__(self, host: str = "127.0.0.1", port: int = 4001, client_id: int = 17,
                 news_providers: str = "BRFG+BRFUPDN+DJNL", market_data_type: int = 1,
                 lookback_hours: int = 24, ib=None):
        self.host, self.port, self.client_id = host, port, client_id
        self.news_providers = news_providers
        self.market_data_type = market_data_type  # 1 live, 3 delayed (no subscription needed)
        self.lookback = timedelta(hours=lookback_hours)
        self.ib = ib
        self._contracts: dict[str, object] = {}

    async def connect(self) -> None:
        if self.ib is None:
            try:
                from ib_async import IB
            except ImportError as e:
                raise RuntimeError("DATA_PROVIDER=ibkr needs `pip install ib_async`") from e
            self.ib = IB()
        if not self.ib.isConnected():
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
        self.ib.reqMarketDataType(self.market_data_type)

    async def close(self) -> None:
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()

    def _build_contract(self, asset: Asset):
        from ib_async import Forex, Stock
        spec = asset.ibkr or {}
        if spec.get("secType") == "CASH":
            return Forex(asset.symbol.replace(".", ""), exchange=spec.get("exchange", "IDEALPRO"))
        return Stock(asset.symbol, spec.get("exchange", "SMART"), spec.get("currency", "USD"))

    async def _contract(self, asset: Asset):
        if asset.symbol not in self._contracts:
            c = self._build_contract(asset)
            qualified = await self.ib.qualifyContractsAsync(c)
            if not qualified or qualified[0] is None:
                raise LookupError(f"IBKR could not find a contract for {asset.symbol}")
            self._contracts[asset.symbol] = qualified[0]
        return self._contracts[asset.symbol]

    async def get_quote(self, asset: Asset) -> Quote | None:
        try:
            [t] = await self.ib.reqTickersAsync(await self._contract(asset))
            last = _num(t.last) or _num(t.marketPrice()) or _num(t.midpoint())
            prev = _num(t.close)
            if last is None or prev is None:
                log.warning("No price for %s (check market data subscription)", asset.symbol)
                return None
            return Quote(asset.symbol, last, prev)
        except Exception:  # noqa: BLE001
            log.exception("IBKR quote failed for %s", asset.symbol)
            return None

    async def get_headlines(self, asset: Asset, limit: int) -> list[Headline]:
        try:
            c = await self._contract(asset)
            end = datetime.now(timezone.utc)
            news = await self.ib.reqHistoricalNewsAsync(
                c.conId, self.news_providers, end - self.lookback, end, limit) or []
            return [Headline(asset.symbol, n.time, n.providerCode, _META.sub("", n.headline))
                    for n in news][:limit]
        except Exception:  # noqa: BLE001
            log.exception("IBKR news failed for %s", asset.symbol)
            return []
