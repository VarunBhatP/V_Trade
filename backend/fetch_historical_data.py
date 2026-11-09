
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.data.providers.zerodha_historical import (
    ZerodhaHistoricalProvider,
)

# Use Indian market-local dates.
today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
start_date = today - timedelta(days=14)

provider = ZerodhaHistoricalProvider()

df = provider.fetch_daily(
    exchange="NSE",
    symbol="RELIANCE",
    start_date=start_date,
    end_date=today,
)

print("\nHistorical data retrieved successfully.")
print(f"Rows: {len(df)}")
print(f"Date range: {start_date} to {today}")
print(f"Columns: {list(df.columns)}")

if not df.empty:
    print("\nLatest candles:")
    print(df.tail(10).to_string(index=False))

    print("\nData validation:")
    print("Dates sorted:", df["date"].is_monotonic_increasing)
    print("Duplicate dates:", df["date"].duplicated().sum())
    print("Missing values:", df.isnull().sum().sum())
else:
    print("\nNo candles returned for this date range.")
