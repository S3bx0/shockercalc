"""Shocker Calc — wersja mobilna (KivyMD).

UI w parytecie z desktopem:
  • TopAppBar z przełącznikiem Dark/Light
  • kaskadowy wybór Kategoria → Produkt
  • masa z przełącznikiem jednostek kg/t
  • paski mocy (schładzanie / zamrożenie / domrażanie) + SUMA
  • tabela właściwości produktu
  • opcjonalne zdjęcie produktu z assets/images
  • Snackbar dla błędów walidacji

Uruchomienie lokalne (desktop, do testów UI):
    python -m pip install -r requirements-mobile.txt
    python -m tpof.mobile

Build APK:
    buildozer android debug
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from tpof.core import (
    FreezingInputs,
    Product,
    calculate_freezing,
    find_product,
    list_categories,
    list_products,
    load_products,
)
from tpof.mobile.paths import DATA_PATH, FONT_PATH, IMAGES_DIR, WATERMARK_PATH

log = logging.getLogger(__name__)

STAGE_COLORS = {
    "schladzanie": (0.16, 0.50, 0.73, 1),
    "zamrozenie": (0.61, 0.35, 0.71, 1),
    "domrozenie": (0.20, 0.60, 0.86, 1),
    "total": (0.18, 0.80, 0.44, 1),
}


def _safe_image_path(nazwa: str) -> Optional[str]:
    """Zwraca ścieżkę do .webp/.png/.jpg dla produktu albo None."""
    for ext in (".webp", ".png", ".jpg", ".jpeg"):
        candidate = IMAGES_DIR / f"{nazwa}{ext}"
        if candidate.exists():
            return str(candidate)
    return None


def _pdf_output_dir() -> Path:
    """Zwraca katalog do zapisu PDF — Android Downloads albo cwd."""
    # Android: użyj public Downloads, gdy aplikacja ma uprawnienia
    if "ANDROID_ARGUMENT" in os.environ:
        for candidate in ("/sdcard/Download", "/storage/emulated/0/Download"):
            p = Path(candidate)
            if p.exists() and os.access(p, os.W_OK):
                return p
        # fallback: prywatny katalog aplikacji
        return Path(os.environ.get("ANDROID_PRIVATE", os.getcwd()))
    return Path.cwd()


def main() -> None:
    """Punkt wejścia mobilnej aplikacji."""
    try:
        from kivy.metrics import dp
        from kivy.uix.image import AsyncImage
        from kivymd.app import MDApp
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        from kivymd.uix.card import MDCard
        from kivymd.uix.gridlayout import MDGridLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.menu import MDDropdownMenu
        from kivymd.uix.progressbar import MDProgressBar
        from kivymd.uix.scrollview import MDScrollView
        from kivymd.uix.selectioncontrol import MDSwitch
        from kivymd.uix.snackbar import Snackbar
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.toolbar import MDTopAppBar
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "KivyMD nie jest zainstalowane. Uruchom:\n"
            "    python -m pip install -r requirements-mobile.txt"
        ) from exc

    catalog: Dict[str, List[Product]] = load_products(DATA_PATH)
    categories = list_categories(catalog)

    class ShockerCalcApp(MDApp):
        def build(self):
            self.title = "Shocker Calc"
            self.theme_cls.primary_palette = "Blue"
            self.theme_cls.accent_palette = "Teal"
            self.theme_cls.theme_style = "Dark"

            self._selected_category: Optional[str] = None
            self._selected_product: Optional[str] = None
            self._mass_unit: str = "kg"
            self._cat_menu: Optional[MDDropdownMenu] = None
            self._prod_menu: Optional[MDDropdownMenu] = None
            self._last_results = None

            root = MDBoxLayout(orientation="vertical")

            self.toolbar = MDTopAppBar(
                title="Shocker Calc",
                elevation=4,
                left_action_items=[["snowflake", lambda *_: None]],
                right_action_items=[["weather-night", lambda *_: self._toggle_theme()]],
            )
            root.add_widget(self.toolbar)

            scroll = MDScrollView()
            content = MDBoxLayout(
                orientation="vertical",
                padding=dp(12),
                spacing=dp(12),
                size_hint_y=None,
            )
            content.bind(minimum_height=content.setter("height"))

            content.add_widget(self._build_product_card(dp, MDCard, MDLabel, MDRaisedButton, AsyncImage))
            content.add_widget(self._build_params_card(dp, MDCard, MDBoxLayout, MDLabel, MDTextField, MDSwitch))
            content.add_widget(self._build_action_button(dp, MDBoxLayout, MDRaisedButton, MDFlatButton))
            self.results_card = self._build_results_card(
                dp, MDCard, MDBoxLayout, MDLabel, MDProgressBar, MDGridLayout
            )
            content.add_widget(self.results_card)

            scroll.add_widget(content)
            root.add_widget(scroll)
            return root

        # --- karty -------------------------------------------------------
        def _build_product_card(self, dp, MDCard, MDLabel, MDRaisedButton, AsyncImage):
            card = MDCard(
                orientation="vertical",
                padding=dp(12),
                spacing=dp(8),
                size_hint_y=None,
                height=dp(220),
                radius=[12, 12, 12, 12],
                elevation=2,
            )
            card.add_widget(MDLabel(text="Produkt", font_style="H6", size_hint_y=None, height=dp(28)))

            self.btn_category = MDRaisedButton(
                text="Wybierz kategorię",
                size_hint_x=1,
                on_release=lambda btn: self._open_category_menu(btn),
            )
            card.add_widget(self.btn_category)

            self.btn_product = MDRaisedButton(
                text="Wybierz produkt",
                size_hint_x=1,
                disabled=True,
                on_release=lambda btn: self._open_product_menu(btn),
            )
            card.add_widget(self.btn_product)

            self.product_image = AsyncImage(
                source="", size_hint_y=None, height=dp(80), allow_stretch=True, keep_ratio=True
            )
            card.add_widget(self.product_image)
            return card

        def _build_params_card(self, dp, MDCard, MDBoxLayout, MDLabel, MDTextField, MDSwitch):
            card = MDCard(
                orientation="vertical",
                padding=dp(12),
                spacing=dp(6),
                size_hint_y=None,
                height=dp(360),
                radius=[12, 12, 12, 12],
                elevation=2,
            )
            card.add_widget(MDLabel(text="Parametry", font_style="H6", size_hint_y=None, height=dp(28)))

            row_mass = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(60))
            self.in_m = MDTextField(hint_text="Masa", input_filter="float", size_hint_x=0.7)
            self.lbl_unit = MDLabel(text="kg", halign="center", size_hint_x=0.15)
            self.switch_unit = MDSwitch(active=False, size_hint_x=0.15)
            self.switch_unit.bind(active=self._on_unit_switch)
            row_mass.add_widget(self.in_m)
            row_mass.add_widget(self.lbl_unit)
            row_mass.add_widget(self.switch_unit)
            card.add_widget(row_mass)

            self.in_T1 = MDTextField(hint_text="Temperatura początkowa [°C]", input_filter="float")
            self.in_T2 = MDTextField(hint_text="Temperatura końcowa [°C]", input_filter="float")
            self.in_t = MDTextField(hint_text="Czas pracy [h]", input_filter="float")
            for w in (self.in_T1, self.in_T2, self.in_t):
                card.add_widget(w)
            return card

        def _build_action_button(self, dp, MDBoxLayout, MDRaisedButton, MDFlatButton):
            wrapper = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(8))
            wrapper.add_widget(
                MDRaisedButton(
                    text="Oblicz",
                    icon="calculator-variant",
                    size_hint_x=0.5,
                    on_release=lambda *_: self._calculate(),
                )
            )
            wrapper.add_widget(
                MDRaisedButton(
                    text="PDF",
                    icon="file-pdf-box",
                    size_hint_x=0.25,
                    on_release=lambda *_: self._export_pdf(),
                )
            )
            wrapper.add_widget(
                MDFlatButton(
                    text="Wyczyść",
                    size_hint_x=0.25,
                    on_release=lambda *_: self._reset_inputs(),
                )
            )
            return wrapper

        def _build_results_card(self, dp, MDCard, MDBoxLayout, MDLabel, MDProgressBar, MDGridLayout):
            card = MDCard(
                orientation="vertical",
                padding=dp(12),
                spacing=dp(8),
                size_hint_y=None,
                height=dp(440),
                radius=[12, 12, 12, 12],
                elevation=2,
            )
            card.add_widget(MDLabel(text="Wynik", font_style="H6", size_hint_y=None, height=dp(28)))

            self.lbl_total = MDLabel(
                text="Suma mocy: — kW",
                font_style="H5",
                halign="center",
                size_hint_y=None,
                height=dp(40),
                theme_text_color="Primary",
            )
            card.add_widget(self.lbl_total)

            self.bars: Dict[str, Dict] = {}
            for key, label in [
                ("schladzanie", "❄ Schładzanie"),
                ("zamrozenie", "🧊 Zamrożenie"),
                ("domrozenie", "⛄ Domrażanie"),
            ]:
                self.bars[key] = self._add_stage_row(card, key, label, dp, MDBoxLayout, MDLabel, MDProgressBar)

            card.add_widget(
                MDLabel(
                    text="Właściwości produktu",
                    font_style="Subtitle1",
                    size_hint_y=None,
                    height=dp(24),
                )
            )
            self.props_grid = MDGridLayout(
                cols=2,
                size_hint_y=None,
                spacing=dp(4),
                row_default_height=dp(22),
                row_force_default=True,
            )
            self.props_grid.bind(minimum_height=self.props_grid.setter("height"))
            card.add_widget(self.props_grid)
            return card

        def _add_stage_row(self, parent, key, label, dp, MDBoxLayout, MDLabel, MDProgressBar):
            row = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(54), spacing=dp(2))
            head = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(22))
            lbl_name = MDLabel(text=label, size_hint_x=0.6)
            lbl_val = MDLabel(text="—", halign="right", size_hint_x=0.4)
            head.add_widget(lbl_name)
            head.add_widget(lbl_val)
            bar = MDProgressBar(value=0, max=100, color=STAGE_COLORS[key])
            row.add_widget(head)
            row.add_widget(bar)
            parent.add_widget(row)
            return {"bar": bar, "value_label": lbl_val}

        # --- menu --------------------------------------------------------
        def _open_category_menu(self, caller):
            from kivy.metrics import dp
            from kivymd.uix.menu import MDDropdownMenu

            items = [
                {
                    "text": cat,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda c=cat: self._pick_category(c),
                }
                for cat in categories
            ]
            self._cat_menu = MDDropdownMenu(caller=caller, items=items, width_mult=4, max_height=dp(360))
            self._cat_menu.open()

        def _pick_category(self, category: str):
            self._selected_category = category
            self._selected_product = None
            self.btn_category.text = category
            self.btn_product.text = "Wybierz produkt"
            self.btn_product.disabled = False
            self.product_image.source = ""
            if self._cat_menu:
                self._cat_menu.dismiss()

        def _open_product_menu(self, caller):
            from kivy.metrics import dp
            from kivymd.uix.menu import MDDropdownMenu

            if not self._selected_category:
                return
            items = [
                {
                    "text": name,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda n=name: self._pick_product(n),
                }
                for name in list_products(catalog, self._selected_category)
            ]
            self._prod_menu = MDDropdownMenu(caller=caller, items=items, width_mult=4, max_height=dp(360))
            self._prod_menu.open()

        def _pick_product(self, name: str):
            self._selected_product = name
            self.btn_product.text = name
            img = _safe_image_path(name)
            self.product_image.source = img or ""
            if self._prod_menu:
                self._prod_menu.dismiss()

        # --- akcje -------------------------------------------------------
        def _on_unit_switch(self, _switch, active: bool):
            self._mass_unit = "t" if active else "kg"
            self.lbl_unit.text = self._mass_unit

        def _toggle_theme(self):
            is_dark = self.theme_cls.theme_style == "Dark"
            self.theme_cls.theme_style = "Light" if is_dark else "Dark"
            self.toolbar.right_action_items = [
                [
                    "weather-sunny" if not is_dark else "weather-night",
                    lambda *_: self._toggle_theme(),
                ]
            ]

        def _reset_inputs(self):
            for field_ in (self.in_m, self.in_T1, self.in_T2, self.in_t):
                field_.text = ""
            self.lbl_total.text = "Suma mocy: — kW"
            for entry in self.bars.values():
                entry["bar"].value = 0
                entry["value_label"].text = "—"
            self.props_grid.clear_widgets()
            self._last_results = None

        def _export_pdf(self):
            if self._last_results is None:
                self._show_error("Najpierw wykonaj obliczenia.")
                return
            try:
                try:
                    from tpof.core.pdf_report import build_pdf, save_pdf
                except ImportError:
                    self._show_error(
                        "Eksport PDF niedostępny w wersji mobilnej. Użyj wersji desktopowej."
                    )
                    return

                img_path = _safe_image_path(self._last_results.produkt.nazwa)
                pdf_bytes = build_pdf(
                    self._last_results,
                    font_path=FONT_PATH,
                    product_image_path=Path(img_path) if img_path else None,
                    watermark_image_path=WATERMARK_PATH if WATERMARK_PATH.exists() else None,
                )
                out_dir = _pdf_output_dir()
                out_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                nazwa = self._last_results.produkt.nazwa.replace(" ", "_")
                out_path = out_dir / f"ShockerCalc_{nazwa}_{ts}.pdf"
                save_pdf(pdf_bytes, out_path)
                self._show_error(f"Zapisano: {out_path}")
            except Exception as exc:  # pragma: no cover - UI feedback
                log.exception("Eksport PDF")
                self._show_error(f"Błąd PDF: {exc}")

        def _show_error(self, message: str):
            from kivymd.uix.snackbar import Snackbar

            try:
                Snackbar(text=message, duration=3).open()
            except Exception:  # pragma: no cover
                log.warning("Snackbar fail: %s", message)

        def _parse_float(self, raw: str, name: str) -> float:
            try:
                return float((raw or "").replace(",", "."))
            except (TypeError, ValueError, AttributeError) as exc:
                raise ValueError(f"Nieprawidłowa wartość pola: {name}") from exc

        def _calculate(self):
            try:
                if not self._selected_category or not self._selected_product:
                    self._show_error("Wybierz kategorię i produkt.")
                    return
                product = find_product(catalog, self._selected_category, self._selected_product)
                if product is None:
                    self._show_error("Nie znaleziono produktu w bazie.")
                    return

                masa = self._parse_float(self.in_m.text, "masa")
                if self._mass_unit == "t":
                    masa *= 1000.0
                T1 = self._parse_float(self.in_T1.text, "T pocz")
                T2 = self._parse_float(self.in_T2.text, "T konc")
                czas = self._parse_float(self.in_t.text, "czas")

                inputs = FreezingInputs(masa_kg=masa, T_pocz_C=T1, T_konc_C=T2, czas_h=czas)
                results = calculate_freezing(inputs, product)
                self._last_results = results
                self._render_results(results)
            except ValueError as exc:
                self._show_error(str(exc))
            except Exception as exc:  # pragma: no cover
                log.exception("Błąd obliczeń")
                self._show_error(f"Błąd: {exc}")

        def _render_results(self, results):
            total = results.P_total_kW or 0.0
            self.lbl_total.text = f"Suma mocy: {total:.2f} kW"

            stages = {
                "schladzanie": results.P_schladzanie_kW,
                "zamrozenie": results.P_zamrozenie_kW,
                "domrozenie": results.P_domrozenie_kW,
            }
            for key, value in stages.items():
                pct = (value / total * 100.0) if total > 0 else 0.0
                self.bars[key]["bar"].value = pct
                self.bars[key]["value_label"].text = f"{value:.2f} kW ({pct:.0f}%)"

            from kivymd.uix.label import MDLabel

            self.props_grid.clear_widgets()
            p = results.produkt
            warn = "  (szacowane)" if results.T_zam_szacunkowy else ""
            rows = [
                ("Kategoria:", p.kategoria or "—"),
                ("c₁ [kJ/kg·K]:", f"{p.c1:.2f}" if p.c1 is not None else "—"),
                ("c₂ [kJ/kg·K]:", f"{p.c2:.2f}" if p.c2 is not None else "—"),
                ("L₁ [kJ/kg]:", f"{p.L1:.0f}" if p.L1 is not None else "—"),
                ("Woda [%]:", f"{p.wodaprocent:.1f}" if p.wodaprocent is not None else "—"),
                ("T_zam [°C]:", f"{results.T_zam_uzyte_C:.2f}{warn}"),
            ]
            for label, value in rows:
                self.props_grid.add_widget(MDLabel(text=label, theme_text_color="Secondary"))
                self.props_grid.add_widget(MDLabel(text=value))

    ShockerCalcApp().run()


if __name__ == "__main__":
    main()
