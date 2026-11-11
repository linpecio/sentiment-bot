"""Print a report in the terminal without Telegram: python preview.py [filter]

Uses DATA_PROVIDER and SCORER from .env, so you can test IBKR and Claude before
switching the bot over (defaults: stub data, keyword scorer).
"""
import asyncio, os, re, sys

from bot.config import load_watchlist
from bot.data import make_provider
from bot.report import analyse, format_report
from bot.sentiment import make_scorer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


async def main(flt):
    wl = load_watchlist()
    data = os.getenv("DATA_PROVIDER", "stub").lower()
    provider = make_provider(data, **({} if data == "stub" else dict(
        host=os.getenv("IBKR_HOST", "127.0.0.1"), port=int(os.getenv("IBKR_PORT", "4001")),
        client_id=int(os.getenv("IBKR_CLIENT_ID", "17")) + 1,  # don't clash with the running bot
        news_providers=os.getenv("IBKR_NEWS_PROVIDERS", "BRFG+BRFUPDN+DJNL"),
        market_data_type=int(os.getenv("IBKR_MARKET_DATA_TYPE", "1")))))
    sc = os.getenv("SCORER", "lexicon").lower()
    scorer = make_scorer(sc, **({} if sc != "claude" else dict(
        model=os.getenv("SENTIMENT_MODEL", "claude-opus-5-5"),
        effort=os.getenv("SENTIMENT_EFFORT", "low"))))
    await provider.connect()
    try:
        rows = await analyse(wl, provider, scorer, flt)
    finally:
        await provider.close()
    print(re.sub(r"</?[bi]>", "", format_report(rows, wl, "Preview")))


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
