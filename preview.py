"""Print a report in the terminal without Telegram: python preview.py [filter]"""
import asyncio, re, sys

from bot.config import load_watchlist
from bot.data.stub import StubProvider
from bot.report import analyse, format_report
from bot.sentiment import LexiconScorer

wl = load_watchlist()
flt = sys.argv[1] if len(sys.argv) > 1 else None
rows = asyncio.run(analyse(wl, StubProvider(), LexiconScorer(), flt))
print(re.sub(r"</?[bi]>", "", format_report(rows, wl, "Preview")))
