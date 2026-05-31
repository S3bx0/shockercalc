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
    "schladzanie": (0.10, 0.48, 0.71, 1),
    "zamrozenie": (0.42, 0.37, 0.86, 1),
    "domrozenie": (0.00, 0.67, 0.74, 1),
    "total": (0.05, 0.62, 0.42, 1),
}

ADMOB_APP_ID = "ca-app-pub-7481054652344026~2716191071"
ADMOB_BANNER_AD_UNIT_ID = "ca-app-pub-7481054652344026/5599859341"
ADMOB_TEST_BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/9214589741"

IS_ANDROID = "ANDROID_ARGUMENT" in os.environ
CARD_BG_DARK = (0.09, 0.13, 0.17, 1)
CARD_BG_LIGHT = (0.96, 0.98, 1.0, 1)
SURFACE_DARK = (0.05, 0.08, 0.11, 1)
SURFACE_LIGHT = (0.93, 0.96, 0.98, 1)


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
        from kivy.core.window import Window
        from kivy.metrics import dp
        from kivy.uix.image import AsyncImage
        from kivymd.app import MDApp
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDRaisedButton
        from kivymd.uix.card import MDCard
        from kivymd.uix.gridlayout import MDGridLayout
        from kivymd.uix.label import MDIcon, MDLabel
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

    # Rejestracja fontu DejaVuSans (pełen Unicode — subscripty, symbole)
    # — działa zarówno na desktopie jak i na Androidzie (font jest w assets/).
    try:
        from kivy.core.text import LabelBase

        if FONT_PATH.exists():
            LabelBase.register(name="DejaVuSans", fn_regular=str(FONT_PATH))
            log.info("Zarejestrowano font DejaVuSans z %s", FONT_PATH)
    except Exception:  # pragma: no cover
        log.exception("Nie udało się zarejestrować fontu DejaVuSans")

    catalog: Dict[str, List[Product]] = load_products(DATA_PATH)
    categories = list_categories(catalog)

    class ShockerCalcApp(MDApp):
        def build(self):
            self.title = "Shocker Calc"
            self.theme_cls.primary_palette = "Blue"
            self.theme_cls.primary_hue = "600"
            self.theme_cls.accent_palette = "Cyan"
            self.theme_cls.theme_style = "Dark"
            try:
                self.theme_cls.material_style = "M3"
            except Exception:  # pragma: no cover - starsze KivyMD
                pass
            Window.clearcolor = SURFACE_DARK

            self._selected_category: Optional[str] = None
            self._selected_product: Optional[str] = None
            self._mass_unit: str = "kg"
            self._cat_menu: Optional[MDDropdownMenu] = None
            self._prod_menu: Optional[MDDropdownMenu] = None
            self._last_results = None
            self._themed_cards = []

            self.root_layout = MDBoxLayout(orientation="vertical", md_bg_color=SURFACE_DARK)
            root = self.root_layout

            self.toolbar = MDTopAppBar(
                title="Shocker Calc",
                elevation=3,
                left_action_items=[["snowflake", lambda *_: None]],
                right_action_items=[["weather-night", lambda *_: self._toggle_theme()]],
            )
            root.add_widget(self.toolbar)

            self.scroll = MDScrollView()
            content = MDBoxLayout(
                orientation="vertical",
                padding=[dp(16), dp(14), dp(16), dp(18)],
                spacing=dp(14),
                size_hint_y=None,
            )
            content.bind(minimum_height=content.setter("height"))

            content.add_widget(
                self._build_product_card(dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDRaisedButton, AsyncImage)
            )
            content.add_widget(self._build_params_card(dp, MDCard, MDBoxLayout, MDLabel, MDTextField, MDSwitch))
            content.add_widget(self._build_action_button(dp, MDBoxLayout, MDRaisedButton))
            self.results_card = self._build_results_card(
                dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDProgressBar, MDGridLayout
            )
            content.add_widget(self.results_card)

            self.scroll.add_widget(content)
            root.add_widget(self.scroll)
            root.add_widget(self._build_footer(dp, MDBoxLayout, MDLabel))
            root.add_widget(self._build_ad_slot(dp, MDBoxLayout, MDIcon, MDLabel))
            return root

        # --- karty -------------------------------------------------------
        def _card_bg(self):
            return CARD_BG_DARK if self.theme_cls.theme_style == "Dark" else CARD_BG_LIGHT

        def _surface_bg(self):
            return SURFACE_DARK if self.theme_cls.theme_style == "Dark" else SURFACE_LIGHT

        def _sync_theme_surfaces(self):
            surface = self._surface_bg()
            Window.clearcolor = surface
            self.root_layout.md_bg_color = surface
            for card in self._themed_cards:
                card.md_bg_color = self._card_bg()
            ad_slot = getattr(self, "ad_slot", None)
            if ad_slot is not None:
                ad_slot.md_bg_color = (
                    (0.02, 0.04, 0.06, 0.92)
                    if self.theme_cls.theme_style == "Dark"
                    else (0.86, 0.91, 0.95, 0.96)
                )
            footer_bar = getattr(self, "footer_bar", None)
            if footer_bar is not None:
                footer_bar.md_bg_color = (
                    (0.04, 0.07, 0.10, 1)
                    if self.theme_cls.theme_style == "Dark"
                    else (0.90, 0.94, 0.97, 1)
                )

        def _build_product_card(self, dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDRaisedButton, AsyncImage):
            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(10),
                size_hint_y=None,
                height=dp(264),
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            self._themed_cards.append(card)
            card.add_widget(MDLabel(text="Produkt", font_style="H6", size_hint_y=None, height=dp(30)))

            self.btn_category = MDRaisedButton(
                text="Wybierz kategorię",
                size_hint_x=1,
                size_hint_y=None,
                height=dp(48),
                font_size="15sp",
                on_release=lambda btn: self._open_category_menu(btn),
            )
            card.add_widget(self.btn_category)

            self.btn_product = MDRaisedButton(
                text="Wybierz produkt",
                size_hint_x=1,
                size_hint_y=None,
                height=dp(48),
                font_size="15sp",
                disabled=True,
                on_release=lambda btn: self._open_product_menu(btn),
            )
            card.add_widget(self.btn_product)

            self.image_box = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(92))
            self.image_placeholder = MDBoxLayout(
                orientation="vertical",
                spacing=dp(2),
                padding=[0, dp(8), 0, dp(4)],
            )
            self.image_placeholder.add_widget(
                MDIcon(
                    icon="image",
                    halign="center",
                    font_size="34sp",
                    theme_text_color="Hint",
                )
            )
            self.image_placeholder.add_widget(
                MDLabel(
                    text="Zdjęcie produktu pojawi się po wyborze",
                    halign="center",
                    font_style="Caption",
                    theme_text_color="Hint",
                )
            )
            self.product_image = AsyncImage(
                source="",
                allow_stretch=True,
                keep_ratio=True,
                opacity=0,
            )
            self.image_box.add_widget(self.image_placeholder)
            card.add_widget(self.image_box)
            return card

        def _build_params_card(self, dp, MDCard, MDBoxLayout, MDLabel, MDTextField, MDSwitch):
            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(10),
                size_hint_y=None,
                height=dp(360),
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            self._themed_cards.append(card)
            card.add_widget(MDLabel(text="Parametry", font_style="H6", size_hint_y=None, height=dp(30)))

            row_mass = MDBoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(68))
            self.in_m = MDTextField(
                hint_text="Masa",
                input_filter="float",
                size_hint_x=1,
                size_hint_y=None,
                height=dp(60),
            )
            self.lbl_unit = MDLabel(
                text="kg",
                halign="center",
                size_hint_x=None,
                width=dp(34),
                font_style="Subtitle1",
            )
            self.switch_unit = MDSwitch(active=False, size_hint_x=None, width=dp(72))
            self.switch_unit.bind(active=self._on_unit_switch)
            row_mass.add_widget(self.in_m)
            row_mass.add_widget(self.lbl_unit)
            row_mass.add_widget(self.switch_unit)
            card.add_widget(row_mass)

            self.in_T1 = MDTextField(
                hint_text="Temperatura początkowa [°C]", input_filter="float"
            )
            self.in_T2 = MDTextField(
                hint_text="Temperatura końcowa [°C]", input_filter="float"
            )
            self.in_t = MDTextField(hint_text="Czas pracy [h]", input_filter="float")
            for w in (self.in_T1, self.in_T2, self.in_t):
                w.size_hint_y = None
                w.height = dp(60)
                card.add_widget(w)
            return card

        def _build_action_button(self, dp, MDBoxLayout, MDRaisedButton):
            wrapper = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(72),
                spacing=dp(10),
                padding=[0, dp(8), 0, dp(8)],
            )
            wrapper.add_widget(
                MDRaisedButton(
                    text="Oblicz",
                    icon="calculator-variant",
                    size_hint_x=0.40,
                    size_hint_y=None,
                    height=dp(50),
                    font_size="15sp",
                    on_release=lambda *_: self._calculate(),
                )
            )
            wrapper.add_widget(
                MDRaisedButton(
                    text="PDF",
                    icon="file-pdf-box",
                    size_hint_x=0.27,
                    size_hint_y=None,
                    height=dp(50),
                    font_size="15sp",
                    on_release=lambda *_: self._export_pdf(),
                )
            )
            wrapper.add_widget(
                MDRaisedButton(
                    text="Wyczyść",
                    icon="broom",
                    size_hint_x=0.33,
                    size_hint_y=None,
                    height=dp(50),
                    font_size="15sp",
                    md_bg_color=(0.16, 0.19, 0.23, 1),
                    on_release=lambda *_: self._reset_inputs(),
                    theme_text_color="Custom",
                    text_color=(1.0, 0.55, 0.55, 1),
                )
            )
            return wrapper

        def _build_results_card(self, dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDProgressBar, MDGridLayout):
            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(10),
                size_hint_y=None,
                height=dp(456),
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            self._themed_cards.append(card)
            title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34), spacing=dp(8))
            title_row.add_widget(
                MDIcon(
                    icon="calculator",
                    size_hint_x=None,
                    width=dp(28),
                    halign="center",
                    font_size="24sp",
                    theme_text_color="Custom",
                    text_color=STAGE_COLORS["total"],
                )
            )
            title_row.add_widget(MDLabel(text="Wynik", font_style="H6"))
            card.add_widget(title_row)

            self.lbl_total = MDLabel(
                text="Suma mocy: — kW",
                font_style="H6",
                halign="center",
                size_hint_y=None,
                height=dp(50),
                theme_text_color="Custom",
                text_color=STAGE_COLORS["total"],
            )
            card.add_widget(self.lbl_total)

            self.bars: Dict[str, Dict] = {}
            for key, label, icon in [
                ("schladzanie", "Schładzanie", "thermometer"),
                ("zamrozenie", "Zamrożenie", "snowflake"),
                ("domrozenie", "Domrażanie", "thermometer"),
            ]:
                self.bars[key] = self._add_stage_row(
                    card, key, label, icon, dp, MDBoxLayout, MDIcon, MDLabel, MDProgressBar
                )

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
                spacing=dp(5),
                row_default_height=dp(24),
                row_force_default=True,
            )
            self.props_grid.bind(minimum_height=self.props_grid.setter("height"))
            card.add_widget(self.props_grid)
            return card

        def _add_stage_row(self, parent, key, label, icon, dp, MDBoxLayout, MDIcon, MDLabel, MDProgressBar):
            row = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(62), spacing=dp(4))
            head = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(8))
            head.add_widget(
                MDIcon(
                    icon=icon,
                    size_hint_x=None,
                    width=dp(28),
                    halign="center",
                    theme_text_color="Custom",
                    text_color=STAGE_COLORS[key],
                )
            )
            lbl_name = MDLabel(text=label, size_hint_x=0.52)
            lbl_val = MDLabel(text="—", halign="right", size_hint_x=0.4)
            head.add_widget(lbl_name)
            head.add_widget(lbl_val)
            bar = MDProgressBar(value=0, max=100, color=STAGE_COLORS[key])
            row.add_widget(head)
            row.add_widget(bar)
            parent.add_widget(row)
            return {"bar": bar, "value_label": lbl_val}

        def _build_footer(self, dp, MDBoxLayout, MDLabel):
            from tpof import __version__ as _app_version

            footer = MDBoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(34),
                padding=[dp(12), dp(4), dp(12), dp(4)],
                md_bg_color=(0.04, 0.07, 0.10, 1),
            )
            self.footer_bar = footer
            footer.add_widget(
                MDLabel(
                    text=f"Shocker Calc v{_app_version}  |  Sebastian Milczarek",
                    halign="center",
                    theme_text_color="Hint",
                    font_style="Caption",
                )
            )
            return footer

        def _build_ad_slot(self, dp, MDBoxLayout, MDIcon, MDLabel):
            slot = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(96),
                padding=[dp(16), dp(6), dp(16), dp(6)],
                spacing=dp(8),
                md_bg_color=(0.02, 0.04, 0.06, 0.92),
            )
            self.ad_slot = slot
            slot.add_widget(
                MDIcon(
                    icon="bullhorn",
                    size_hint_x=None,
                    width=dp(28),
                    halign="center",
                    theme_text_color="Hint",
                )
            )
            text = "Reklama" if IS_ANDROID else "Miejsce na baner AdMob"
            slot.add_widget(MDLabel(text=text, halign="center", font_style="Caption", theme_text_color="Hint"))
            return slot

        def _show_product_image(self, img_path: Optional[str]) -> None:
            self.image_box.clear_widgets()
            if img_path:
                self.product_image.source = img_path
                self.product_image.opacity = 1
                self.image_box.add_widget(self.product_image)
                return
            self.product_image.source = ""
            self.product_image.opacity = 0
            self.image_box.add_widget(self.image_placeholder)

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
            self._show_product_image(None)
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
            self._show_product_image(img)
            if self._prod_menu:
                self._prod_menu.dismiss()

        # --- akcje -------------------------------------------------------
        def _on_unit_switch(self, _switch, active: bool):
            self._mass_unit = "t" if active else "kg"
            self.lbl_unit.text = self._mass_unit

        def _toggle_theme(self):
            is_dark = self.theme_cls.theme_style == "Dark"
            self.theme_cls.theme_style = "Light" if is_dark else "Dark"
            self._sync_theme_surfaces()
            is_now_dark = self.theme_cls.theme_style == "Dark"
            self.toolbar.right_action_items = [
                [
                    "weather-night" if is_now_dark else "weather-sunny",
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
            # Subscripty przez Kivy markup (Roboto nie ma ₁₂).
            rows = [
                ("Kategoria:", p.kategoria or "—"),
                ("c[sub]1[/sub] [kJ/kg·K]:", f"{p.c1:.2f}" if p.c1 is not None else "—"),
                ("c[sub]2[/sub] [kJ/kg·K]:", f"{p.c2:.2f}" if p.c2 is not None else "—"),
                ("L[sub]1[/sub] [kJ/kg]:", f"{p.L1:.0f}" if p.L1 is not None else "—"),
                ("Woda [%]:", f"{p.wodaprocent:.1f}" if p.wodaprocent is not None else "—"),
                ("T[sub]zam[/sub] [°C]:", f"{results.T_zam_uzyte_C:.2f}{warn}"),
            ]
            for label, value in rows:
                self.props_grid.add_widget(
                    MDLabel(text=label, theme_text_color="Secondary", markup=True)
                )
                self.props_grid.add_widget(MDLabel(text=value))

            # Auto-scroll do wyników po obliczeniu — żeby nie chowały się pod akcjami.
            try:
                self.scroll.scroll_to(self.results_card, padding=dp(12), animate=True)
            except Exception:  # pragma: no cover
                pass

    ShockerCalcApp().run()


if __name__ == "__main__":
    main()
