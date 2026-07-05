"""Główne obliczenia termodynamiczne procesu zamrażania.

Wynik to dataclass `FreezingResults` — UI sam decyduje jak go wyświetlić.
"""

from __future__ import annotations

import logging

from .models import FreezingInputs, FreezingResults, Product

log = logging.getLogger(__name__)

SECONDS_IN_HOUR: int = 3600


def _estimate_T_zam(woda_procent: float | None) -> float:
    """Szacuje punkt zamarzania produktu na podstawie zawartości wody [%].

    Empiryczne przybliżenie inżynierskie: T_zam ≈ -0.6 · (100 / woda%)
    daje wartości w zakresie ~-0.6 °C (woda czysta) do ~-6 °C (10% wody).
    Wzór jest zgrubny — używany tylko gdy brak danych w bazie.
    """
    if woda_procent is None or woda_procent <= 0:
        return -0.6  # domyślnie ~woda
    # Proste, monotonicznie malejące przybliżenie:
    # 100% wody -> -0.6°C, 50% -> -1.2°C, 10% -> -6°C
    return round(-0.6 * (100.0 / woda_procent), 2)


def _power_kW(Q_kJ: float, t_h: float) -> float:
    """Zamienia energię [kJ] w czasie [h] na moc [kW]."""
    if not t_h or t_h <= 0:
        return 0.0
    return Q_kJ / (t_h * SECONDS_IN_HOUR)


def calculate_freezing(inputs: FreezingInputs, product: Product) -> FreezingResults:
    """Zwraca pełen bilans cieplny i wymagane moce dla podanego produktu.

    Logika obejmuje trzy etapy:
      1. schładzanie ponad punktem zamarzania (c1),
      2. zamrażanie (ciepło utajone L1),
      3. domrażanie poniżej punktu zamarzania (c2).

    Raises:
        ValueError: gdy `inputs.czas_h <= 0` (moc nieobliczalna).
    """
    if inputs.czas_h <= 0:
        raise ValueError(
            f"Czas pracy musi być > 0 h (otrzymano: {inputs.czas_h}). "
            "Bez czasu nie można policzyć mocy chłodniczej."
        )

    m = inputs.masa_kg
    T_pocz = inputs.T_pocz_C
    T_konc = inputs.T_konc_C
    t = inputs.czas_h
    if T_konc >= T_pocz:
        raise ValueError(
            "Temperatura końcowa musi być niższa od temperatury początkowej "
            f"(otrzymano: {T_pocz:.2f}°C -> {T_konc:.2f}°C). "
            "Dla ogrzewania lub braku zmiany temperatury kalkulator chłodniczy "
            "nie wyznacza poprawnego zapotrzebowania mocy."
        )

    T_zam: float | None = product.T_zam
    T_zam_szacunkowy = T_zam is None
    if T_zam is None:
        T_zam = _estimate_T_zam(product.wodaprocent)

    c1 = product.c1
    c2 = product.c2
    L1 = product.L1

    Q_schladzanie = 0.0
    Q_zamrozenie = 0.0
    Q_domrozenie = 0.0

    if T_pocz > T_zam:
        if T_konc > T_zam:
            # Cały proces powyżej punktu zamarzania — tylko schładzanie c1.
            if c1:
                Q_schladzanie = m * c1 * (T_pocz - T_konc)
        else:
            # Schładzanie do punktu zamarzania.
            if c1:
                Q_schladzanie = m * c1 * (T_pocz - T_zam)
            # Zamrożenie — ciepło utajone.
            if L1:
                Q_zamrozenie = m * L1
            # Domrożenie poniżej punktu zamarzania.
            if c2:
                Q_domrozenie = m * c2 * (T_zam - T_konc)
    else:
        # Produkt już zamrożony — tylko domrażanie (jeśli T_konc niższa).
        if T_konc < T_pocz and c2:
            Q_domrozenie = m * c2 * (T_pocz - T_konc)

    P_schladzanie = _power_kW(Q_schladzanie, t)
    P_zamrozenie = _power_kW(Q_zamrozenie, t)
    P_domrozenie = _power_kW(Q_domrozenie, t)

    log.debug(
        "Produkt=%s m=%.2fkg T:%.2f->%.2f T_zam=%.2f t=%.2fh -> P_total=%.2fkW",
        product.nazwa, m, T_pocz, T_konc, T_zam, t,
        P_schladzanie + P_zamrozenie + P_domrozenie,
    )

    return FreezingResults(
        produkt=product,
        inputs=inputs,
        T_zam_uzyte_C=float(T_zam),
        T_zam_szacunkowy=T_zam_szacunkowy,
        Q_schladzanie_kJ=Q_schladzanie,
        Q_zamrozenie_kJ=Q_zamrozenie,
        Q_domrozenie_kJ=Q_domrozenie,
        P_schladzanie_kW=P_schladzanie,
        P_zamrozenie_kW=P_zamrozenie,
        P_domrozenie_kW=P_domrozenie,
    )
