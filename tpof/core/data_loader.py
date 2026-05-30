"""Ładowanie bazy produktów z Table3.json (lub innego pliku JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

from .models import Product

METADATA_KEY = "metadata"
ROOT_KEY = "żywność"


def load_products(json_path: Union[str, Path]) -> Dict[str, List[Product]]:
    """Wczytuje bazę produktów do słownika {kategoria: [Product, ...]}."""
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    root = raw.get(ROOT_KEY, {})
    result: Dict[str, List[Product]] = {}
    for category, items in root.items():
        if category == METADATA_KEY or not isinstance(items, list):
            continue
        result[category] = [Product.from_dict(item, kategoria=category) for item in items]
    return result


def list_categories(catalog: Dict[str, List[Product]]) -> List[str]:
    return sorted(catalog.keys())


def list_products(catalog: Dict[str, List[Product]], category: str) -> List[str]:
    return [p.nazwa for p in catalog.get(category, [])]


def find_product(
    catalog: Dict[str, List[Product]], category: str, name: str
) -> Optional[Product]:
    for product in catalog.get(category, []):
        if product.nazwa == name:
            return product
    return None
