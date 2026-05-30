"""Modele danych domenowych jako dataclasses.

Wszystkie pola są typowane — używane zarówno przez warstwę logiki,
jak i UI (desktop/mobile) do bezpiecznej wymiany danych.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Product:
    """Surowy rekord produktu wczytany z bazy (Table3.json).

    Pola opcjonalne odpowiadają sytuacji, gdy w źródle jest `null` lub brak klucza.
    """

    nazwa: str
    kategoria: str = ""
    c1: Optional[float] = None  # ciepło właściwe powyżej zamrażania [kJ/(kg·K)]
    c2: Optional[float] = None  # ciepło właściwe poniżej zamrażania [kJ/(kg·K)]
    T_zam: Optional[float] = None  # punkt zamarzania [°C]
    wodaprocent: Optional[float] = None  # zawartość wody [%]
    L1: Optional[float] = None  # ciepło topnienia (utajone) [kJ/kg]
    bialko: Optional[float] = None
    tluszcz: Optional[float] = None
    weglowodany: Optional[float] = None
    blonnik: Optional[float] = None
    popiol: Optional[float] = None

    @classmethod
    def from_dict(cls, raw: dict, kategoria: str = "") -> "Product":
        """Tworzy Product ze słownika w formacie używanym w Table3.json."""

        def _num(value):
            if value is None or value == "null" or value == "":
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        return cls(
            nazwa=raw.get("nazwa", "Nieznany produkt"),
            kategoria=kategoria,
            c1=_num(raw.get("ciepło_właściwe_powyżej")),
            c2=_num(raw.get("ciepło_właściwe_poniżej")),
            T_zam=_num(raw.get("punkt_zamarzania")),
            wodaprocent=_num(raw.get("wilgotność")),
            L1=_num(raw.get("ciepło_topnienia")),
            bialko=_num(raw.get("białko")),
            tluszcz=_num(raw.get("tłuszcz")),
            weglowodany=_num(raw.get("węglowodany")),
            blonnik=_num(raw.get("błonnik")),
            popiol=_num(raw.get("popiół")),
        )


@dataclass(frozen=True)
class FreezingInputs:
    """Walidowane dane wejściowe procesu zamrażania."""

    masa_kg: float
    T_pocz_C: float
    T_konc_C: float
    czas_h: float


@dataclass(frozen=True)
class FreezingResults:
    """Wynik obliczeń: energie [kJ] i moce [kW] dla trzech etapów procesu."""

    produkt: Product
    inputs: FreezingInputs
    T_zam_uzyte_C: float
    T_zam_szacunkowy: bool = False  # True, gdy w danych brak punktu zamarzania
    Q_schladzanie_kJ: float = 0.0
    Q_zamrozenie_kJ: float = 0.0
    Q_domrozenie_kJ: float = 0.0
    P_schladzanie_kW: float = 0.0
    P_zamrozenie_kW: float = 0.0
    P_domrozenie_kW: float = 0.0

    @property
    def Q_total_kJ(self) -> float:
        return self.Q_schladzanie_kJ + self.Q_zamrozenie_kJ + self.Q_domrozenie_kJ

    @property
    def P_total_kW(self) -> float:
        return self.P_schladzanie_kW + self.P_zamrozenie_kW + self.P_domrozenie_kW
