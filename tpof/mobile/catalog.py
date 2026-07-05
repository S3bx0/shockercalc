"""Mobile-only catalog helpers.

This module stays independent from ``tpof.mobile.main`` so catalog behavior can
be tested without importing the Kivy application.
"""
from __future__ import annotations

import unicodedata
from collections.abc import Callable

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
    categories: list[str], display_name: Callable[[str], str] | None = None
) -> tuple[list[str], list[str]]:
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


def _mobile_product_names(catalog: dict[str, list[Product]], category: str) -> list[str]:
    return [
        name
        for name in list_products(catalog, category)
        if not _is_mobile_hidden_product(category, name)
    ]


def _safe_image_path(nazwa: str) -> str | None:
    """Zwraca ścieżkę do .webp/.png/.jpg dla produktu albo None."""
    for ext in (".webp", ".png", ".jpg", ".jpeg"):
        candidate = IMAGES_DIR / f"{nazwa}{ext}"
        if candidate.exists():
            return str(candidate)
    return None


def _search_key(value: str) -> str:
    """Normalizuje tekst do wyszukiwania bez wielkości liter i akcentów."""
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return text.replace("ł", "l")


def _search_product_names(names: list[str], query: str) -> list[str]:
    """Filtruje produkty, preferując początek nazwy i początek słowa."""
    normalized_query = _search_key(query).strip()
    if not normalized_query:
        return list(names)
    tokens = normalized_query.split()
    matches = []
    for index, name in enumerate(names):
        normalized_name = _search_key(name)
        if not all(token in normalized_name for token in tokens):
            continue
        words = normalized_name.split()
        if normalized_name.startswith(normalized_query):
            rank = 0
        elif any(word.startswith(tokens[0]) for word in words):
            rank = 1
        else:
            rank = 2
        matches.append((rank, index, name))
    return [name for _rank, _index, name in sorted(matches)]


__all__ = [
    "FEATURED_MOBILE_CATEGORIES",
    "_is_mobile_hidden_product",
    "_mobile_product_names",
    "_mobile_sort_key",
    "_ordered_mobile_categories",
    "_safe_image_path",
    "_search_key",
    "_search_product_names",
]
