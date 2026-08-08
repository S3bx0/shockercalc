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
_MOBILE_ASCII_IMAGES_DIR = IMAGES_DIR / "mobile_ascii"


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
    """Zwraca ścieżkę obrazu, z bezpiecznym aliasem ASCII na Androidzie.

    Część wersji Androida/Kivy nie otwiera poprawnie plików z polskimi znakami
    po rozpakowaniu ``private.tar``. Najpierw zachowujemy zgodność z pełną nazwą
    katalogową, a następnie próbujemy stabilnego aliasu bez znaków diakrytycznych.
    """

    normalized = unicodedata.normalize(
        "NFKD", str(nazwa or "").translate(_POLISH_SORT_TRANSLATION)
    )
    ascii_name = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    locations = ((_MOBILE_ASCII_IMAGES_DIR, ascii_name), (IMAGES_DIR, nazwa))
    for directory, stem in locations:
        for ext in (".webp", ".png", ".jpg", ".jpeg"):
            candidate = directory / f"{stem}{ext}"
            if candidate.exists():
                return str(candidate)
    return None


def _search_key(value: str) -> str:
    """Normalizuje tekst do wyszukiwania bez wielkości liter i akcentów."""
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return text.replace("ł", "l")


def _search_product_names(
    names: list[str],
    query: str,
    display_name: Callable[[str], str] | None = None,
) -> list[str]:
    """Filtruje produkty po nazwie kanonicznej i aktualnej etykiecie UI."""

    display_name = display_name or (lambda name: name)
    normalized_query = _search_key(query).strip()
    if not normalized_query:
        return list(names)
    tokens = normalized_query.split()
    matches = []
    for index, name in enumerate(names):
        search_names = tuple(
            dict.fromkeys((_search_key(display_name(name)), _search_key(name)))
        )
        matching_names = [
            candidate
            for candidate in search_names
            if all(token in candidate for token in tokens)
        ]
        if not matching_names:
            continue
        rank = min(
            0
            if candidate.startswith(normalized_query)
            else (
                1
                if any(word.startswith(tokens[0]) for word in candidate.split())
                else 2
            )
            for candidate in matching_names
        )
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
