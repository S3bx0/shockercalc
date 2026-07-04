"""Mobile-only catalog helpers.

This module stays independent from ``tpof.mobile.main`` so catalog behavior can
be tested without importing the Kivy application.
"""
from __future__ import annotations

import unicodedata
from typing import Callable, Dict, List, Optional

from tpof.core import Product, list_products
from tpof.mobile.paths import IMAGES_DIR

FEATURED_MOBILE_CATEGORIES = ("owoce", "warzywa")
_POLISH_SORT_TRANSLATION = str.maketrans({"ł": "l", "Ł": "L"})


def _mobile_sort_key(value: str) -> str:
    """Zwraca stabilny klucz sortowania nazw polskich i angielskich."""
    normalized = unicodedata.normalize(
        "NFKD", value.translate(_POLISH_SORT_TRANSLATION)
    )
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def _ordered_mobile_categories(
    categories: List[str], display_name: Optional[Callable[[str], str]] = None
) -> tuple[List[str], List[str]]:
    """Umieszcza owoce i warzywa na początku, resztę sortuje alfabetycznie."""
    display_name = display_name or (lambda category: category.replace("_", " "))
    available = list(dict.fromkeys(categories))
    featured = [
        category for category in FEATURED_MOBILE_CATEGORIES if category in available
    ]
    remaining = sorted(
        (category for category in available if category not in featured),
        key=lambda category: _mobile_sort_key(display_name(category)),
    )
    return featured, remaining


def _is_mobile_hidden_product(category: str, product_name: str) -> bool:
    """Ukrywa techniczne rekordy CTP wyłącznie w mobilnym selektorze."""
    return category.casefold() == "różne" and product_name.casefold().endswith(
        "_ctp aldi"
    )


def _mobile_product_names(catalog: Dict[str, List[Product]], category: str) -> List[str]:
    return [
        name
        for name in list_products(catalog, category)
        if not _is_mobile_hidden_product(category, name)
    ]


def _safe_image_path(nazwa: str) -> Optional[str]:
    """Zwraca ścieżkę do .webp/.png/.jpg dla produktu albo None."""
    for ext in (".webp", ".png", ".jpg", ".jpeg"):
        candidate = IMAGES_DIR / f"{nazwa}{ext}"
        if candidate.exists():
            return str(candidate)
    return None


__all__ = [
    "FEATURED_MOBILE_CATEGORIES",
    "_is_mobile_hidden_product",
    "_mobile_product_names",
    "_mobile_sort_key",
    "_ordered_mobile_categories",
    "_safe_image_path",
]
