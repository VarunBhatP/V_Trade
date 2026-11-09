
import pytest

from app.data.universe import InstrumentUniverse


@pytest.fixture
def universe_csv(tmp_path):
    path = tmp_path / "nse_universe.csv"

    path.write_text(
        "exchange,symbol,company_name,isin,yahoo_symbol,"
        "zerodha_symbol,indices\n"
        "NSE,RELIANCE,Reliance Industries Ltd,INE002A01018,"
        "RELIANCE.NS,RELIANCE,NIFTY_50;NIFTY_100\n"
        "NSE,TCS,Tata Consultancy Services Ltd,INE467B01029,"
        "TCS.NS,TCS,NIFTY_50\n",
        encoding="utf-8",
    )

    return path


def test_load_universe(universe_csv):
    universe = InstrumentUniverse.from_csv(universe_csv)

    assert universe.count() == 2


def test_load_provider_symbols(universe_csv):
    universe = InstrumentUniverse.from_csv(universe_csv)

    instrument = universe.registry.get_by_exchange_symbol(
        "NSE", "RELIANCE"
    )

    assert instrument.provider_symbols["yahoo"] == "RELIANCE.NS"
    assert instrument.provider_symbols["zerodha"] == "RELIANCE"


def test_get_by_index(universe_csv):
    universe = InstrumentUniverse.from_csv(universe_csv)

    nifty_50 = universe.get_by_index("NIFTY_50")

    assert len(nifty_50) == 2


def test_multiple_index_memberships(universe_csv):
    universe = InstrumentUniverse.from_csv(universe_csv)

    nifty_100 = universe.get_by_index("NIFTY_100")

    assert len(nifty_100) == 1
    assert nifty_100[0].symbol == "RELIANCE"


def test_index_names(universe_csv):
    universe = InstrumentUniverse.from_csv(universe_csv)

    assert universe.get_index_names() == [
        "NIFTY_100",
        "NIFTY_50",
    ]


def test_count_by_index(universe_csv):
    universe = InstrumentUniverse.from_csv(universe_csv)

    assert universe.count_by_index() == {
        "NIFTY_100": 1,
        "NIFTY_50": 2,
    }


def test_unknown_index_returns_empty_list(universe_csv):
    universe = InstrumentUniverse.from_csv(universe_csv)

    assert universe.get_by_index("UNKNOWN") == []


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        InstrumentUniverse.from_csv("missing_universe.csv")


def test_missing_columns(tmp_path):
    path = tmp_path / "invalid.csv"
    path.write_text("symbol,company_name\nRELIANCE,Reliance\n")

    with pytest.raises(ValueError, match="missing columns"):
        InstrumentUniverse.from_csv(path)


def test_missing_required_value(tmp_path):
    path = tmp_path / "invalid.csv"

    path.write_text(
        "exchange,symbol,company_name,isin,yahoo_symbol,indices\n"
        "NSE,RELIANCE,Reliance Industries Ltd,,RELIANCE.NS,NIFTY_50\n"
    )

    with pytest.raises(ValueError, match="Missing required value"):
        InstrumentUniverse.from_csv(path)


def test_duplicate_instrument_rejected(tmp_path):
    path = tmp_path / "duplicate.csv"

    path.write_text(
        "exchange,symbol,company_name,isin,yahoo_symbol,indices\n"
        "NSE,RELIANCE,Reliance Industries Ltd,INE002A01018,"
        "RELIANCE.NS,NIFTY_50\n"
        "NSE,RELIANCE,Reliance Industries Ltd,INE002A01018,"
        "RELIANCE.NS,NIFTY_100\n"
    )

    with pytest.raises(ValueError):
        InstrumentUniverse.from_csv(path)
