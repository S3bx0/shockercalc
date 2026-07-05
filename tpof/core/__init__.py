"""Czysta logika domenowa — bez zależności od bibliotek UI."""

from .calculations import calculate_freezing
from .data_loader import find_product, list_categories, list_products, load_products
from .formatters import format_results_text
from .models import FreezingInputs, FreezingResults, Product
from .validators import (
    MAX_TEMPERATURE_C,
    MIN_TEMPERATURE_C,
    is_positive_number,
    is_valid_temperature,
    parse_number,
)
from .valves import (
    F_MAX,
    TEMP_MAX,
    TEMP_MIN,
    V_MAX,
    ZAWORY,
    K,
    ValveResults,
    calculate_decompression_valves,
)

__all__ = [
    "Product",
    "FreezingInputs",
    "FreezingResults",
    "is_positive_number",
    "is_valid_temperature",
    "parse_number",
    "MIN_TEMPERATURE_C",
    "MAX_TEMPERATURE_C",
    "calculate_freezing",
    "load_products",
    "find_product",
    "list_categories",
    "list_products",
    "format_results_text",
    "ValveResults",
    "calculate_decompression_valves",
    "ZAWORY",
    "K",
    "V_MAX",
    "F_MAX",
    "TEMP_MIN",
    "TEMP_MAX",
]
