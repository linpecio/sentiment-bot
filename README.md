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
Tests: `pip install -r requirements-dev.txt && pytest`.

## Commands
- `/sentiment [filter]`: ranked report; filter by asset class, location or symbol
- `/markets`: open/closed state and next open per location
- `/watchlist`: the static list

## Layout
- `config/watchlist.yaml`: locations (timezone, hours) and assets. Edit this to change coverage.
- `bot/market_hours.py`: open/next-open logic (no holiday calendar yet)
- `bot/data/`: `stub.py` fake prices + headlines; `ibkr.py` placeholder for TWS/IB Gateway
- `bot/sentiment/`: `lexicon.py` placeholder keyword scorer; swap for an LLM later
- `bot/report.py`: ranking (open markets first, then absolute % move) and message format

## Not done yet
- Live IBKR quotes and news (`DATA_PROVIDER=ibkr`)
- Real sentiment model
- Exchange holidays and lunch breaks (Tokyo, Hong Kong)
