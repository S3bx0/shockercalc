"""Warstwa prezentacji walut dla kosztow liczonych wewnetrznie w PLN."""

from __future__ import annotations

import json
import ssl
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date as calendar_date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from http.client import HTTPException
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
        return rate if rate is not None and rate.is_finite() and rate > 0 else None


def default_exchange_rates() -> ExchangeRates:
    return ExchangeRates({"PLN": Decimal("1")})


def _positive_rate(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("Invalid exchange rate type")
    try:
        rate = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid exchange rate") from exc
    if not rate.is_finite() or rate <= 0:
        raise ValueError("Exchange rate must be finite and positive")
    return rate


def _rate_date(value: object) -> str:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("Expected an ISO exchange-rate date")
    if calendar_date.fromisoformat(value).isoformat() != value:
        raise ValueError("Expected an ISO exchange-rate date")
    return value


def _complete_rates(values: object) -> dict[str, Decimal]:
    if not isinstance(values, Mapping):
        raise ValueError("Expected an exchange-rate mapping")
    rates = {code: _positive_rate(values.get(code)) for code in SUPPORTED_DISPLAY_CURRENCIES}
    if rates["PLN"] != 1:
        raise ValueError("The base PLN exchange rate must equal one")
    return rates


def _http_fetch(code: str, timeout: float) -> dict:
    request = Request(
        NBP_RATE_URL.format(code=code.lower()),
        headers={"Accept": "application/json", "User-Agent": "RefrigerationCalc/1"},
    )
    context = None
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        # Desktop Python normally has a working platform certificate store.
        context = ssl.create_default_context()
    with urlopen(  # noqa: S310 - trusted NBP URL
        request,
        timeout=timeout,
        context=context,
    ) as response:
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
        if not isinstance(payload, Mapping) or payload.get("code") != code:
            raise ValueError(f"Unexpected NBP currency code for {code}")
        entries = payload.get("rates")
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"NBP response does not contain a rate for {code}")
        entry = entries[0]
        if not isinstance(entry, Mapping):
            raise ValueError(f"Invalid NBP rate entry for {code}")
        rate = _positive_rate(entry.get("mid"))
        date = _rate_date(entry.get("effectiveDate"))
        rates[code] = rate
        effective_dates.append(date)
    return ExchangeRates(rates, date=min(effective_dates), source=NBP_SOURCE)


def save_cached_rates(cache_path: Path, exchange_rates: ExchangeRates) -> None:
    """Zapisuje ostatni poprawny komplet kursow w sposob atomowy."""

    rates = _complete_rates(exchange_rates.rates)
    date = _rate_date(exchange_rates.date)
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "source": NBP_SOURCE,
        "date": date,
        "rates": {code: str(rate) for code, rate in rates.items()},
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
        if not isinstance(payload, Mapping):
            return None
        rates = _complete_rates(payload.get("rates"))
        date = _rate_date(payload.get("date"))
        if payload.get("source", NBP_SOURCE) != NBP_SOURCE:
            return None
        return ExchangeRates(
            rates,
            date=date,
            source=NBP_SOURCE,
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
        except (OSError, ValueError, TypeError, HTTPException):
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


def format_exchange_rate(
    currency: str,
    exchange_rates: ExchangeRates,
    language: str,
) -> str | None:
    """Formats one display-currency rate as PLN per currency unit."""

    code = str(currency or "").strip().upper()
    if code not in SUPPORTED_DISPLAY_CURRENCIES:
        return None
    rate = exchange_rates.rate_for(code)
    if rate is None:
        return None
    value = f"{rate.quantize(Decimal('0.0001')):.4f}"
    if str(language).casefold() == "pl":
        value = value.replace(".", ",")
    return f"1 {code} = {value} PLN"


def convert_display_amount_to_pln(
    value,
    currency: str,
    exchange_rates: ExchangeRates,
) -> Decimal:
    """Converts a user-entered display amount to the internal PLN value."""

    code = str(currency or "PLN").strip().upper()
    if code not in SUPPORTED_DISPLAY_CURRENCIES:
        code = "PLN"
    rate = exchange_rates.rate_for(code)
    if rate is None:
        raise ValueError(f"Missing exchange rate for {code}")
    return (Decimal(str(value)) * rate).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def convert_display_amount(
    value,
    source_currency: str,
    target_currency: str,
    exchange_rates: ExchangeRates,
) -> Decimal:
    """Converts an editable amount between display currencies via PLN."""

    value_pln = convert_display_amount_to_pln(
        value,
        source_currency,
        exchange_rates,
    )
    target_rate = exchange_rates.rate_for(target_currency)
    if target_rate is None:
        raise ValueError(f"Missing exchange rate for {target_currency}")
    return (value_pln / target_rate).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
