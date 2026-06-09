"""Czysta logika domenowa — bez zależności od bibliotek UI."""

from .models import Product, FreezingInputs, FreezingResults
from .validators import (
    is_positive_number,
    is_valid_temperature,
    parse_number,
    MIN_TEMPERATURE_C,
    MAX_TEMPERATURE_C,
)
from .calculations import calculate_freezing
from .data_loader import load_products, find_product, list_categories, list_products
from .formatters import format_results_text
from .valves import (
    ValveResults,
    calculate_decompression_valves,
    ZAWORY,
    K,
    V_MAX,
    F_MAX,
    TEMP_MIN,
    TEMP_MAX,
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
