
import pytest

from app.data.instruments import Instrument, InstrumentRegistry


@pytest.fixture
def reliance():
    return Instrument(
        instrument_id="NSE:INE002A01018",
        exchange="NSE",
        symbol="RELIANCE",
        company_name="Reliance Industries Ltd",
        isin="INE002A01018",
        provider_symbols={
            "zerodha": "RELIANCE",
            "yahoo": "RELIANCE.NS",
        },
    )


def test_add_and_get_instrument(reliance):
    registry = InstrumentRegistry()
    registry.add(reliance)

    result = registry.get("NSE:INE002A01018")

    assert result.symbol == "RELIANCE"
    assert result.exchange == "NSE"


def test_lookup_by_yahoo_symbol(reliance):
    registry = InstrumentRegistry()
    registry.add(reliance)

    result = registry.get_by_provider_symbol(
        "yahoo", "RELIANCE.NS"
    )

    assert result.instrument_id == "NSE:INE002A01018"


def test_lookup_by_zerodha_symbol(reliance):
    registry = InstrumentRegistry()
    registry.add(reliance)

    result = registry.get_by_provider_symbol(
        "zerodha", "RELIANCE"
    )

    assert result.company_name == "Reliance Industries Ltd"


def test_provider_and_symbol_lookup_is_case_insensitive(reliance):
    registry = InstrumentRegistry()
    registry.add(reliance)

    result = registry.get_by_provider_symbol(
        "YAHOO", "reliance.ns"
    )

    assert result.symbol == "RELIANCE"


def test_duplicate_instrument_id_is_rejected(reliance):
    registry = InstrumentRegistry()
    registry.add(reliance)

    with pytest.raises(ValueError, match="already exists"):
        registry.add(reliance)


def test_duplicate_provider_symbol_is_rejected(reliance):
    registry = InstrumentRegistry()
    registry.add(reliance)

    another = Instrument(
        instrument_id="NSE:OTHER",
        exchange="NSE",
        symbol="OTHER",
        company_name="Other Company",
        isin="INE000A01000",
        provider_symbols={"yahoo": "RELIANCE.NS"},
    )

    with pytest.raises(ValueError, match="already mapped"):
        registry.add(another)


def test_unknown_instrument_is_rejected():
    registry = InstrumentRegistry()

    with pytest.raises(KeyError, match="Instrument not found"):
        registry.get("NSE:UNKNOWN")


def test_unknown_provider_symbol_is_rejected():
    registry = InstrumentRegistry()

    with pytest.raises(KeyError, match="Unknown symbol"):
        registry.get_by_provider_symbol("yahoo", "UNKNOWN.NS")


def test_unsupported_exchange_is_rejected():
    with pytest.raises(ValueError, match="Unsupported exchange"):
        Instrument(
            instrument_id="MCX:UNKNOWN",
            exchange="MCX",
            symbol="UNKNOWN",
            company_name="Unknown Company",
            isin="INE000A01000",
            provider_symbols={"yahoo": "UNKNOWN.NS"},
        )


def test_registry_length(reliance):
    registry = InstrumentRegistry()

    assert len(registry) == 0

    registry.add(reliance)

    assert len(registry) == 1
