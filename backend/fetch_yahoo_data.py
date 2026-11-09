
from datetime import date, timedelta
from pathlib import Path

from app.data.instruments import Instrument, InstrumentRegistry
from app.data.providers.yahoo_historical import YahooHistoricalProvider


def main():
    registry = InstrumentRegistry()

    registry.add(
        Instrument(
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
    )

    provider = YahooHistoricalProvider(
        instrument_registry=registry
    )

    end_date = date.today()
    start_date = end_date - timedelta(days=730)

    df = provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=start_date,
        end_date=end_date,
    )

    if df.empty:
        raise RuntimeError("Yahoo returned no historical data.")

    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "NSE_RELIANCE.csv"
    df.to_csv(output_file, index=False)

    print(f"Downloaded candles: {len(df)}")
    print(f"First date: {df['date'].iloc[0]}")
    print(f"Last date: {df['date'].iloc[-1]}")
    print(f"Saved to: {output_file}")
    print("\nLatest 5 candles:")
    print(df.tail())


if __name__ == "__main__":
    main()
