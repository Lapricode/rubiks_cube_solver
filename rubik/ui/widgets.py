"""Small Tkinter widget wrappers used by the menus."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

ButtonCallback = Callable[[tk.Event], None]
SoundPlayer = Callable[[str, str], None]


class MenuButton:
    def __init__(
        self,
        background: tk.Misc,
        button_text: str | int | float,
        button_font: str,
        button_fg: str,
        button_bg: str,
        button_xcor: float | None,
        button_ycor: float | None,
        button_func: ButtonCallback,
        sound_player: SoundPlayer,
    ) -> None:
        self.button = tk.Label(
            background, text=button_text, font=button_font, fg=button_fg, bg=button_bg
        )
        if button_xcor is not None and button_ycor is not None:
            self.button.place(x=button_xcor, y=button_ycor, anchor="center")
        hover_font = self._hover_font(button_font)
        self.button.bind(
            "<Enter>",
            lambda event, button=self.button: [
                button.configure(font=hover_font),
                sound_player("hover_button_sound", "sound"),
            ],
        )
        self.button.bind(
            "<Leave>", lambda event, button=self.button: button.configure(font=button_font)
        )
        self.button.bind(
            "<Button-1>",
            lambda event: [button_func(event), sound_player("select_button_sound", "sound")],
        )

    @staticmethod
    def _hover_font(button_font: str) -> str:
        parts = button_font.split()
        if len(parts) > 1 and parts[1].isdigit():
            size = int(parts[1])
            parts[1] = str(size + max(2, int(size * 0.15)))
        return " ".join(parts)


class MenuLabel:
    def __init__(
        self,
        background: tk.Misc,
        label_text: str | int | float,
        label_font: str,
        label_fg: str,
        label_bg: str,
        label_xcor: float | None,
        label_ycor: float | None,
    ) -> None:
        self.label = tk.Label(
            background, text=label_text, font=label_font, fg=label_fg, bg=label_bg
        )
        if label_xcor is not None and label_ycor is not None:
            self.label.place(x=label_xcor, y=label_ycor, anchor="center")


class WidgetFactoryMixin:
    """Creates widgets wired to the application's sound player."""

    def _button(
        self,
        background: tk.Misc,
        text: str | int | float,
        font: str,
        fg: str,
        bg: str,
        x: float | None,
        y: float | None,
        func: ButtonCallback,
    ) -> tk.Label:
        return MenuButton(background, text, font, fg, bg, x, y, func, self.play_sound).button

    def _label(
        self,
        background: tk.Misc,
        text: str | int | float,
        font: str,
        fg: str,
        bg: str,
        x: float | None,
        y: float | None,
    ) -> tk.Label:
        return MenuLabel(background, text, font, fg, bg, x, y).label

    def _menu_button(
        self,
        background: tk.Misc,
        text: str | int | float,
        font: str,
        fg: str,
        bg: str,
        func: ButtonCallback,
    ) -> tk.Label:
        return MenuButton(background, text, font, fg, bg, None, None, func, self.play_sound).button

    def _menu_label(
        self,
        background: tk.Misc,
        text: str | int | float,
        font: str,
        fg: str,
        bg: str,
    ) -> tk.Label:
        return MenuLabel(background, text, font, fg, bg, None, None).label
