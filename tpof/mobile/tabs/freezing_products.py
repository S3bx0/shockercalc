"""Product selection workflow for the mobile freezing tab."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Any

from tpof.core import Product
from tpof.mobile.catalog import (
    _mobile_product_names,
    _ordered_mobile_categories,
    _search_product_names,
)
from tpof.mobile.tabs.freezing_view import FreezingTabView

log = logging.getLogger(__name__)


class FreezingProductSelectionMixin:
    """Own category, product, search and recent-selection interactions."""

    _catalog: dict[str, list[Product]]
    _categories: list[str]
    _translate: Callable[..., str]
    _display_category: Callable[[str | None], str]
    _display_product: Callable[[str | None], str]
    _show_message: Callable[[str], None]
    _is_product_selectable: Callable[[int], bool]
    _recent_products: Callable[[str, Sequence[str]], Sequence[str]]
    _add_recent_product: Callable[[str, str], None]
    _resolve_product_image: Callable[[str], str | None]
    _menu_factory: Callable[..., Any]
    _is_compact: Callable[[], bool]
    _menu_text_color: Callable[[], Any]
    _divider_color: Callable[[], Any]

    selected_category: str | None
    selected_product: str | None
    view: FreezingTabView | None

    _category_menu: Any | None
    _product_dialog: Any | None
    _product_search_field: Any | None
    _product_results_list: Any | None
    _product_dialog_names: list[str]
    _product_dialog_indexes: dict[str, int]
    _product_dialog_window: Any | None
    _product_previous_softinput_mode: str | None

    def _initialize_product_selection(self) -> None:
        self.selected_category = None
        self.selected_product = None
        self._category_menu = None
        self._product_dialog = None
        self._product_search_field = None
        self._product_results_list = None
        self._product_dialog_names = []
        self._product_dialog_indexes = {}
        self._product_dialog_window = None
        self._product_previous_softinput_mode = None

    def set_custom_product_available(self, available: bool) -> None:
        if self.view is not None:
            self.view.add_product_button.opacity = 1 if available else 0.72

    def show_product_image(self, image_path: str | None) -> None:
        if self.view is None:
            return
        self.view.image_box.clear_widgets()
        if image_path:
            self.view.product_image.source = image_path
            self.view.product_image.opacity = 1
            self.view.image_box.add_widget(self.view.product_image)
            return
        self.view.product_image.source = ""
        self.view.product_image.opacity = 0
        self.view.image_box.add_widget(self.view.image_placeholder)

    def select_category(self, category: str) -> None:
        """Select a category and clear a stale product selection."""

        self.selected_category = category
        self.selected_product = None
        if self.view is not None:
            self.view.category_button.text = self._display_category(category)
            self.view.product_button.text = self._translate("choose_product")
            self.view.product_button.disabled = False
            self.view.category_error_line.opacity = 0
            self.view.product_error_line.opacity = 0
            self.show_product_image(None)
        if self._category_menu is not None:
            self._category_menu.dismiss()

    def select_product(self, name: str, *, image_path: str | None = None) -> None:
        """Select a product in the active category."""

        if self.selected_category is None:
            return
        self.selected_product = name
        self._add_recent_product(self.selected_category, name)
        if self.view is not None:
            self.view.product_button.text = self._display_product(name)
            self.view.product_error_line.opacity = 0
            resolved = (
                image_path
                if image_path is not None
                else self._resolve_product_image(name)
            )
            self.show_product_image(resolved)
        self.close_product_dialog()

    def select_saved_product(self, product: Product) -> None:
        """Select a newly persisted custom product without resolving an image."""

        self.select_category(product.kategoria)
        self.selected_product = product.nazwa
        self._add_recent_product(product.kategoria, product.nazwa)
        if self.view is not None:
            self.view.product_button.text = self._display_product(product.nazwa)
            self.show_product_image(None)

    def open_category_menu(self, caller: Any) -> None:
        from kivy.metrics import dp
        from kivymd.uix.menu import MDDropdownMenu

        item_height = dp(46 if self._is_compact() else 52)
        featured, remaining = _ordered_mobile_categories(
            self._categories,
            self._display_category,
        )
        ordered = featured + remaining
        items = [
            {
                "text": self._display_category(category),
                "viewclass": "OneLineListItem",
                "height": item_height,
                "theme_text_color": "Custom",
                "text_color": self._menu_text_color(),
                "on_release": lambda value=category: self.select_category(value),
            }
            for category in ordered
        ]
        if featured and remaining:
            items.insert(
                len(featured),
                {
                    "viewclass": "MDSeparator",
                    "height": dp(1),
                    "color": self._divider_color(),
                },
            )
        self._category_menu = self._menu_factory(
            caller,
            items,
            3.7,
            dp(390),
            dp,
            MDDropdownMenu,
        )
        self._category_menu.open()

    def open_product_menu(self, _caller: Any) -> None:
        from kivy.core.window import Window
        from kivy.metrics import dp
        from kivy.uix.scrollview import ScrollView
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.list import MDList
        from kivymd.uix.textfield import MDTextField

        if not self.selected_category:
            return
        self.close_product_dialog()
        self._begin_product_dialog_softinput_mode(Window)
        self._product_dialog_names = _mobile_product_names(
            self._catalog,
            self.selected_category,
        )
        self._product_dialog_indexes = {
            name: index for index, name in enumerate(self._product_dialog_names)
        }
        outer = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None,
            height=min(dp(520), max(dp(340), Window.height * 0.66)),
        )
        self._product_search_field = MDTextField(
            hint_text=self._translate("search_products"),
            icon_right="magnify",
            mode="rectangle",
            size_hint_y=None,
            height=dp(58),
        )
        outer.add_widget(self._product_search_field)
        results_scroll = ScrollView(do_scroll_x=False)
        self._product_results_list = MDList()
        results_scroll.add_widget(self._product_results_list)
        outer.add_widget(results_scroll)
        self._product_dialog = MDDialog(
            title=self._translate("product_picker_title"),
            type="custom",
            content_cls=outer,
            buttons=[
                MDFlatButton(
                    text=self._translate("close"),
                    on_release=lambda *_: self.close_product_dialog(),
                )
            ],
        )
        self._product_search_field.bind(
            text=lambda _field, value: self.refresh_product_search_results(value)
        )
        self.refresh_product_search_results("")
        self._product_dialog.open()

    def _begin_product_dialog_softinput_mode(self, window: Any) -> None:
        """Keep a modal search field from panning the whole Kivy surface."""

        if self._product_dialog_window is not None:
            return
        previous = getattr(window, "softinput_mode", None)
        self._product_dialog_window = window
        self._product_previous_softinput_mode = (
            previous if isinstance(previous, str) else None
        )
        try:
            window.softinput_mode = ""
        except Exception:
            log.debug(
                "Could not disable product-dialog soft-input panning.",
                exc_info=True,
            )

    def _restore_product_dialog_softinput_mode(self) -> None:
        window = self._product_dialog_window
        previous = self._product_previous_softinput_mode
        self._product_dialog_window = None
        self._product_previous_softinput_mode = None
        if window is None or previous is None:
            return
        try:
            window.softinput_mode = previous
        except Exception:
            log.debug(
                "Could not restore the window soft-input mode.",
                exc_info=True,
            )

    def _add_product_search_item(self, name: str, item_height: Any) -> None:
        from kivymd.uix.list import OneLineListItem

        if self._product_results_list is None:
            return
        index = self._product_dialog_indexes.get(name, 10**9)
        allowed = self._is_product_selectable(index)
        item = OneLineListItem(
            text=(
                self._display_product(name)
                if allowed
                else (
                    f"{self._display_product(name)}"
                    f"{self._translate('locked_suffix')}"
                )
            ),
            height=item_height,
            theme_text_color="Custom",
            text_color=(
                self._menu_text_color()
                if allowed
                else (0.55, 0.58, 0.62, 1)
            ),
            on_release=(
                (lambda *_args, value=name: self.select_product(value))
                if allowed
                else (lambda *_args: self.on_locked_product())
            ),
        )
        self._product_results_list.add_widget(item)

    def _add_product_search_heading(self, text: str, dp: Any) -> None:
        from kivymd.uix.label import MDLabel

        if self._product_results_list is None:
            return
        self._product_results_list.add_widget(
            MDLabel(
                text=text,
                size_hint_y=None,
                height=dp(34),
                font_style="Caption",
                theme_text_color="Secondary",
                padding=(dp(12), 0),
            )
        )

    def refresh_product_search_results(self, query: str) -> None:
        from kivy.metrics import dp

        if self._product_results_list is None:
            return
        self._product_results_list.clear_widgets()
        names = _search_product_names(
            self._product_dialog_names,
            query,
            self._display_product,
        )
        item_height = dp(46 if self._is_compact() else 52)
        if not names:
            self._add_product_search_heading(
                self._translate("no_products_found"),
                dp,
            )
            return
        if not str(query or "").strip():
            recent = list(
                self._recent_products(
                    self.selected_category or "",
                    self._product_dialog_names,
                )
            )[:4]
            if recent:
                self._add_product_search_heading(
                    self._translate("recent_products"),
                    dp,
                )
                for name in recent:
                    self._add_product_search_item(name, item_height)
                self._add_product_search_heading(
                    self._translate("all_products"),
                    dp,
                )
        for name in names:
            self._add_product_search_item(name, item_height)

    def close_product_dialog(self) -> None:
        if self._product_search_field is not None:
            self._product_search_field.focus = False
        if self._product_dialog is not None:
            self._product_dialog.dismiss()
        self._product_dialog = None
        self._product_search_field = None
        self._product_results_list = None
        self._restore_product_dialog_softinput_mode()

    def on_locked_product(self) -> None:
        self.close_product_dialog()
        self._show_message(self._translate("product_locked"))
