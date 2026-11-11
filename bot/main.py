"""Telegram entry point: commands + automatic reports at each market open."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from .config import DEFAULT_PATH, load_watchlist
from .data import make_provider
from .market_hours import is_open, next_open
from .report import analyse, format_report
from .sentiment import make_scorer

log = logging.getLogger("sentiment-bot")


def _env_chat_ids() -> list[int]:
    return [int(x) for x in os.getenv("REPORT_CHAT_IDS", "").replace(" ", "").split(",") if x]


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Hi! Your chat ID is {update.effective_chat.id}.\n\n"
        "/sentiment: ranked sentiment for the whole list\n"
        "/sentiment <class|location|symbol>: filter, e.g. /sentiment FX or /sentiment US\n"
        "/markets: which markets are open and when the next ones open\n"
        "/watchlist: what the bot covers")


async def cmd_sentiment(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    app = ctx.application.bot_data
    flt = " ".join(ctx.args) if ctx.args else None
    rows = await analyse(app["wl"], app["provider"], app["scorer"], flt)
    if not rows:
        await update.message.reply_text(f"Nothing in the watchlist matches {flt!r}.")
        return
    title = "Sentiment" + (f": {flt}" if flt else "")
    await update.message.reply_text(format_report(rows, app["wl"], title), parse_mode=ParseMode.HTML)


async def cmd_markets(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    wl = ctx.application.bot_data["wl"]
    now = datetime.now(timezone.utc)
    lines = []
    for loc in wl.locations.values():
        state = "🟢 open" if is_open(loc, now) else \
            f"⚫ opens {next_open(loc, now).astimezone(timezone.utc):%a %H:%M} UTC"
        lines.append(f"{loc.code} ({loc.name}): {state}")
    await update.message.reply_text("\n".join(lines))


async def cmd_watchlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    wl = ctx.application.bot_data["wl"]
    lines = [f"{a.symbol}: {a.name} · {a.asset_class} · {a.location}" for a in wl.assets]
    await update.message.reply_text("\n".join(lines))


async def job_market_open(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Fires report_offset_minutes after a location opens, then reschedules itself."""
    app = ctx.application
    code = ctx.job.data
    wl = app.bot_data["wl"]
    rows = await analyse(wl, app.bot_data["provider"], app.bot_data["scorer"])
    text = format_report(rows, wl, f"{wl.locations[code].name} open: sentiment")
    for chat_id in app.bot_data["chat_ids"]:
        await ctx.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
    schedule_open(app, code)


def schedule_open(app: Application, code: str) -> None:
    wl = app.bot_data["wl"]
    when = next_open(wl.locations[code]) + timedelta(minutes=wl.settings.report_offset_minutes)
    app.job_queue.run_once(job_market_open, when=when, data=code, name=f"open:{code}")
    log.info("Next %s report at %s UTC", code, when.astimezone(timezone.utc))


async def post_init(app: Application) -> None:
    await app.bot_data["provider"].connect()
    if app.bot_data["chat_ids"]:
        for code in app.bot_data["wl"].locations:
            schedule_open(app, code)
    else:
        log.warning("REPORT_CHAT_IDS empty: automatic market-open reports are off")


async def post_shutdown(app: Application) -> None:
    await app.bot_data["provider"].close()


def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN (from @BotFather) in .env")
    app = (Application.builder().token(token)
           .post_init(post_init).post_shutdown(post_shutdown).build())
    app.bot_data.update(
        wl=load_watchlist(os.getenv("WATCHLIST_PATH") or DEFAULT_PATH),
        provider=make_provider(
            os.getenv("DATA_PROVIDER", "stub"),
            **({} if os.getenv("DATA_PROVIDER", "stub") == "stub" else dict(
                host=os.getenv("IBKR_HOST", "127.0.0.1"),
                port=int(os.getenv("IBKR_PORT", "4001")),
                client_id=int(os.getenv("IBKR_CLIENT_ID", "17")),
                news_providers=os.getenv("IBKR_NEWS_PROVIDERS", "BRFG+BRFUPDN+DJNL"),
                market_data_type=int(os.getenv("IBKR_MARKET_DATA_TYPE", "1")),
                lookback_hours=int(os.getenv("NEWS_LOOKBACK_HOURS", "24"))))),
        scorer=make_scorer(
            os.getenv("SCORER", "lexicon"),
            **({} if os.getenv("SCORER", "lexicon").lower() != "claude" else dict(
                model=os.getenv("SENTIMENT_MODEL", "claude-opus-5-5"),
                effort=os.getenv("SENTIMENT_EFFORT", "low")))),
        chat_ids=_env_chat_ids(),
    )
    for name, fn in [("start", cmd_start), ("help", cmd_start), ("sentiment", cmd_sentiment),
                     ("markets", cmd_markets), ("watchlist", cmd_watchlist)]:
        app.add_handler(CommandHandler(name, fn))
    app.run_polling()


if __name__ == "__main__":
    main()
