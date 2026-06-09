"""Obliczenia zaworów dekompresyjnych — czysta logika domenowa.

Port logiki z desktopowej aplikacji (repo: zawory-dekompresyjne).
Bez zależności od bibliotek UI — zwraca dataclass `ValveResults`.

Model fizyczny:
    Przy gwałtownym schłodzeniu powietrza w komorze (np. po zamknięciu drzwi
    mroźni) ciśnienie spada. Zawory dekompresyjne wyrównują różnicę ciśnień,
    aby uniknąć uszkodzenia konstrukcji. Liczba zaworów zależy od objętości
    komory, dynamiki zmian temperatury i wydajności pojedynczego zaworu.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Stała przepływu (empiryczna) [l/(min·m³·(°C/min))].
K: float = 3.66

# Wydajności dostępnych typów zaworów [l/min].
ZAWORY: dict[str, int] = {
    "Maxi Elebar": 4300,
    "Maxi Elebar EVO-VERTICAL": 1430,
}

# Limity sanity-check, by chronić przed absurdalnymi danymi wejściowymi.
V_MAX: float = 1_000_000.0      # maksymalna objętość komory [m³]
F_MAX: float = 10_000_000.0     # maksymalna częstość/współczynnik [1/h]
TEMP_MIN: float = -200.0        # dolny limit temperatury [°C]
TEMP_MAX: float = 200.0         # górny limit temperatury [°C]


@dataclass(frozen=True)
class ValveResults:
    """Wynik obliczeń zaworów dekompresyjnych.

    Pola:
        delta_T: tempo zmiany temperatury [°C/min].
        Q: wymagany przepływ powietrza [l/min].
        ilosc_zaworow: minimalna liczba zaworów (zaokrąglona w górę).
        przeplyw_zaworu: wydajność pojedynczego zaworu [l/min].
        typ_zaworu: nazwa wybranego typu zaworu.
    """

    delta_T: float
    Q: float
    ilosc_zaworow: int
    przeplyw_zaworu: int
    typ_zaworu: str = ""


def calculate_decompression_valves(
    V: float,
    temp_przed: float,
    temp_za: float,
    F: float,
    typ_zaworu: str = "Maxi Elebar",
) -> ValveResults:
    """Oblicza liczbę zaworów dekompresyjnych dla podanej komory.

    Args:
        V: objętość komory [m³] (> 0, <= V_MAX).
        temp_przed: temperatura przed dekompresją [°C].
        temp_za: temperatura po dekompresji [°C] (musi być < temp_przed).
        F: współczynnik częstości zmian [1/h] (> 0, <= F_MAX).
        typ_zaworu: nazwa typu zaworu (klucz w ZAWORY).

    Returns:
        ValveResults z tempem zmian, wymaganym przepływem i liczbą zaworów.

    Raises:
        ValueError: gdy dane wejściowe są niefinitne lub poza zakresem,
            temperatury są równe lub temp_przed <= temp_za.
        KeyError: gdy `typ_zaworu` nie istnieje w słowniku ZAWORY.
    """
    # Sprawdzenie skończoności (odrzuca NaN/inf).
    for nazwa, wartosc in (("V", V), ("temp_przed", temp_przed),
                           ("temp_za", temp_za), ("F", F)):
        if not math.isfinite(wartosc):
            raise ValueError(f"Wartość '{nazwa}' musi być liczbą skończoną.")

    if V <= 0:
        raise ValueError("Objętość komory V musi być > 0.")
    if V > V_MAX:
        raise ValueError(f"Objętość komory V nie może przekraczać {V_MAX:g} m³.")
    if F <= 0:
        raise ValueError("Współczynnik F musi być > 0.")
    if F > F_MAX:
        raise ValueError(f"Współczynnik F nie może przekraczać {F_MAX:g}.")

    for nazwa, temp in (("temp_przed", temp_przed), ("temp_za", temp_za)):
        if not (TEMP_MIN <= temp <= TEMP_MAX):
            raise ValueError(
                f"Temperatura '{nazwa}' musi być w zakresie "
                f"{TEMP_MIN:g}…{TEMP_MAX:g} °C."
            )

    if temp_przed == temp_za:
        raise ValueError("Temperatury przed i po dekompresji nie mogą być równe.")
    if temp_przed <= temp_za:
        raise ValueError(
            "Temperatura przed dekompresją musi być wyższa niż po dekompresji."
        )

    # KeyError, gdy nieznany typ zaworu (zgodne z konwencją źródła).
    przeplyw_zaworu = ZAWORY[typ_zaworu]

    # Bez pośrednich zaokrągleń — zachowujemy margines bezpieczeństwa.
    DT1 = temp_przed - temp_za
    delta_T = (F / V * DT1) / 60.0
    Q = K * V * delta_T
    ilosc_zaworow = math.ceil(Q / przeplyw_zaworu)

    return ValveResults(
        delta_T=delta_T,
        Q=Q,
        ilosc_zaworow=ilosc_zaworow,
        przeplyw_zaworu=przeplyw_zaworu,
        typ_zaworu=typ_zaworu,
    )
