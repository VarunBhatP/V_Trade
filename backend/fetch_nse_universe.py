
from collections import defaultdict
from datetime import date
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd


INDEX_URLS = {
    "NIFTY_50": (
        "https://www.niftyindices.com/IndexConstituent/"
        "ind_nifty50list.csv",
        50,
    ),
    "NIFTY_NEXT_50": (
        "https://www.niftyindices.com/IndexConstituent/"
        "ind_niftynext50list.csv",
        50,
    ),
    "NIFTY_MIDCAP_150": (
        "https://www.niftyindices.com/IndexConstituent/"
        "ind_niftymidcap150list.csv",
        150,
    ),
    "NIFTY_SMALLCAP_250": (
        "https://www.niftyindices.com/IndexConstituent/"
        "ind_niftysmallcap250list.csv",
        250,
    ),
}


def download_csv(url: str) -> pd.DataFrame:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv,*/*",
        },
    )

    with urlopen(request, timeout=30) as response:
        content = response.read()

    return pd.read_csv(BytesIO(content))



def normalize_constituents(
    index_name: str,
    df: pd.DataFrame,
) -> pd.DataFrame:

    df.columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

    required = {"symbol", "company name", "isin code"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{index_name}: missing columns {sorted(missing)}. "
            f"Received: {list(df.columns)}"
        )

    # Remove repeated header rows embedded in the downloaded CSV
    header_mask = (
        df["symbol"].astype(str).str.strip().str.lower().eq("symbol")
        & df["company name"].astype(str).str.strip().str.lower().eq("company name")
        & df["isin code"].astype(str).str.strip().str.lower().eq("isin code")
    )

    df = df.loc[~header_mask].copy()
    print(f"{index_name}: rows before filter = {len(header_mask)}")
    print(f"{index_name}: repeated headers found = {header_mask.sum()}")
    print(f"{index_name}: rows after filter = {len(df)}")

    result = pd.DataFrame({
        "symbol": df["symbol"].astype(str).str.strip().str.upper(),
        "company_name": df["company name"].astype(str).str.strip(),
        "isin": df["isin code"].astype(str).str.strip().str.upper(),
    })

    if result.empty:
        raise ValueError(f"{index_name}: no constituents received")

    if result[["symbol", "company_name", "isin"]].isnull().any().any():
        raise ValueError(f"{index_name}: missing constituent values")

    if result[["symbol", "company_name", "isin"]].eq("").any().any():
        raise ValueError(f"{index_name}: empty constituent values")

    if result["isin"].duplicated().any():
        raise ValueError(f"{index_name}: duplicate ISINs found")

    result["index"] = index_name

    return result



def main():
    memberships = []
    print("Downloading official NSE Indices constituents...\n")

    for index_name, (url, expected_count) in INDEX_URLS.items():
        print(f"Downloading {index_name}...")

        raw = download_csv(url)
        df = normalize_constituents(index_name, raw)

        print(
            f"  Received: {len(df)} "
            f"(expected approximately {expected_count})"
        )

        memberships.append(df)

    combined = pd.concat(memberships, ignore_index=True)

    # Group by ISIN so one security can retain multiple memberships.
    grouped = defaultdict(lambda: {
        "symbol": None,
        "company_name": None,
        "indices": set(),
    })

    for row in combined.to_dict("records"):
        isin = row["isin"]
        entry = grouped[isin]

        if entry["symbol"] is not None:
            if entry["symbol"] != row["symbol"]:
                raise ValueError(
                    f"Conflicting symbols for ISIN {isin}: "
                    f"{entry['symbol']} and {row['symbol']}"
                )

        entry["symbol"] = row["symbol"]
        entry["company_name"] = row["company_name"]
        entry["indices"].add(row["index"])

    output_rows = []

    for isin, entry in grouped.items():
        output_rows.append({
            "exchange": "NSE",
            "symbol": entry["symbol"],
            "company_name": entry["company_name"],
            "isin": isin,
            "indices": ";".join(sorted(entry["indices"])),
        })

    result = pd.DataFrame(output_rows)
    result = result.sort_values("symbol").reset_index(drop=True)

    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "data" / "universe"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "nse_constituents.csv"
    result.to_csv(output_file, index=False)

    print("\n========== UNIVERSE SUMMARY ==========")
    print(f"Index memberships: {len(combined)}")
    print(f"Unique securities: {len(result)}")
    print(f"Duplicate memberships removed: {len(combined) - len(result)}")
    print(f"Snapshot date: {date.today()}")
    print(f"Saved to: {output_file}")

    print("\nUnique stocks by index:")
    for index_name in INDEX_URLS:
        count = sum(
            index_name in indices.split(";")
            for indices in result["indices"]
        )
        print(f"  {index_name}: {count}")

    print("\nFirst 10 securities:")
    print(result.head(10).to_string(index=False))


if __name__ == "__main__":
    main()