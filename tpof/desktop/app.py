"""Aplikacja desktopowa Refrigeration Calc (Tkinter + ttkbootstrap).

Cała logika domenowa jest delegowana do `tpof.core` — ta warstwa odpowiada
wyłącznie za prezentację, walidację formularza i interakcję z systemem plików.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ttkbootstrap.constants import BOTH, EW, LEFT, NSEW, RIGHT, E, W, X
from ttkbootstrap.widgets import Floodgauge, Meter

from tpof.core import (
    FreezingInputs,
    Product,
    calculate_freezing,
    find_product,
    is_positive_number,
    is_valid_temperature,
    list_categories,
    list_products,
    load_products,
    parse_number,
)
from tpof.core.pdf_report import build_pdf, save_pdf

from .paths import (
    DATA_PATH,
    FALLBACK_IMAGE,
    FONT_PATH,
    IMAGES_DIR,
    WATERMARK_PATH,
)

log = logging.getLogger(__name__)

APP_TITLE = "Refrigeration Calc"
APP_SUBTITLE = "Kalkulator zapotrzebowania chłodu dla procesu zamrażania"
AUTHOR_TEXT = "Autor: Sebastian Milczarek — MD-Puch Sp. z o.o."
PDF_AUTHOR_TEXT = "Autor:\nSebastian Milczarek\nMD-Puch Sp. z o.o."

# Dostępne motywy ttkbootstrap z podziałem na ciemne/jasne
DARK_THEMES = ["superhero", "darkly", "cyborg", "vapor", "solar"]
LIGHT_THEMES = ["cosmo", "flatly", "litera", "minty", "yeti"]
THEMES = DARK_THEMES + LIGHT_THEMES
DEFAULT_THEME = "superhero"
DEFAULT_LIGHT_THEME = "flatly"
DEFAULT_DARK_THEME = "superhero"

# Limit mocy do Metera (kW) — skala wizualna
METER_MAX_KW = 200.0


class FreezingCalculatorApp:
    def __init__(self, master: ttk.Window, catalog: dict[str, list[Product]]) -> None:
        self.master = master
        self.master.title(f"{APP_TITLE} — {APP_SUBTITLE}")
        self.master.minsize(1100, 720)
        self.catalog = catalog

        self.current_image_path: pathlib.Path | None = None
        self.current_photo: ImageTk.PhotoImage | None = None
        self.last_results = None  # type: ignore[assignment]

        self.status_var = tk.StringVar(value="Gotowy. Wprowadź parametry i wybierz produkt.")
        self.theme_var = tk.StringVar(value=DEFAULT_THEME)
        self.mass_unit_var = tk.StringVar(value="kg")  # kg | t

        self._set_app_icon()
        self._build_ui()
        self._center_window()

        self.master.protocol("WM_DELETE_WINDOW", self._on_close)

    # ============================================================== UI ===

    def _build_ui(self) -> None:
        self._apply_global_style()
        outer = ttk.Frame(self.master, padding=16)
        outer.pack(fill=BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        self._build_header(outer).grid(row=0, column=0, sticky=EW, pady=(0, 6))
        ttk.Separator(outer, bootstyle="primary").grid(row=1, column=0, sticky=EW, pady=(0, 12))
        self._build_top_panels(outer).grid(row=2, column=0, sticky=EW, pady=(0, 12))
        self._build_results_panel(outer).grid(row=3, column=0, sticky=NSEW)
        self._build_status_bar(self.master)

    def _apply_global_style(self) -> None:
        """Globalna typografia. Wysokość Treeview ustawiana per-widget po stworzeniu."""
        try:
            style = ttk.Style()
            style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        except Exception:  # noqa: BLE001
            log.exception("Nie udało się zastosować globalnego stylu")

    # ---------------------------------------------------------- Header ---

    def _build_header(self, parent: ttk.Frame) -> ttk.Frame:
        header = ttk.Frame(parent)
        header.columnconfigure(1, weight=1)

        logo_label = ttk.Label(header)
        try:
            if WATERMARK_PATH.exists():
                img = Image.open(WATERMARK_PATH)
                img.thumbnail((72, 72))
                self._logo_photo = ImageTk.PhotoImage(img)
                logo_label.configure(image=self._logo_photo)
        except Exception:  # noqa: BLE001
            log.exception("Nie udało się załadować logo")
        logo_label.grid(row=0, column=0, rowspan=2, padx=(0, 18), sticky=W)

        ttk.Label(
            header, text=APP_TITLE, font=("Segoe UI", 26, "bold"), bootstyle="primary",
        ).grid(row=0, column=1, sticky=W)
        ttk.Label(
            header, text=APP_SUBTITLE, font=("Segoe UI", 11, "italic"), bootstyle="info",
        ).grid(row=1, column=1, sticky=W)

        theme_frame = ttk.Frame(header)
        theme_frame.grid(row=0, column=2, rowspan=2, sticky=E)

        # Toggle dark/light
        self.dark_mode_var = tk.BooleanVar(value=self.theme_var.get() in DARK_THEMES)
        self.theme_toggle_btn = ttk.Button(
            theme_frame,
            text="☾ Dark" if self.dark_mode_var.get() else "☀ Light",
            command=self._toggle_dark_light,
            bootstyle="secondary-outline",
            width=10,
        )
        self.theme_toggle_btn.pack(side=LEFT, padx=(0, 8))

        ttk.Label(theme_frame, text="Motyw:", bootstyle="secondary").pack(side=LEFT, padx=(0, 6))
        theme_combo = ttk.Combobox(
            theme_frame, textvariable=self.theme_var, values=THEMES,
            state="readonly", width=12, bootstyle="secondary",
        )
        theme_combo.pack(side=LEFT)
        theme_combo.bind("<<ComboboxSelected>>", self._on_theme_changed)

        return header

    # ----------------------------------------------------- Top panels ---

    def _build_top_panels(self, parent: ttk.Frame) -> ttk.Frame:
        wrapper = ttk.Frame(parent)
        wrapper.columnconfigure(0, weight=2, uniform="cols")
        wrapper.columnconfigure(1, weight=1, uniform="cols")
        wrapper.columnconfigure(2, weight=1, uniform="cols")

        self._build_form(wrapper).grid(row=0, column=0, sticky=NSEW, padx=(0, 8))
        self._build_product_card(wrapper).grid(row=0, column=1, sticky=NSEW, padx=4)
        self._build_meter_card(wrapper).grid(row=0, column=2, sticky=NSEW, padx=(8, 0))
        return wrapper

    def _build_form(self, parent: ttk.Frame) -> ttk.Labelframe:
        card = ttk.Labelframe(parent, text="  Parametry procesu  ", padding=16, bootstyle="primary")
        card.columnconfigure(1, weight=1)

        # --- Masa z selektorem jednostek ---
        ttk.Label(card, text="Masa produktu").grid(row=0, column=0, sticky=W, padx=4, pady=6)
        mass_row = ttk.Frame(card)
        mass_row.grid(row=0, column=1, sticky=EW, padx=4, pady=6)
        mass_row.columnconfigure(0, weight=1)
        self.mass_entry = ttk.Entry(mass_row, bootstyle="primary")
        self.mass_entry.grid(row=0, column=0, sticky=EW, ipady=3)
        self._add_placeholder(self.mass_entry, "np. 250")
        self._add_tooltip(self.mass_entry, "Wprowadź masę produktu.\nPrzełącz jednostkę kg/t z prawej strony.")
        unit_combo = ttk.Combobox(
            mass_row, textvariable=self.mass_unit_var, values=["kg", "t"],
            state="readonly", width=4, bootstyle="primary",
        )
        unit_combo.grid(row=0, column=1, padx=(6, 0))
        unit_combo.bind("<<ComboboxSelected>>", self._on_mass_unit_changed)

        # --- Pozostałe pola ---
        other_rows = [
            (1, "Temperatura początkowa [°C]", "start_temp_entry", "np. 12",
             "Temperatura produktu przed włożeniem do komory."),
            (2, "Temperatura końcowa [°C]", "end_temp_entry", "np. -18",
             "Docelowa temperatura w środku produktu."),
            (3, "Czas pracy [h/dobę]", "time_entry", "np. 8",
             "Ile godzin na dobę agregat ma pracować, aby osiągnąć cel."),
        ]
        for i, label, attr, placeholder, tip in other_rows:
            ttk.Label(card, text=label).grid(row=i, column=0, sticky=W, padx=4, pady=6)
            entry = ttk.Entry(card, bootstyle="primary")
            entry.grid(row=i, column=1, sticky=EW, padx=4, pady=6, ipady=3)
            self._add_placeholder(entry, placeholder)
            self._add_tooltip(entry, tip)
            setattr(self, attr, entry)

        ttk.Separator(card, bootstyle="secondary").grid(
            row=4, column=0, columnspan=2, sticky=EW, pady=10,
        )

        ttk.Label(card, text="Kategoria").grid(row=5, column=0, sticky=W, padx=4, pady=6)
        self.category_var = tk.StringVar()
        self.category_dropdown = ttk.Combobox(
            card, textvariable=self.category_var, state="readonly", bootstyle="success",
        )
        self.category_dropdown.grid(row=5, column=1, sticky=EW, padx=4, pady=6, ipady=2)
        self.category_dropdown["values"] = list_categories(self.catalog)
        self.category_dropdown.bind("<<ComboboxSelected>>", self._on_category_changed)

        ttk.Label(card, text="Produkt").grid(row=6, column=0, sticky=W, padx=4, pady=6)
        self.product_var = tk.StringVar()
        self.product_dropdown = ttk.Combobox(
            card, textvariable=self.product_var, state="readonly", bootstyle="success",
        )
        self.product_dropdown.grid(row=6, column=1, sticky=EW, padx=4, pady=6, ipady=2)
        self.product_dropdown.bind("<<ComboboxSelected>>", self._on_product_changed)

        btn_frame = ttk.Frame(card)
        btn_frame.grid(row=7, column=0, columnspan=2, sticky=EW, pady=(16, 0))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        ttk.Button(
            btn_frame, text="Oblicz", command=self.calculate, bootstyle="success",
        ).grid(row=0, column=0, sticky=EW, padx=4, ipady=6)
        ttk.Button(
            btn_frame, text="Wyczyść", command=self.clear_form, bootstyle="secondary-outline",
        ).grid(row=0, column=1, sticky=EW, padx=4, ipady=6)
        ttk.Button(
            btn_frame, text="Generuj PDF", command=self.generate_pdf, bootstyle="info",
        ).grid(row=0, column=2, sticky=EW, padx=4, ipady=6)

        return card

    def _build_product_card(self, parent: ttk.Frame) -> ttk.Labelframe:
        card = ttk.Labelframe(parent, text="  Produkt  ", padding=12, bootstyle="info")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.image_label = ttk.Label(card, anchor="center")
        self.image_label.grid(row=0, column=0, sticky=NSEW, pady=(4, 8))

        self.product_name_label = ttk.Label(
            card, text="Wybierz produkt", font=("Segoe UI", 12, "bold"),
            anchor="center", bootstyle="inverse-info",
        )
        self.product_name_label.grid(row=1, column=0, sticky=EW, ipady=6)

        # Badge'y z najważniejszymi parametrami produktu
        self.product_badges = ttk.Frame(card)
        self.product_badges.grid(row=2, column=0, sticky=EW, pady=(8, 0))
        for c in range(3):
            self.product_badges.columnconfigure(c, weight=1, uniform="badges")
        self.product_info_label = ttk.Label(
            card, text="—", font=("Segoe UI", 9), anchor="center", bootstyle="secondary",
        )
        self.product_info_label.grid(row=3, column=0, sticky=EW, pady=(4, 0))

        self._set_image(None)
        return card

    def _build_meter_card(self, parent: ttk.Frame) -> ttk.Labelframe:
        card = ttk.Labelframe(parent, text="  Moc chłodnicza  ", padding=12, bootstyle="warning")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.power_meter = Meter(
            card,
            metersize=220,
            amountused=0,
            amounttotal=METER_MAX_KW,
            subtext="kW",
            textright="",
            bootstyle="warning",
            stripethickness=8,
            interactive=False,
        )
        self.power_meter.grid(row=0, column=0, pady=(4, 8))

        self.energy_label = ttk.Label(
            card, text="Q całkowite: —", font=("Segoe UI", 11, "bold"), anchor="center",
        )
        self.energy_label.grid(row=1, column=0, sticky=EW)

        return card

    # --------------------------------------------------------- Results ---

    def _build_results_panel(self, parent: ttk.Frame) -> ttk.Labelframe:
        card = ttk.Labelframe(parent, text="  Wyniki obliczeń  ", padding=12, bootstyle="success")
        card.columnconfigure(0, weight=3)
        card.columnconfigure(1, weight=1)
        card.rowconfigure(1, weight=1)

        # --- Górny rząd: Floodgauge dla każdego etapu (animowane słupki) ---
        gauges = ttk.Frame(card)
        gauges.grid(row=0, column=0, columnspan=2, sticky=EW, pady=(0, 12))
        for col in range(3):
            gauges.columnconfigure(col, weight=1, uniform="gauges")

        self.gauge_schladzanie = self._make_floodgauge(gauges, "Schładzanie", "info")
        self.gauge_schladzanie["frame"].grid(row=0, column=0, sticky=EW, padx=(0, 6))
        self.gauge_zamrozenie = self._make_floodgauge(gauges, "Zamrożenie", "primary")
        self.gauge_zamrozenie["frame"].grid(row=0, column=1, sticky=EW, padx=6)
        self.gauge_domrozenie = self._make_floodgauge(gauges, "Domrażanie", "warning")
        self.gauge_domrozenie["frame"].grid(row=0, column=2, sticky=EW, padx=(6, 0))

        # --- Tabela podsumowania (Treeview) ---
        table_frame = ttk.Frame(card)
        table_frame.grid(row=1, column=0, sticky=NSEW, padx=(0, 6))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("etap", "q_mj", "p_kw", "udzial")
        self.results_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings",
            bootstyle="success", height=8,
        )
        headings = [
            ("etap", "Etap", 200, W),
            ("q_mj", "Q [MJ]", 110, E),
            ("p_kw", "P [kW]", 110, E),
            ("udzial", "Udział [%]", 110, E),
        ]
        for col, label, width, anchor in headings:
            self.results_tree.heading(col, text=label)
            self.results_tree.column(col, width=width, anchor=anchor, stretch=True)
        self.results_tree.grid(row=0, column=0, sticky=NSEW)

        # KLUCZ: ttkbootstrap nadaje styl 'success.Treeview' — musimy go skonfigurować
        tree_style_name = self.results_tree.cget("style") or "Treeview"
        heading_style = f"{tree_style_name}.Heading"
        s = ttk.Style()
        s.configure(tree_style_name, rowheight=38, font=("Segoe UI", 11), borderwidth=0)
        s.configure(heading_style, font=("Segoe UI", 10, "bold"), padding=(6, 10))
        # Reapply po inicjalizacji (motyw może nadpisać)
        self.master.after(100, lambda: s.configure(tree_style_name, rowheight=38))

        tree_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.results_tree.yview, bootstyle="round",
        )
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.results_tree.configure(yscrollcommand=tree_scroll.set)

        # Style tagów dla wierszy (zebra + akcent na SUMA)
        try:
            style = self.master.style  # type: ignore[attr-defined]
            primary = style.colors.primary
            light_stripe = style.colors.inputbg
        except Exception:  # noqa: BLE001
            primary, light_stripe = "#2780E3", "#3A3A3A"
        self.results_tree.tag_configure("stage", font=("Segoe UI", 10))
        self.results_tree.tag_configure("stage_alt", font=("Segoe UI", 10), background=light_stripe)
        self.results_tree.tag_configure(
            "total", font=("Segoe UI", 11, "bold"),
            background=primary, foreground="#FFFFFF",
        )
        self.results_tree.tag_configure("separator", font=("Segoe UI", 4))

        # --- Panel parametrów produktu (po prawej) ---
        self.props_frame = ttk.Labelframe(
            card, text="  Parametry produktu  ", padding=10, bootstyle="info",
        )
        self.props_frame.grid(row=1, column=1, sticky=NSEW, padx=(6, 0))
        self.props_frame.columnconfigure(1, weight=1)
        self._props_rows: list = []
        self._render_props([])

        return card

    def _make_floodgauge(self, parent, title: str, bootstyle: str) -> dict:
        wrapper = ttk.Frame(parent)
        wrapper.columnconfigure(0, weight=1)
        ttk.Label(
            wrapper, text=title, font=("Segoe UI", 10, "bold"),
            bootstyle=bootstyle, anchor="center",
        ).grid(row=0, column=0, sticky=EW, pady=(0, 4))
        gauge = Floodgauge(
            wrapper, length=200, maximum=100, value=0,
            bootstyle=bootstyle, font=("Segoe UI", 14, "bold"),
            text="— kW",
        )
        gauge.grid(row=1, column=0, sticky=EW, ipady=8)
        return {"frame": wrapper, "gauge": gauge}

    def _render_props(self, rows) -> None:
        """Wyrenderuj tabelę etykieta -> wartość w panelu Parametry produktu."""
        for child in self.props_frame.winfo_children():
            child.destroy()
        if not rows:
            ttk.Label(
                self.props_frame, text="Wybierz produkt aby zobaczyć jego parametry.",
                bootstyle="secondary", wraplength=180, justify="left",
            ).grid(row=0, column=0, columnspan=2, sticky=W, pady=4)
            return
        for i, (label, value) in enumerate(rows):
            ttk.Label(
                self.props_frame, text=label, bootstyle="secondary", font=("Segoe UI", 9),
            ).grid(row=i, column=0, sticky=W, padx=(0, 8), pady=2)
            ttk.Label(
                self.props_frame, text=value, font=("Segoe UI", 10, "bold"),
            ).grid(row=i, column=1, sticky=E, pady=2)

    # ------------------------------------------------------ Status bar ---

    def _build_status_bar(self, parent) -> ttk.Frame:
        ttk.Separator(parent, bootstyle="secondary").pack(fill=X, side="bottom")
        bar = ttk.Frame(parent, padding=(12, 6))
        bar.pack(fill=X, side="bottom")
        self.status_dot = ttk.Label(
            bar, text="●", foreground="#2ECC71", font=("Segoe UI", 12),
        )
        self.status_dot.pack(side=LEFT, padx=(0, 6))
        ttk.Label(
            bar, textvariable=self.status_var,
            foreground="#FFFFFF", font=("Segoe UI", 9, "bold"),
        ).pack(side=LEFT)
        ttk.Label(
            bar, text=AUTHOR_TEXT,
            foreground="#E74C3C", font=("Segoe UI", 10, "bold italic"),
        ).pack(side=RIGHT)
        return bar

    # =========================================================== Helpers ===

    def _add_placeholder(self, entry: ttk.Entry, text: str) -> None:
        placeholder_color = "gray"

        def on_focus_in(_e):
            if entry.get() == text:
                entry.delete(0, tk.END)
                entry.configure(foreground="")

        def on_focus_out(_e):
            if not entry.get():
                entry.insert(0, text)
                entry.configure(foreground=placeholder_color)

        entry.insert(0, text)
        entry.configure(foreground=placeholder_color)
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        entry._placeholder = text  # type: ignore[attr-defined]

    def _get_entry_value(self, entry: ttk.Entry) -> str:
        value = entry.get()
        placeholder = getattr(entry, "_placeholder", None)
        return "" if value == placeholder else value

    def _set_image(self, path: pathlib.Path | None) -> None:
        target = path if (path and path.exists()) else (
            FALLBACK_IMAGE if FALLBACK_IMAGE.exists() else None
        )
        if target is None:
            self.image_label.configure(image="", text="(brak zdjęcia)")
            self.current_photo = None
            self.current_image_path = None
            return
        try:
            img = Image.open(target)
            img.thumbnail((220, 220))
            self.current_photo = ImageTk.PhotoImage(img)
            self.image_label.configure(image=self.current_photo, text="")
            self.image_label.image = self.current_photo
            self.current_image_path = target if target != FALLBACK_IMAGE else None
        except Exception:  # noqa: BLE001
            log.exception("Błąd ładowania zdjęcia")
            self.image_label.configure(image="", text="(błąd zdjęcia)")
            self.current_photo = None
            self.current_image_path = None

    def _set_app_icon(self) -> None:
        try:
            if WATERMARK_PATH.exists():
                img = Image.open(WATERMARK_PATH)
                img.thumbnail((64, 64))
                self._icon_photo = ImageTk.PhotoImage(img)
                self.master.iconphoto(True, self._icon_photo)
        except Exception:  # noqa: BLE001
            log.exception("Nie udało się ustawić ikony okna")

    def _center_window(self) -> None:
        self.master.update_idletasks()
        w = max(self.master.winfo_width(), 1100)
        h = max(self.master.winfo_height(), 720)
        sw = self.master.winfo_screenwidth()
        sh = self.master.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 3)
        self.master.geometry(f"{w}x{h}+{x}+{y}")

    def _set_status(self, msg: str, level: str = "info") -> None:
        """Aktualizuje pasek statusu i koloruje kropkę (info/success/warn/error)."""
        self.status_var.set(msg)
        colors = {
            "info": "#3498DB",
            "success": "#2ECC71",
            "warn": "#F39C12",
            "error": "#E74C3C",
        }
        dot = getattr(self, "status_dot", None)
        if dot is not None:
            dot.configure(foreground=colors.get(level, colors["info"]))

    def _add_tooltip(self, widget, text: str) -> None:
        """Lekki tooltip oparty na Toplevel."""
        tip = {"win": None}

        def show(_e=None):
            if tip["win"] is not None:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            try:
                tw.attributes("-topmost", True)
            except Exception:
                log.debug("Nie udało się ustawić tooltipa jako topmost", exc_info=True)
            lbl = tk.Label(
                tw, text=text, justify="left",
                background="#FFFFE0", foreground="#202020",
                relief="solid", borderwidth=1, font=("Segoe UI", 9),
                padx=8, pady=4,
            )
            lbl.pack()
            tip["win"] = tw

        def hide(_e=None):
            if tip["win"] is not None:
                try:
                    tip["win"].destroy()
                except Exception:
                    log.debug("Nie udało się zamknąć tooltipa", exc_info=True)
                tip["win"] = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)
        widget.bind("<FocusOut>", hide)

    def _on_mass_unit_changed(self, _event=None) -> None:
        unit = self.mass_unit_var.get()
        self._set_status(f"Jednostka masy: {unit} — wpisuj wartość w {unit}.")

    # ============================================================ Events ===

    def _on_category_changed(self, _event=None) -> None:
        selected_category = self.category_var.get()
        self.product_dropdown["values"] = list_products(self.catalog, selected_category)
        self.product_var.set("")
        self.product_name_label.configure(text="Wybierz produkt")
        self.product_info_label.configure(text="—")
        self._set_image(None)
        self._set_status(f"Kategoria: {selected_category}. Wybierz produkt.")

    def _on_product_changed(self, _event=None) -> None:
        name = self.product_var.get()
        category = self.category_var.get()
        if not name:
            return
        product = find_product(self.catalog, category, name)
        if product is None:
            return
        self.product_name_label.configure(text=name)
        info_parts = []
        if getattr(product, "T_zam", None) is not None:
            info_parts.append(f"T_zam: {product.T_zam:.1f} °C")
        if getattr(product, "wodaprocent", None) is not None:
            info_parts.append(f"woda: {product.wodaprocent:.0f} %")
        self.product_info_label.configure(text=" • ".join(info_parts) if info_parts else "—")
        self._render_product_badges(category, product)
        self._set_image(IMAGES_DIR / f"{name}.webp")
        self._set_status(f"Wybrano: {category} / {name}", level="info")

    def _render_product_badges(self, category: str, product) -> None:
        """Renderuje 3 odznaki pod nazwą produktu: kategoria, T_zam, woda."""
        for child in self.product_badges.winfo_children():
            child.destroy()
        badges = [("success", f" {category} ")]
        t_zam = getattr(product, "T_zam", None)
        if t_zam is not None:
            badges.append(("info", f" T_zam {t_zam:.1f}°C "))
        woda = getattr(product, "wodaprocent", None)
        if woda is not None:
            badges.append(("primary", f" H₂O {woda:.0f}% "))
        for i, (style, text) in enumerate(badges):
            ttk.Label(
                self.product_badges, text=text, bootstyle=f"inverse-{style}",
                font=("Segoe UI", 9, "bold"), anchor="center",
            ).grid(row=0, column=i, sticky=EW, padx=2, ipady=3)

    def _on_theme_changed(self, _event=None) -> None:
        new_theme = self.theme_var.get()
        try:
            self.master.style.theme_use(new_theme)  # type: ignore[attr-defined]
            self._apply_global_style()
            # Synchronizuj toggle dark/light z faktycznym motywem
            is_dark = new_theme in DARK_THEMES
            self.dark_mode_var.set(is_dark)
            self.theme_toggle_btn.configure(text="☾ Dark" if is_dark else "☀ Light")
            self._set_status(f"Motyw zmieniony: {new_theme}")
        except Exception as e:  # noqa: BLE001
            log.exception("Błąd zmiany motywu")
            messagebox.showerror("Błąd", f"Nie można zmienić motywu: {e}")

    def _toggle_dark_light(self) -> None:
        """Przełącz między domyślnym ciemnym a jasnym motywem."""
        currently_dark = self.theme_var.get() in DARK_THEMES
        new_theme = DEFAULT_LIGHT_THEME if currently_dark else DEFAULT_DARK_THEME
        self.theme_var.set(new_theme)
        self._on_theme_changed()

    def _on_close(self) -> None:
        self.master.destroy()

    def clear_form(self) -> None:
        for attr in ("mass_entry", "start_temp_entry", "end_temp_entry", "time_entry"):
            entry: ttk.Entry = getattr(self, attr)
            entry.delete(0, tk.END)
            ph = getattr(entry, "_placeholder", None)
            if ph:
                entry.insert(0, ph)
                entry.configure(foreground="gray")
        self.category_var.set("")
        self.product_var.set("")
        self.product_dropdown["values"] = []
        self.product_name_label.configure(text="Wybierz produkt")
        self.product_info_label.configure(text="—")
        for child in self.product_badges.winfo_children():
            child.destroy()
        self._set_image(None)
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self._render_props([])
        self.power_meter.configure(amountused=0)
        self.energy_label.configure(text="Q całkowite: —")
        for g in (self.gauge_schladzanie, self.gauge_zamrozenie, self.gauge_domrozenie):
            g["gauge"].configure(value=0, text="— kW")
        self.last_results = None
        self._set_status("Formularz wyczyszczony.", level="info")

    # ====================================================== Calculations ===

    def calculate(self) -> None:
        try:
            inputs = self._read_inputs()
            if inputs is None:
                return

            category = self.category_var.get()
            product_name = self.product_var.get()
            if not category or not product_name:
                messagebox.showerror("Błąd", "Wybierz kategorię i produkt.")
                return

            product = find_product(self.catalog, category, product_name)
            if product is None:
                messagebox.showerror("Błąd", "Nie znaleziono wybranego produktu.")
                return

            results = calculate_freezing(inputs, product)
            self.last_results = results
            self._display_results(results)
            self._update_meter(results)
            self._set_status(
                f"Obliczono: {product_name} • Q={results.Q_total_kJ/1000:.2f} MJ • "
                f"P={results.P_total_kW:.2f} kW",
                level="success",
            )
        except Exception as e:  # noqa: BLE001
            log.exception("Błąd podczas obliczeń")
            messagebox.showerror("Błąd", f"Wystąpił błąd: {e}")
            self._set_status("Błąd obliczeń — zobacz okno błędu.", level="error")

    def _read_inputs(self) -> FreezingInputs | None:
        m = self._validate(self.mass_entry, "Masa musi być liczbą dodatnią.", is_positive_number)
        T_pocz = self._validate(
            self.start_temp_entry,
            "Temperatura początkowa musi być w zakresie -273.15..200 °C.",
            is_valid_temperature,
        )
        T_konc = self._validate(
            self.end_temp_entry,
            "Temperatura końcowa musi być w zakresie -273.15..200 °C.",
            is_valid_temperature,
        )
        t = self._validate(self.time_entry, "Czas musi być liczbą dodatnią.", is_positive_number)

        if None in (m, T_pocz, T_konc, t):
            return None

        # Konwersja jednostki masy
        masa_kg = float(m) * 1000.0 if self.mass_unit_var.get() == "t" else float(m)

        if T_konc >= T_pocz:  # type: ignore[operator]
            messagebox.showerror(
                "Błąd",
                "Temperatura końcowa musi być niższa niż początkowa "
                "(proces chłodzenia/zamrażania).",
            )
            return None

        return FreezingInputs(
            masa_kg=masa_kg, T_pocz_C=float(T_pocz), T_konc_C=float(T_konc), czas_h=float(t)
        )

    def _validate(self, entry: ttk.Entry, error_message: str, validator) -> float | None:
        raw = self._get_entry_value(entry)
        value = parse_number(raw)
        if value is None or not validator(value):
            messagebox.showerror("Błąd", error_message)
            return None
        return value

    def _display_results(self, results) -> None:
        # 1) Tabela podsumowania (Treeview)
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        total_p = max(float(results.P_total_kW), 1e-9)
        rows = [
            ("❄ Schładzanie", results.Q_schladzanie_kJ, results.P_schladzanie_kW),
            ("🧊 Zamrożenie", results.Q_zamrozenie_kJ, results.P_zamrozenie_kW),
            ("⛄ Domrażanie", results.Q_domrozenie_kJ, results.P_domrozenie_kW),
        ]
        for idx, (name, q_kj, p_kw) in enumerate(rows):
            udzial = p_kw / total_p * 100.0
            tag = "stage_alt" if idx % 2 else "stage"
            self.results_tree.insert(
                "", "end", tags=(tag,),
                values=(name, f"{q_kj/1000:.2f}", f"{p_kw:.2f}", f"{udzial:.1f}"),
            )
        self.results_tree.insert(
            "", "end", tags=("total",),
            values=(
                "  Σ  SUMA",
                f"{results.Q_total_kJ/1000:.2f}",
                f"{results.P_total_kW:.2f}",
                "100.0",
            ),
        )

        # 2) Panel parametrów produktu (po prawej)
        p = results.produkt
        props = []

        def add(label, value, fmt="{:.2f}", suffix=""):
            if value is not None:
                props.append((label, fmt.format(value) + suffix))

        add("c (powyżej zam.)", p.c1, suffix=" kJ/(kg·K)")
        add("c (poniżej zam.)", p.c2, suffix=" kJ/(kg·K)")
        add("T_zam", results.T_zam_uzyte_C, suffix=" °C")
        add("Woda", p.wodaprocent, suffix=" %")
        add("L (top.)", p.L1, suffix=" kJ/kg")
        if any(x is not None for x in (p.bialko, p.tluszcz, p.weglowodany, p.blonnik, p.popiol)):
            props.append(("── Skład ──", ""))
            add("Białko", p.bialko, suffix=" %")
            add("Tłuszcz", p.tluszcz, suffix=" %")
            add("Węglowodany", p.weglowodany, suffix=" %")
            add("Błonnik", p.blonnik, suffix=" %")
            add("Popiół", p.popiol, suffix=" %")

        if results.T_zam_szacunkowy:
            props.append(("⚠ T_zam", "wartość szacunkowa"))

        self._render_props(props)
        self.master.update_idletasks()

    def _update_meter(self, results) -> None:
        p_kw = float(results.P_total_kW)
        # Auto-skalowanie: jeśli wynik >80% obecnej skali, podnieś ją
        try:
            scale = float(self.power_meter.amounttotalvar.get())
        except Exception:  # noqa: BLE001
            scale = METER_MAX_KW
        if p_kw > scale * 0.8 or (scale > METER_MAX_KW and p_kw < scale * 0.25):
            new_scale = max(50, int(((p_kw * 1.5) // 50 + 1) * 50))
            self.power_meter.configure(amounttotal=new_scale)
            scale = new_scale
        if p_kw < scale * 0.4:
            style = "success"
        elif p_kw < scale * 0.75:
            style = "warning"
        else:
            style = "danger"
        self.power_meter.configure(bootstyle=style)
        try:
            current = float(self.power_meter.amountusedvar.get())
        except Exception:  # noqa: BLE001
            current = 0.0
        self._animate_meter(current, round(p_kw, 1))
        self.energy_label.configure(text=f"Q całkowite: {results.Q_total_kJ/1000:.2f} MJ")

        # Floodgauges — każdy etap pokazuje swój % udziału w sumie mocy
        total = max(p_kw, 1e-9)
        for g, p_stage in (
            (self.gauge_schladzanie, results.P_schladzanie_kW),
            (self.gauge_zamrozenie, results.P_zamrozenie_kW),
            (self.gauge_domrozenie, results.P_domrozenie_kW),
        ):
            pct = round(p_stage / total * 100.0, 1)
            self._animate_gauge(g["gauge"], float(g["gauge"].cget("value")), pct,
                                  label=f"{p_stage:.1f} kW  ({pct:.0f}%)")

    def _animate_meter(self, start: float, end: float, steps: int = 20) -> None:
        """Płynne dojście wskazówki Meter od start → end."""
        if steps <= 0 or abs(end - start) < 0.5:
            self.power_meter.configure(amountused=end)
            return
        delta = (end - start) / steps

        def step(i: int, current: float) -> None:
            if i >= steps:
                self.power_meter.configure(amountused=end)
                return
            current += delta
            self.power_meter.configure(amountused=round(current, 1))
            self.master.after(20, step, i + 1, current)

        step(0, start)

    def _animate_gauge(self, gauge: Floodgauge, start: float, end: float,
                       label: str, steps: int = 20) -> None:
        """Płynna animacja Floodgauge z aktualizacją etykiety."""
        gauge.configure(text=label)
        if steps <= 0 or abs(end - start) < 0.5:
            gauge.configure(value=end)
            return
        delta = (end - start) / steps

        def step(i: int, current: float) -> None:
            if i >= steps:
                gauge.configure(value=end)
                return
            current += delta
            gauge.configure(value=round(current, 1))
            self.master.after(20, step, i + 1, current)

        step(0, start)

    # ============================================================= PDF ===

    def generate_pdf(self) -> None:
        if self.last_results is None:
            messagebox.showerror("Błąd", "Najpierw wykonaj obliczenia.")
            return

        desktop = pathlib.Path(os.path.expanduser("~")) / "Desktop"
        file_path = filedialog.asksaveasfilename(
            initialdir=desktop if desktop.exists() else pathlib.Path.home(),
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="Zapisz PDF",
        )
        if not file_path:
            return

        password = simpledialog.askstring(
            "Hasło PDF",
            "Hasło właściciela (do edycji). Zostaw puste, aby nie szyfrować:",
            show="*",
            parent=self.master,
        )

        try:
            pdf_bytes = build_pdf(
                results=self.last_results,
                font_path=FONT_PATH,
                product_image_path=self.current_image_path,
                watermark_image_path=WATERMARK_PATH if WATERMARK_PATH.exists() else None,
                author_text=PDF_AUTHOR_TEXT,
                owner_password=password or None,
            )
            save_pdf(pdf_bytes, pathlib.Path(file_path))
            msg = "PDF wygenerowany i zabezpieczony hasłem." if password else "PDF wygenerowany."
            messagebox.showinfo("Sukces", msg)
            self._set_status(f"Zapisano PDF: {file_path}")
        except Exception as e:  # noqa: BLE001
            log.exception("Błąd generowania PDF")
            messagebox.showerror("Błąd", f"Wystąpił błąd podczas generowania PDF: {e}")
            self._set_status("Błąd zapisu PDF.")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    try:
        catalog = load_products(DATA_PATH)
    except FileNotFoundError:
        root = ttk.Window()
        root.withdraw()
        messagebox.showerror("Błąd", f"Nie znaleziono pliku Table3.json:\n{DATA_PATH}")
        return
    except json.JSONDecodeError:
        root = ttk.Window()
        root.withdraw()
        messagebox.showerror("Błąd", "Niepoprawna struktura pliku JSON.")
        return

    root = ttk.Window(themename=DEFAULT_THEME)
    FreezingCalculatorApp(root, catalog)
    root.mainloop()


if __name__ == "__main__":
    main()
