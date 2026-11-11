# Sentiment bot (skeleton)

Telegram bot that reads a static list of asset classes and locations, knows when each
market opens, and ranks sentiment with the biggest movers in open markets first.

## Run it
1. Create a bot: message @BotFather on Telegram, `/newbot`, copy the token.
2. `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. `cp .env.example .env` and paste the token into `TELEGRAM_BOT_TOKEN`.
4. `python -m bot.main`, then send `/start` to your bot to get your chat ID.
5. Put that chat ID in `REPORT_CHAT_IDS` and restart to get automatic reports
   `report_offset_minutes` after each market opens.

Try the report without Telegram: `python preview.py` or `python preview.py FX`.
It reads `DATA_PROVIDER` and `SCORER` from `.env`, so use it to test IBKR and Claude first.

## Turn on live data and Claude sentiment
Do these one at a time and check `python preview.py` after each.
1. **Claude scoring:** put an API key from console.anthropic.com in `ANTHROPIC_API_KEY`
   and set `SCORER=claude`. All headlines in a report are scored in one call; the same
   headline is never scored twice. If the call fails, the keyword scorer is used for that report.
   `SENTIMENT_MODEL=claude-haiku-5-5` is much cheaper than the default.
2. **IBKR data:** start TWS or IB Gateway and log in, enable the API
   (Configure > Settings > API > Settings: "Enable ActiveX and Socket Clients"),
   check the port (IB Gateway live 4001, paper 4002; TWS live 7496, paper 7497),
   then set `DATA_PROVIDER=ibkr` and `IBKR_PORT`. Without live market data subscriptions,
   set `IBKR_MARKET_DATA_TYPE=3` for free delayed prices.
Tests: `pip install -r requirements-dev.txt && pytest`.

## Commands
- `/sentiment [filter]`: ranked report; filter by asset class, location or symbol
- `/markets`: open/closed state and next open per location
- `/watchlist`: the static list

## Layout
- `config/watchlist.yaml`: locations (timezone, hours) and assets. Edit this to change coverage.
- `bot/market_hours.py`: open/next-open logic (no holiday calendar yet)
- `bot/data/`: `stub.py` fake prices + headlines; `ibkr.py` live quotes + news via TWS/IB Gateway
- `bot/sentiment/`: `claude.py` Claude headline scorer; `lexicon.py` keyword fallback
- `bot/report.py`: ranking (open markets first, then absolute % move) and message format

## Not done yet
- Testing IBKR against a real TWS / IB Gateway session (written against ib_async 2.1, tested with a fake)
- Exchange holidays and lunch breaks (Tokyo, Hong Kong)
