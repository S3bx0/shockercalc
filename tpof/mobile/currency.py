"""Warstwa prezentacji walut dla kosztow liczonych wewnetrznie w PLN."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

SUPPORTED_DISPLAY_CURRENCIES = ("PLN", "EUR", "USD")
NBP_SOURCE = "NBP"
NBP_RATE_URL = "https://api.nbp.pl/api/exchangerates/rates/a/{code}/?format=json"


@dataclass(frozen=True)
class ExchangeRates:
    """Kursy wyrazone jako liczba PLN za jedna jednostke waluty."""

    rates: Mapping[str, Decimal]
    date: str = ""
    source: str = NBP_SOURCE
    from_cache: bool = False

    def rate_for(self, currency: str) -> Decimal | None:
        code = str(currency or "").strip().upper()
        if code == "PLN":
            return Decimal("1")
        rate = self.rates.get(code)
        return rate if rate is not None and rate > 0 else None


def default_exchange_rates() -> ExchangeRates:
    return ExchangeRates({"PLN": Decimal("1")})


def _http_fetch(code: str, timeout: float) -> dict:
    request = Request(
        NBP_RATE_URL.format(code=code.lower()),
        headers={"Accept": "application/json", "User-Agent": "RefrigerationCalc/1"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - trusted NBP URL
        return json.loads(response.read().decode("utf-8"))


def fetch_nbp_exchange_rates(
    *,
    timeout: float = 5.0,
    fetcher: Callable[[str], Mapping[str, object]] | None = None,
) -> ExchangeRates:
    """Pobiera aktualne srednie kursy tabeli A NBP dla EUR i USD."""

    rates: dict[str, Decimal] = {"PLN": Decimal("1")}
    effective_dates: list[str] = []
    for code in SUPPORTED_DISPLAY_CURRENCIES[1:]:
        payload = fetcher(code) if fetcher is not None else _http_fetch(code, timeout)
        entries = payload.get("rates") if isinstance(payload, Mapping) else None
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"NBP response does not contain a rate for {code}")
        entry = entries[0]
        if not isinstance(entry, Mapping):
            raise ValueError(f"Invalid NBP rate entry for {code}")
        try:
            rate = Decimal(str(entry.get("mid")))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid NBP rate for {code}") from exc
        if rate <= 0:
            raise ValueError(f"Invalid NBP rate for {code}")
        date = str(entry.get("effectiveDate", "")).strip()
        if not date:
            raise ValueError(f"NBP response does not contain a date for {code}")
        rates[code] = rate
        effective_dates.append(date)
    return ExchangeRates(rates, date=min(effective_dates), source=NBP_SOURCE)


def save_cached_rates(cache_path: Path, exchange_rates: ExchangeRates) -> None:
    """Zapisuje ostatni poprawny komplet kursow w sposob atomowy."""

    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "source": exchange_rates.source or NBP_SOURCE,
        "date": exchange_rates.date,
        "rates": {code: str(rate) for code, rate in exchange_rates.rates.items()},
    }
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def load_cached_rates(cache_path: Path) -> ExchangeRates | None:
    """Odczytuje cache; uszkodzony lub niepelny plik jest ignorowany."""

    try:
        payload = json.loads(Path(cache_path).read_text(encoding="utf-8"))
        raw_rates = payload.get("rates", {})
        rates = {
            str(code).upper(): Decimal(str(value))
            for code, value in raw_rates.items()
        }
        if any(rates.get(code, Decimal("0")) <= 0 for code in SUPPORTED_DISPLAY_CURRENCIES):
            return None
        date = str(payload.get("date", "")).strip()
        if not date:
            return None
        return ExchangeRates(
            rates,
            date=date,
            source=str(payload.get("source", NBP_SOURCE)) or NBP_SOURCE,
            from_cache=True,
        )
    except (FileNotFoundError, OSError, ValueError, TypeError, InvalidOperation):
        return None


def get_exchange_rates(
    cache_path: Path,
    *,
    auto_update: bool = True,
    timeout: float = 5.0,
    fetcher: Callable[[str], Mapping[str, object]] | None = None,
) -> ExchangeRates:
    """Zwraca swieze kursy, a offline ostatni poprawny cache."""

    cached = load_cached_rates(cache_path)
    if auto_update:
        try:
            current = fetch_nbp_exchange_rates(timeout=timeout, fetcher=fetcher)
            save_cached_rates(cache_path, current)
            return current
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    return cached or default_exchange_rates()


def format_money(
    value_pln,
    currency: str,
    exchange_rates: ExchangeRates,
    language: str = "pl",
) -> str:
    """Formatuje kwote PLN w wybranej walucie bez zmiany wartosci zrodlowej."""

    code = str(currency or "PLN").strip().upper()
    if code not in SUPPORTED_DISPLAY_CURRENCIES:
        code = "PLN"
    rate = exchange_rates.rate_for(code)
    if rate is None:
        code = "PLN"
        rate = Decimal("1")
    amount = (Decimal(str(value_pln)) / rate).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    text = f"{amount:,.2f}"
    if str(language).casefold() == "pl":
        text = text.replace(",", " ").replace(".", ",")
    suffix = "zł" if code == "PLN" and str(language).casefold() == "pl" else code
    return f"{text} {suffix}"
