"""Formatowanie wyników do tekstu — używane przez UI i generator PDF."""

from __future__ import annotations

from .models import FreezingResults


def _fmt(value, suffix: str = "", precision: int = 2) -> str:
    if value is None:
        return "brak danych"
    return f"{float(value):.{precision}f}{suffix}"


def format_results_text(
    results: FreezingResults, *, include_product_properties: bool = True
) -> str:
    """Zwraca wieloliniowy raport tekstowy gotowy do pokazania w UI."""
    p = results.produkt
    i = results.inputs

    T_zam_warning = (
        " (szacunkowo — brak danych katalogowych)"
        if results.T_zam_szacunkowy
        else ""
    )

    lines = [
        "--- Wyniki obliczeń ---",
        f"Nazwa produktu: {p.nazwa}",
        f"Masa [kg]: {i.masa_kg:.2f}",
    ]
    if include_product_properties:
        lines.extend(
            [
                f"Ciepło właściwe powyżej zamrażania [kJ/kg·K]: {_fmt(p.c1)}",
                f"Ciepło właściwe poniżej zamrażania [kJ/kg·K]: {_fmt(p.c2)}",
                f"Zawartość wody [%]: {_fmt(p.wodaprocent)}",
                f"Ciepło topnienia [kJ/kg]: {_fmt(p.L1)}",
            ]
        )
    lines.extend(
        [
            f"Temperatura początkowa [°C]: {i.T_pocz_C:.2f}",
            f"Temperatura końcowa [°C]: {i.T_konc_C:.2f}",
        ]
    )
    if include_product_properties:
        lines.append(
            f"Temperatura początkowego zamarzania [°C]: {results.T_zam_uzyte_C:.2f}{T_zam_warning}"
        )
    lines.extend(
        [
            f"Czas pracy [h]: {i.czas_h:.2f}",
            f"Moc potrzebna do schłodzenia [kW]: {results.P_schladzanie_kW:.2f}",
            f"Moc potrzebna do zamrożenia [kW]: {results.P_zamrozenie_kW:.2f}",
            f"Moc potrzebna do domrożenia [kW]: {results.P_domrozenie_kW:.2f}",
            f"Suma mocy potrzebnej [kW]: {results.P_total_kW:.2f}",
        ]
    )
    return "\n".join(lines) + "\n"
