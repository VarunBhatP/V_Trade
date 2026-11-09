
import csv
from pathlib import Path

from app.data.instruments import Instrument, InstrumentRegistry


REQUIRED_COLUMNS = {
    "exchange",
    "symbol",
    "company_name",
    "isin",
    "yahoo_symbol",
    "indices",
}


class InstrumentUniverse:
    """Loads and manages a data-driven stock universe."""

    def __init__(self):
        self.registry = InstrumentRegistry()
        self._memberships: dict[str, set[str]] = {}

    @classmethod
    def from_csv(cls, file_path: str | Path):
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"Universe file not found: {path}")

        universe = cls()

        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames:
                raise ValueError("Universe CSV has no header")

            missing = REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing:
                raise ValueError(
                    f"Universe CSV missing columns: {sorted(missing)}"
                )

            for row_number, row in enumerate(reader, start=2):
                exchange = (row["exchange"] or "").strip().upper()
                symbol = (row["symbol"] or "").strip().upper()
                company_name = (row["company_name"] or "").strip()
                isin = (row["isin"] or "").strip().upper()
                yahoo_symbol = (row["yahoo_symbol"] or "").strip().upper()

                if not all([
                    exchange,
                    symbol,
                    company_name,
                    isin,
                    yahoo_symbol,
                ]):
                    raise ValueError(
                        f"Missing required value in universe CSV row {row_number}"
                    )

                indices = {
                    index.strip().upper()
                    for index in (row["indices"] or "").split(";")
                    if index.strip()
                }

                if not indices:
                    raise ValueError(
                        f"No index membership in universe CSV row {row_number}"
                    )

                provider_symbols = {"yahoo": yahoo_symbol}

                zerodha_symbol = (
                    row.get("zerodha_symbol") or ""
                ).strip().upper()

                if zerodha_symbol:
                    provider_symbols["zerodha"] = zerodha_symbol

                instrument = Instrument(
                    instrument_id=f"{exchange}:{isin}",
                    exchange=exchange,
                    symbol=symbol,
                    company_name=company_name,
                    isin=isin,
                    provider_symbols=provider_symbols,
                )

                universe.registry.add(instrument)

                for index in indices:
                    universe._memberships.setdefault(
                        index, set()
                    ).add(instrument.instrument_id)

        if len(universe.registry) == 0:
            raise ValueError("Universe CSV contains no instruments")

        return universe

    def get_all(self) -> list[Instrument]:
        return self.registry.list_all()

    def get_by_index(self, index: str) -> list[Instrument]:
        index = index.strip().upper()

        instrument_ids = self._memberships.get(index, set())

        return [
            self.registry.get(instrument_id)
            for instrument_id in instrument_ids
        ]

    def get_index_names(self) -> list[str]:
        return sorted(self._memberships.keys())

    def count(self) -> int:
        return len(self.registry)

    def count_by_index(self) -> dict[str, int]:
        return {
            index: len(instrument_ids)
            for index, instrument_ids in sorted(
                self._memberships.items()
            )
        }
