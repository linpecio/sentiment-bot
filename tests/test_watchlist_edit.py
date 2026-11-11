import pytest

from bot import watchlist_edit as w
from bot.config import DEFAULT_PATH, load_watchlist, read_raw

RAW = read_raw(DEFAULT_PATH)


def test_add_and_remove_asset():
    raw = w.add_asset(RAW, "tsla", "us", "Equity", "Tesla")
    a = raw["assets"][-1]
    assert a == {"symbol": "TSLA", "name": "Tesla", "asset_class": "Equity", "location": "US",
                 "ibkr": {"secType": "STK", "exchange": "SMART", "currency": "USD"}}
    assert len(RAW["assets"]) + 1 == len(raw["assets"])  # original untouched
    raw = w.remove_asset(raw, "TSLA")
    assert len(raw["assets"]) == len(RAW["assets"])


def test_add_asset_uses_location_and_fx_defaults():
    raw = w.add_asset(RAW, "BP", "UK", "Equity")
    assert raw["assets"][-1]["ibkr"] == {"secType": "STK", "exchange": "LSE", "currency": "GBP"}
    raw = w.add_asset(RAW, "gbp.usd", "FX", "FX")
    assert raw["assets"][-1]["ibkr"] == {"secType": "CASH", "exchange": "IDEALPRO", "currency": "USD"}


@pytest.mark.parametrize("args,msg", [
    (("SPY", "US", "Equity"), "already"),
    (("ZZZ", "MARS", "Equity"), "Unknown location"),
])
def test_add_asset_errors(args, msg):
    with pytest.raises(w.EditError, match=msg):
        w.add_asset(RAW, *args)


def test_remove_missing_asset():
    with pytest.raises(w.EditError, match="isn't in"):
        w.remove_asset(RAW, "NOPE")


def test_location_add_remove_and_guards():
    raw = w.add_location(RAW, "sg", "Asia/Singapore", "9:00", "17:00", "Singapore")
    assert raw["locations"]["SG"]["open"] == "09:00"
    raw = w.add_asset(raw, "D05", "SG", "Equity")
    with pytest.raises(w.EditError, match="Remove these assets first: D05"):
        w.remove_location(raw, "SG")
    raw = w.remove_location(w.remove_asset(raw, "D05"), "SG")
    assert "SG" not in raw["locations"]


@pytest.mark.parametrize("args,msg", [
    (("US", "America/New_York", "09:30", "16:00"), "already exists"),
    (("XX", "Mars/Olympus", "09:00", "17:00"), "Unknown timezone"),
    (("XX", "Asia/Singapore", "9am", "17:00"), "should look like"),
    (("XX", "Asia/Singapore", "17:00", "09:00"), "before close"),
])
def test_add_location_errors(args, msg):
    with pytest.raises(w.EditError, match=msg):
        w.add_location(RAW, *args)


def test_save_round_trip(tmp_path):
    path = tmp_path / "watchlist.local.yaml"
    wl = w.save(w.add_asset(RAW, "TSLA", "US", "Equity"), path)
    assert "TSLA" in [a.symbol for a in wl.assets]
    assert "TSLA" in [a.symbol for a in load_watchlist(path).assets]
