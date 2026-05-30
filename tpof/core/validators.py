"""Walidatory wejściowe — czyste funkcje bez efektów ubocznych.

UWAGA: ta warstwa NIE wyświetla okienek dialogowych. Zwraca True/False
lub rzuca wyjątkiem. Warstwa UI (Tk/Kivy) sama decyduje, jak pokazać błąd.
"""

from __future__ import annotations

from typing import Optional, Union

Number = Union[int, float, str]

# Akceptowalny zakres temperatur procesowych dla produktów spożywczych [°C]
MIN_TEMPERATURE_C: float = -273.15
MAX_TEMPERATURE_C: float = 200.0


def parse_number(value: Number) -> Optional[float]:
    """Parsuje liczbę, akceptując przecinek dziesiętny.

    Zwraca None gdy wartość nie jest liczbą.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def is_positive_number(value: Number) -> bool:
    """True jeżeli wartość jest liczbą > 0."""
    n = parse_number(value)
    return n is not None and n > 0


def is_valid_temperature(value: Number) -> bool:
    """True jeżeli wartość mieści się w zakresie procesowym."""
    n = parse_number(value)
    return n is not None and MIN_TEMPERATURE_C <= n <= MAX_TEMPERATURE_C
