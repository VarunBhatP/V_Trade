
from datetime import date

from app.data.universe import InstrumentUniverse
from app.data.providers.yahoo_historical import YahooHistoricalProvider


universe = InstrumentUniverse.from_csv(
    "../data/universe/validated_universe.csv"
)

provider = YahooHistoricalProvider(
    instrument_registry=universe.registry
)

df = provider.fetch_daily(
    exchange="NSE",
    symbol="360ONE",
    start_date=date(2026, 10, 1),
    end_date=date(2026, 11, 9),
)

print("\n========== YAHOO INTEGRATION CHECK ==========")
print("Instrument:", universe.registry.get_by_exchange_symbol(
    "NSE", "360ONE"
))
print("Candles fetched:", len(df))

if not df.empty:
    print("\nFirst candle:")
    print(df.head(1).to_string(index=False))

    print("\nLatest candle:")
    print(df.tail(1).to_string(index=False))
