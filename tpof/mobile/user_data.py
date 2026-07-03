"""Trwale ustawienia UI i prywatna baza produktow uzytkownika."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Mapping, MutableMapping, Optional

from tpof.core.models import Product
from tpof.labor import default_rate_config, rate_config_from_values, rate_config_to_dict


PREFERENCES_FILE = "ui_preferences.json"
CUSTOM_PRODUCTS_FILE = "custom_products.json"
ROOT_KEY = "zywnosc"
LABOR_RATES_KEY = "labor_rates"
SUPPORTED_UNIT_SYSTEMS = frozenset({"metric"})
MIN_CUSTOM_T_ZAM_C = -80.0
MAX_CUSTOM_T_ZAM_C = 10.0


def app_data_dir() -> Path:
    """Zwraca prywatny, zapisywalny katalog aplikacji."""
    if "ANDROID_ARGUMENT" in os.environ:
        base = (
            os.environ.get("ANDROID_PRIVATE")
            or os.environ.get("ANDROID_APP_PATH")
            or os.getcwd()
        )
        return Path(base)
    base = (
        os.environ.get("APPDATA")
        or os.environ.get("XDG_CONFIG_HOME")
        or str(Path.home())
    )
    return Path(base) / "RefrigerationCalc"


def _read_json(path: Path, default):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return default
    return data


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


class UiPreferences:
    """Male ustawienia interfejsu zapisywane lokalnie na urzadzeniu."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else app_data_dir() / PREFERENCES_FILE
        raw = _read_json(self.path, {})
        self._data = raw if isinstance(raw, dict) else {}

    @property
    def hints_enabled(self) -> bool:
        return bool(self._data.get("hints_enabled", True))

    def set_hints_enabled(self, enabled: bool) -> None:
        self._data["hints_enabled"] = bool(enabled)
        self._save()

    @property
    def unit_system(self) -> str:
        value = str(self._data.get("unit_system", "metric")).strip().casefold()
        return value if value in SUPPORTED_UNIT_SYSTEMS else "metric"

    def set_unit_system(self, unit_system: str) -> None:
        # TODO: Enable "imperial" after full input/output conversion is implemented.
        value = str(unit_system or "").strip().casefold()
        if value not in SUPPORTED_UNIT_SYSTEMS:
            value = "metric"
        self._data["unit_system"] = value
        self._save()

    @property
    def labor_rate_values(self) -> Dict[str, str]:
        raw = self._data.get(LABOR_RATES_KEY, {})
        if not isinstance(raw, dict):
            return rate_config_to_dict(default_rate_config())
        try:
            return rate_config_to_dict(rate_config_from_values(raw))
        except ValueError:
            return rate_config_to_dict(default_rate_config())

    def set_labor_rate_values(self, values: Mapping[str, object]) -> None:
        rates = rate_config_from_values(values)
        self._data[LABOR_RATES_KEY] = rate_config_to_dict(rates)
        self._save()

    def reset_labor_rate_values(self) -> None:
        self._data.pop(LABOR_RATES_KEY, None)
        self._save()

    @property
    def recent_products(self) -> List[tuple[str, str]]:
        """Zwraca ostatnio wybrane produkty od najnowszego."""
        result: List[tuple[str, str]] = []
        raw_items = self._data.get("recent_products", [])
        if not isinstance(raw_items, list):
            return result
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category", "")).strip()
            name = str(item.get("name", "")).strip()
            if category and name:
                result.append((category, name))
        return result

    def recent_products_for_category(
        self,
        category: str,
        available_names: Optional[List[str]] = None,
    ) -> List[str]:
        """Filtruje historię do kategorii i aktualnie dostępnej listy."""
        wanted_category = str(category or "").casefold()
        canonical = {
            name.casefold(): name for name in (available_names or []) if name
        }
        result: List[str] = []
        for stored_category, stored_name in self.recent_products:
            if stored_category.casefold() != wanted_category:
                continue
            if canonical:
                name = canonical.get(stored_name.casefold())
                if name is None:
                    continue
            else:
                name = stored_name
            if name not in result:
                result.append(name)
        return result

    def add_recent_product(
        self,
        category: str,
        name: str,
        *,
        limit: int = 24,
    ) -> None:
        """Dodaje produkt na początek historii i usuwa duplikaty."""
        category = str(category or "").strip()
        name = str(name or "").strip()
        if not category or not name:
            return
        key = (category.casefold(), name.casefold())
        recent = [
            (stored_category, stored_name)
            for stored_category, stored_name in self.recent_products
            if (stored_category.casefold(), stored_name.casefold()) != key
        ]
        recent.insert(0, (category, name))
        self._data["recent_products"] = [
            {"category": stored_category, "name": stored_name}
            for stored_category, stored_name in recent[: max(1, int(limit))]
        ]
        self._save()

    def _save(self) -> None:
        try:
            _write_json(self.path, self._data)
        except OSError:
            pass


def normalize_category(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    text = re.sub(r"\s+", "_", ascii_text.strip().lower())
    return re.sub(r"_+", "_", text).strip("_")


def _number(value, field: str, *, required: bool = False) -> Optional[float]:
    if value is None or str(value).strip() == "":
        if required:
            raise ValueError(field)
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise ValueError(field) from exc


def create_custom_product(values: Mapping[str, object]) -> Product:
    """Waliduje dane formularza i tworzy rekord zgodny z ``Product``."""
    name = str(values.get("nazwa", "")).strip()
    category = normalize_category(str(values.get("kategoria", "")))
    if not name:
        raise ValueError("nazwa")
    if not category:
        raise ValueError("kategoria")

    water = _number(values.get("wilgotnosc"), "wilgotnosc", required=True)
    c1 = _number(values.get("c1"), "c1", required=True)
    c2 = _number(values.get("c2"), "c2", required=True)
    latent = _number(values.get("l1"), "l1", required=True)
    freezing = _number(values.get("t_zam"), "t_zam", required=True)

    if water is None or not 0 <= water <= 100:
        raise ValueError("wilgotnosc")
    if c1 is None or c1 <= 0:
        raise ValueError("c1")
    if c2 is None or c2 <= 0:
        raise ValueError("c2")
    if latent is None or latent < 0:
        raise ValueError("l1")
    if (
        freezing is None
        or freezing < MIN_CUSTOM_T_ZAM_C
        or freezing > MAX_CUSTOM_T_ZAM_C
    ):
        raise ValueError("t_zam")

    optional = {}
    for key in ("bialko", "tluszcz", "weglowodany", "blonnik", "popiol"):
        number = _number(values.get(key), key)
        if number is not None and not 0 <= number <= 100:
            raise ValueError(key)
        optional[key] = number
    macro_sum = sum(number or 0.0 for number in optional.values())
    if macro_sum > 100.0:
        raise ValueError("makroskladniki")

    return Product(
        nazwa=name,
        kategoria=category,
        c1=c1,
        c2=c2,
        T_zam=freezing,
        wodaprocent=water,
        L1=latent,
        bialko=optional["bialko"],
        tluszcz=optional["tluszcz"],
        weglowodany=optional["weglowodany"],
        blonnik=optional["blonnik"],
        popiol=optional["popiol"],
    )


def product_to_json_record(product: Product) -> dict:
    return {
        "nazwa": product.nazwa,
        "wilgotnosc": product.wodaprocent,
        "bialko": product.bialko,
        "tluszcz": product.tluszcz,
        "weglowodany": product.weglowodany,
        "blonnik": product.blonnik,
        "popiol": product.popiol,
        "punkt_zamarzania": product.T_zam,
        "cieplo_wlasciwe_powyzej": product.c1,
        "cieplo_wlasciwe_ponizej": product.c2,
        "cieplo_topnienia": product.L1,
    }


def _product_from_json_record(record: Mapping[str, object], category: str) -> Product:
    return create_custom_product(
        {
            "nazwa": record.get("nazwa"),
            "kategoria": category,
            "wilgotnosc": record.get("wilgotnosc"),
            "bialko": record.get("bialko"),
            "tluszcz": record.get("tluszcz"),
            "weglowodany": record.get("weglowodany"),
            "blonnik": record.get("blonnik"),
            "popiol": record.get("popiol"),
            "t_zam": record.get("punkt_zamarzania"),
            "c1": record.get("cieplo_wlasciwe_powyzej"),
            "c2": record.get("cieplo_wlasciwe_ponizej"),
            "l1": record.get("cieplo_topnienia"),
        }
    )


class CustomProductStore:
    """Baza produktow PRO zapisywana tylko w pamieci prywatnej aplikacji."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else app_data_dir() / CUSTOM_PRODUCTS_FILE
        self._cache_mtime_ns: Optional[int] = None
        self._cache_catalog: Optional[Dict[str, List[Product]]] = None

    def _path_mtime_ns(self) -> Optional[int]:
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return None

    def _cache_copy(self, catalog: Dict[str, List[Product]]) -> Dict[str, List[Product]]:
        return {category: list(products) for category, products in catalog.items()}

    def _invalidate_cache(self) -> None:
        self._cache_mtime_ns = None
        self._cache_catalog = None

    def load_catalog(self) -> Dict[str, List[Product]]:
        current_mtime = self._path_mtime_ns()
        if self._cache_catalog is not None and self._cache_mtime_ns == current_mtime:
            return self._cache_copy(self._cache_catalog)

        raw = _read_json(self.path, {})
        root = raw.get(ROOT_KEY, {}) if isinstance(raw, dict) else {}
        if not isinstance(root, dict):
            return {}
        result: Dict[str, List[Product]] = {}
        for category, records in root.items():
            if not isinstance(category, str) or not isinstance(records, list):
                continue
            products = []
            for record in records:
                if not isinstance(record, dict):
                    continue
                try:
                    products.append(_product_from_json_record(record, category))
                except ValueError:
                    continue
            if products:
                result[normalize_category(category)] = products
        self._cache_mtime_ns = current_mtime
        self._cache_catalog = self._cache_copy(result)
        return result

    def merge_into(self, catalog: MutableMapping[str, List[Product]]) -> None:
        for category, products in self.load_catalog().items():
            destination = catalog.setdefault(category, [])
            for product in products:
                for index, existing in enumerate(destination):
                    if existing.nazwa.casefold() == product.nazwa.casefold():
                        destination[index] = product
                        break
                else:
                    destination.append(product)

    def count(self) -> int:
        return sum(len(products) for products in self.load_catalog().values())

    def contains(self, category: str, name: str) -> bool:
        normalized_category = normalize_category(category)
        wanted_name = str(name or "").casefold()
        return any(
            product.nazwa.casefold() == wanted_name
            for product in self.load_catalog().get(normalized_category, [])
        )

    def upsert(self, product: Product) -> None:
        raw = _read_json(self.path, {})
        if not isinstance(raw, dict):
            raw = {}
        root = raw.setdefault(ROOT_KEY, {})
        if not isinstance(root, dict):
            root = {}
            raw[ROOT_KEY] = root
        records = root.setdefault(product.kategoria, [])
        if not isinstance(records, list):
            records = []
            root[product.kategoria] = records

        replacement = product_to_json_record(product)
        for index, record in enumerate(records):
            if (
                isinstance(record, dict)
                and str(record.get("nazwa", "")).casefold() == product.nazwa.casefold()
            ):
                records[index] = replacement
                break
        else:
            records.append(replacement)
        _write_json(self.path, raw)
        self._invalidate_cache()
