
from dataclasses import dataclass
from typing import Mapping


SUPPORTED_EXCHANGES = {"NSE", "BSE"}


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    exchange: str
    symbol: str
    company_name: str
    isin: str
    provider_symbols: Mapping[str, str]

    def __post_init__(self):
        exchange = self.exchange.strip().upper()
        symbol = self.symbol.strip().upper()
        isin = self.isin.strip().upper()

        if exchange not in SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported exchange: {exchange}")

        if not all([
            self.instrument_id.strip(),
            symbol,
            self.company_name.strip(),
            isin,
        ]):
            raise ValueError("Instrument fields cannot be empty")

        if not self.provider_symbols:
            raise ValueError("At least one provider symbol is required")

        normalized_symbols = {}

        for provider, provider_symbol in self.provider_symbols.items():
            provider = provider.strip().lower()
            provider_symbol = provider_symbol.strip().upper()

            if not provider or not provider_symbol:
                raise ValueError("Provider names and symbols cannot be empty")

            normalized_symbols[provider] = provider_symbol

        object.__setattr__(self, "exchange", exchange)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "isin", isin)
        object.__setattr__(self, "provider_symbols", normalized_symbols)


class InstrumentRegistry:
    def __init__(self):
        self._instruments: dict[str, Instrument] = {}
        self._provider_index: dict[tuple[str, str], str] = {}

    def add(self, instrument: Instrument) -> None:
        if instrument.instrument_id in self._instruments:
            raise ValueError(
                f"Instrument already exists: {instrument.instrument_id}"
            )

        # Check provider symbol collisions before modifying the registry.
        for provider, symbol in instrument.provider_symbols.items():
            key = (provider, symbol)

            if key in self._provider_index:
                existing_id = self._provider_index[key]
                raise ValueError(
                    f"{provider} symbol {symbol} is already mapped "
                    f"to {existing_id}"
                )

        self._instruments[instrument.instrument_id] = instrument

        for provider, symbol in instrument.provider_symbols.items():
            self._provider_index[(provider, symbol)] = (
                instrument.instrument_id
            )

    def get(self, instrument_id: str) -> Instrument:
        try:
            return self._instruments[instrument_id]
        except KeyError:
            raise KeyError(
                f"Instrument not found: {instrument_id}"
            ) from None

    def get_by_provider_symbol(
        self,
        provider: str,
        symbol: str,
    ) -> Instrument:
        key = (provider.strip().lower(), symbol.strip().upper())

        instrument_id = self._provider_index.get(key)

        if instrument_id is None:
            raise KeyError(
                f"Unknown symbol for provider {key[0]}: {key[1]}"
            )

        return self._instruments[instrument_id]

    def list_all(self) -> list[Instrument]:
        return list(self._instruments.values())

    def __len__(self) -> int:
        return len(self._instruments)
    def get_by_exchange_symbol(
        self,
        exchange: str,
        symbol: str,
        ) -> Instrument:
        exchange = exchange.strip().upper()
        symbol = symbol.strip().upper()

        for instrument in self._instruments.values():
            if (
                instrument.exchange == exchange
                and instrument.symbol == symbol
            ):
                return instrument

        raise KeyError(
            f"Instrument not found: {exchange}:{symbol}"
        )