"""Kivy view composition for the mobile freezing tab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tpof.mobile.constants import STAGE_COLORS


@dataclass(frozen=True)
class FreezingStageView:
    """Widget references for one freezing-result stage."""

    row: Any
    head: Any
    icon_chip: Any
    icon: Any
    name_label: Any
    value_label: Any
    bar: Any


@dataclass(frozen=True)
class FreezingTabView:
    """Widget references exposed by the freezing tab's view boundary."""

    scroll: Any
    content: Any
    product_card: Any
    product_title_row: Any
    product_title_label: Any
    add_product_button: Any
    product_hint_label: Any
    product_body: Any
    product_controls: Any
    category_button: Any
    category_field_box: Any
    category_error_line: Any
    product_button: Any
    product_field_box: Any
    product_error_line: Any
    image_box: Any
    image_placeholder: Any
    image_placeholder_icon: Any
    image_placeholder_label: Any
    product_image: Any
    params_card: Any
    params_title_label: Any
    mass_row: Any
    mass_input: Any
    unit_button: Any
    temp_start_input: Any
    temp_end_input: Any
    time_input: Any
    results_card: Any
    results_title_row: Any
    results_title_label: Any
    action_row: Any
    calculate_button: Any
    pdf_button: Any
    clear_button: Any
    total_label: Any
    stages: dict[str, FreezingStageView]

    @property
    def input_fields(self) -> tuple[Any, ...]:
        """Return inputs in keyboard-navigation order."""

        return (
            self.mass_input,
            self.temp_start_input,
            self.temp_end_input,
            self.time_input,
        )


class FreezingTabViewCompositionMixin:
    """Build the Kivy widget tree while the controller owns behavior."""

    view: FreezingTabView | None

    def build(self: Any) -> FreezingTabView:
        """Create the complete freezing tab and retain its typed boundary."""

        from kivy.metrics import dp, sp
        from kivy.uix.image import AsyncImage
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDIconButton, MDRaisedButton
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDIcon, MDLabel
        from kivymd.uix.progressbar import MDProgressBar
        from kivymd.uix.scrollview import MDScrollView
        from kivymd.uix.textfield import MDTextField

        from tpof.mobile.widgets import StageIconBadge, StageMotionIcon

        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            padding=[dp(16), dp(14), dp(16), dp(18)],
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        product_card = MDCard(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(12),
            size_hint_y=None,
            height=dp(322 if self._hints_enabled() else 292),
            radius=[16, 16, 16, 16],
            elevation=3,
            md_bg_color=self._card_bg(),
        )
        self._register_themed_card(product_card)
        product_title_row = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(30)
        )
        product_title_label = MDLabel(
            text=self._translate("product"),
            font_style="H6",
        )
        add_product_button = MDIconButton(
            icon="plus-circle-outline",
            size_hint_x=None,
            width=dp(48),
            icon_size="26sp",
            theme_text_color="Custom",
            text_color=(0.18, 0.68, 0.95, 1),
            on_release=lambda *_: self._on_add_custom_product(),
        )
        product_title_row.add_widget(product_title_label)
        product_title_row.add_widget(add_product_button)
        product_card.add_widget(product_title_row)

        product_hint_label = MDLabel(
            text=self._translate("product_hint"),
            size_hint_y=None,
            height=dp(30 if self._hints_enabled() else 0),
            opacity=1 if self._hints_enabled() else 0,
            font_style="Caption",
            theme_text_color="Hint",
        )
        product_card.add_widget(product_hint_label)

        product_body = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(14),
            size_hint_y=None,
            height=dp(202),
        )
        product_controls = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=0.46,
            padding=[0, dp(8), 0, dp(8)],
        )
        category_button = MDRaisedButton(
            text=self._translate("choose_category"),
            size_hint_x=1,
            size_hint_y=None,
            height=dp(52),
            font_size="15sp",
            on_release=lambda caller: self.open_category_menu(caller),
        )
        category_field_box = MDBoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(54), spacing=0
        )
        category_field_box.add_widget(category_button)
        category_error_line = MDBoxLayout(
            size_hint_y=None,
            height=dp(2),
            opacity=0,
            md_bg_color=(0.94, 0.20, 0.26, 1),
        )
        category_field_box.add_widget(category_error_line)
        product_controls.add_widget(category_field_box)

        product_button = MDRaisedButton(
            text=self._translate("choose_product"),
            size_hint_x=1,
            size_hint_y=None,
            height=dp(52),
            font_size="15sp",
            disabled=True,
            on_release=lambda caller: self.open_product_menu(caller),
        )
        product_field_box = MDBoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(54), spacing=0
        )
        product_field_box.add_widget(product_button)
        product_error_line = MDBoxLayout(
            size_hint_y=None,
            height=dp(2),
            opacity=0,
            md_bg_color=(0.94, 0.20, 0.26, 1),
        )
        product_field_box.add_widget(product_error_line)
        product_controls.add_widget(product_field_box)
        product_body.add_widget(product_controls)

        image_box = MDBoxLayout(
            orientation="vertical",
            size_hint_x=0.54,
            padding=[0, dp(4), 0, dp(4)],
        )
        image_placeholder = MDBoxLayout(
            orientation="vertical",
            spacing=dp(2),
            padding=[0, dp(44), 0, dp(28)],
        )
        image_placeholder_icon = MDIcon(
            icon="image",
            halign="center",
            font_size="42sp",
            theme_text_color="Hint",
        )
        image_placeholder_label = MDLabel(
            text=self._translate("image_placeholder"),
            halign="center",
            font_style="Caption",
            theme_text_color="Hint",
        )
        image_placeholder.add_widget(image_placeholder_icon)
        image_placeholder.add_widget(image_placeholder_label)
        product_image = AsyncImage(
            source="",
            allow_stretch=True,
            keep_ratio=True,
            opacity=0,
        )
        image_box.add_widget(image_placeholder)
        product_body.add_widget(image_box)
        product_card.add_widget(product_body)
        content.add_widget(product_card)

        params_card = MDCard(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(10),
            size_hint_y=None,
            height=dp(392),
            radius=[16, 16, 16, 16],
            elevation=3,
            md_bg_color=self._card_bg(),
        )
        self._register_themed_card(params_card)
        params_title_label = MDLabel(
            text=self._translate("params"),
            font_style="H6",
            size_hint_y=None,
            height=dp(30),
        )
        params_card.add_widget(params_title_label)
        mass_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(10),
            size_hint_y=None,
            height=dp(78),
        )
        mass_input = MDTextField(
            hint_text=self._translate("mass"),
            input_filter=self._numeric_input_filter,
            size_hint_x=1,
        )
        self._configure_text_field(mass_input, dp=dp, sp=sp)
        unit_button = MDRaisedButton(
            text=self.mass_unit,
            size_hint_x=None,
            width=dp(72),
            size_hint_y=None,
            height=dp(48),
            font_size="15sp",
            pos_hint={"center_y": 0.5},
            on_release=lambda *_: self.toggle_mass_unit(),
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
        )
        mass_row.add_widget(mass_input)
        mass_row.add_widget(unit_button)
        params_card.add_widget(mass_row)

        temp_start_input = MDTextField(
            hint_text=self._translate("temperature_start"),
            input_filter=self._numeric_input_filter,
        )
        temp_end_input = MDTextField(
            hint_text=self._translate("temperature_end"),
            input_filter=self._numeric_input_filter,
        )
        time_input = MDTextField(
            hint_text=self._translate("work_time"),
            input_filter=self._numeric_input_filter,
        )
        for field in (temp_start_input, temp_end_input, time_input):
            self._configure_text_field(field, dp=dp, sp=sp)
            params_card.add_widget(field)
        content.add_widget(params_card)

        results_card = MDCard(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(8),
            size_hint_y=None,
            height=dp(390),
            radius=[16, 16, 16, 16],
            elevation=3,
            md_bg_color=self._card_bg(),
        )
        self._register_themed_card(results_card)
        results_title_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=0,
        )
        results_title_label = MDLabel(
            text=self._translate("result"),
            font_style="H6",
            valign="middle",
        )
        results_title_row.add_widget(results_title_label)
        results_card.add_widget(results_title_row)

        action_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(64),
            spacing=dp(8),
            padding=[0, dp(6), 0, dp(6)],
        )
        calculate_button = MDRaisedButton(
            text=self._translate("calculate"),
            icon="calculator-variant",
            size_hint_x=0.40,
            size_hint_y=None,
            height=dp(48),
            font_size="14sp",
            pos_hint={"center_y": 0.5},
            on_release=lambda *_: self.calculate(),
        )
        pdf_button = MDRaisedButton(
            text="PDF",
            icon="file-pdf-box",
            size_hint_x=0.27,
            size_hint_y=None,
            height=dp(48),
            font_size="14sp",
            pos_hint={"center_y": 0.5},
            on_release=lambda *_: self._on_export_pdf(),
        )
        clear_button = MDRaisedButton(
            text=self._translate("clear"),
            icon="broom",
            size_hint_x=0.33,
            size_hint_y=None,
            height=dp(48),
            font_size="14sp",
            md_bg_color=(0.16, 0.19, 0.23, 1),
            pos_hint={"center_y": 0.5},
            on_release=lambda *_: self.reset_inputs(),
            theme_text_color="Custom",
            text_color=(1.0, 0.55, 0.55, 1),
        )
        action_row.add_widget(calculate_button)
        action_row.add_widget(pdf_button)
        action_row.add_widget(clear_button)
        results_card.add_widget(action_row)

        total_label = MDLabel(
            text=self.total_text(),
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(46),
            theme_text_color="Custom",
            text_color=self.result_color(),
        )
        results_card.add_widget(total_label)

        stages: dict[str, FreezingStageView] = {}
        for key, label_key in (
            ("schladzanie", "cooling"),
            ("zamrozenie", "freezing"),
            ("domrozenie", "deep_freezing"),
        ):
            row = MDBoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(74),
                spacing=dp(6),
            )
            head = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(38),
                spacing=dp(10),
            )
            icon_chip = StageIconBadge(
                accent=STAGE_COLORS[key],
                size_hint_x=None,
                size_hint_y=None,
                width=dp(38),
                height=dp(38),
            )
            icon_widget = StageMotionIcon(
                mode=key,
                accent=STAGE_COLORS[key],
                size_hint=(1, 1),
            )
            icon_chip.add_widget(icon_widget)
            head.add_widget(icon_chip)
            name_label = MDLabel(
                text=self._translate(label_key),
                size_hint_x=0.52,
            )
            value_label = MDLabel(text="—", halign="right", size_hint_x=0.4)
            head.add_widget(name_label)
            head.add_widget(value_label)
            bar = MDProgressBar(value=0, max=100, color=STAGE_COLORS[key])
            row.add_widget(head)
            row.add_widget(bar)
            results_card.add_widget(row)
            stages[key] = FreezingStageView(
                row=row,
                head=head,
                icon_chip=icon_chip,
                icon=icon_widget,
                name_label=name_label,
                value_label=value_label,
                bar=bar,
            )
        content.add_widget(results_card)
        scroll.add_widget(content)
        scroll.size_hint = (1, 1)

        self.view = FreezingTabView(
            scroll=scroll,
            content=content,
            product_card=product_card,
            product_title_row=product_title_row,
            product_title_label=product_title_label,
            add_product_button=add_product_button,
            product_hint_label=product_hint_label,
            product_body=product_body,
            product_controls=product_controls,
            category_button=category_button,
            category_field_box=category_field_box,
            category_error_line=category_error_line,
            product_button=product_button,
            product_field_box=product_field_box,
            product_error_line=product_error_line,
            image_box=image_box,
            image_placeholder=image_placeholder,
            image_placeholder_icon=image_placeholder_icon,
            image_placeholder_label=image_placeholder_label,
            product_image=product_image,
            params_card=params_card,
            params_title_label=params_title_label,
            mass_row=mass_row,
            mass_input=mass_input,
            unit_button=unit_button,
            temp_start_input=temp_start_input,
            temp_end_input=temp_end_input,
            time_input=time_input,
            results_card=results_card,
            results_title_row=results_title_row,
            results_title_label=results_title_label,
            action_row=action_row,
            calculate_button=calculate_button,
            pdf_button=pdf_button,
            clear_button=clear_button,
            total_label=total_label,
            stages=stages,
        )
        self._bind_keyboard_scroll(self.view.input_fields, scroll)
        self.set_mass_unit(self.mass_unit)
        self.apply_theme()
        return self.view

    @staticmethod
    def _configure_text_field(field: Any, *, dp: Any, sp: Any) -> Any:
        field.size_hint_y = None
        field.height = dp(70)
        field.font_size = sp(18)
        field.padding = [0, dp(12), 0, dp(8)]
        field.multiline = False
        field.write_tab = False
        return field
