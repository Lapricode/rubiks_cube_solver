"""Menu construction and menu-related event handlers."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import simpledialog

from PIL import Image, ImageTk

from .. import texts
from ..config import (
    BORDERS_WIDTHS,
    CUBE_DIMENSIONS,
    DEFAULT_BUTTONS_FONT,
    DEFAULT_MENUS_FONT,
    DEFAULT_OPTIONS_FONT,
    MAX_CUBE_SIZE,
    MIN_CUBE_SIZE,
    MOVE_KEY_BINDINGS,
    MOVE_SPEEDS,
    NOTATION_IMAGE_PATH,
    RANDOM_SCRAMBLE_MOVE_COUNTS,
    SIDES_DISTORTIONS,
    SPECIAL_MOVE_KEY_BINDINGS,
    VIEW_KEY_BINDINGS,
    piece_side_length_for_size,
    piece_side_length_limits,
)


class MenusMixin:
    def create_menus(self) -> None:
        panel = self.menu_panel
        width, height = panel.width, panel.height
        if width <= 1 or height <= 1:
            return

        menu_bg = self.theme["menu_bg"]
        menu_title = self.theme["menu_title"]
        menu_label = self.theme["menu_label"]
        menu_text = self.theme["menu_text"]
        button_fg = self.theme["button_fg"]
        button_bg = self.theme["button_bg"]
        button_hover = self.theme["button_hover"]
        button_outline = self.theme["button_outline"]
        panel.begin(menu_bg)
        scale = max(0.7, min(1.35, min(width / 360.0, height / 700.0)))
        pad = max(6, int(9 * scale))
        title_size = max(13, int(18 * scale))
        label_size = max(10, int(13 * scale))
        button_size = max(9, int(12 * scale))
        small_size = max(8, int(10 * scale))
        row_height = max(18, int(24 * scale))
        action_height = max(20, int(27 * scale))
        gap = max(5, int(8 * scale))
        footer_height = max(15, int(20 * scale))
        footer_y = height - footer_height
        y = pad

        def draw_setting(
            key_prefix: str, label: str, value: object, callback: Callable[[], None]
        ) -> None:
            nonlocal y
            panel.text(
                label,
                pad,
                y + row_height / 2,
                size=label_size,
                color=menu_label,
                anchor="w",
                max_width=max(40, width - 3 * pad - int(width * 0.28)),
            )
            button_width = max(52, int(width * 0.27))
            panel.button(
                f"setting:{key_prefix}:{label}",
                (width - pad - button_width, y, button_width, row_height - 2),
                str(value),
                button_size,
                button_fg,
                button_bg,
                callback,
                hover_bg=button_hover,
                outline=button_outline,
            )
            y += row_height

        def draw_section(title: str, rows: list[tuple[str, object, Callable[[], None]]]) -> None:
            nonlocal y
            panel.text(
                title,
                pad,
                y,
                size=title_size,
                color=menu_title,
                bold=True,
                serif=True,
                max_width=width - 2 * pad,
            )
            y += title_size + 3
            key_prefix = title.lower().rstrip(":").replace(" ", "_")
            for label, value, callback in rows:
                draw_setting(key_prefix, label, value, callback)
            y += gap

        def draw_action(label: str, callback: Callable[[], None]) -> None:
            nonlocal y
            panel.button(
                f"action:{label}",
                (pad, y, width - 2 * pad, action_height),
                label,
                button_size,
                button_fg,
                button_bg,
                callback,
                hover_bg=button_hover,
                outline=button_outline,
            )
            y += action_height + max(2, gap // 2)

        def separator() -> None:
            nonlocal y
            panel.line((pad, y), (width - pad, y), button_outline)
            y += gap

        header_height = max(21, int(28 * scale))
        header_gap = max(3, pad // 2)
        reset_width = int((width - 2 * pad - 2 * header_gap) * 0.44)
        info_width = int((width - 2 * pad - 2 * header_gap) * 0.22)
        sound_width = width - 2 * pad - 2 * header_gap - reset_width - info_width
        header_y = y
        panel.button(
            "header:reset",
            (pad, header_y, reset_width, header_height),
            "reset",
            button_size,
            button_fg,
            button_bg,
            self.reset_game,
            hover_bg=button_hover,
            outline=button_outline,
        )
        panel.button(
            "header:info",
            (pad + reset_width + header_gap, header_y, info_width, header_height),
            "info",
            button_size,
            button_fg,
            button_bg,
            self.show_instructions,
            hover_bg=button_hover,
            outline=button_outline,
        )
        panel.button(
            "header:sound",
            (
                pad + reset_width + info_width + 2 * header_gap,
                header_y,
                sound_width,
                header_height,
            ),
            "sound on" if self.sound_is_activated else "sound off",
            button_size,
            button_fg,
            button_bg,
            self.enable_disable_sound,
            hover_bg=button_hover,
            outline=button_outline,
        )
        y += header_height + gap

        draw_section(
            "Cube:",
            [
                (
                    "size:",
                    self.cube_size_label(),
                    lambda: self.change_cube_size(None),
                )
            ],
        )
        separator()
        draw_section(
            "Cube graphics:",
            [
                (
                    "borders width:",
                    self.borders_width,
                    lambda: self.change_game_setting("borders_width"),
                ),
                (
                    "sides distortion:",
                    self.sides_distortion,
                    lambda: self.change_game_setting("sides_distortion"),
                ),
                (
                    "hidden sides:",
                    self.hidden_sides_visibility,
                    lambda: self.change_game_setting("hidden_sides_visibility"),
                ),
                (
                    "3d axis:",
                    self.axis_visibility,
                    lambda: self.change_game_setting("axis_visibility"),
                ),
                (
                    "scramble pattern:",
                    self.scramble_pattern_visibility,
                    lambda: self.change_game_setting("scramble_pattern_visibility"),
                ),
                (
                    "dimensions:",
                    self.cube_dimensions,
                    lambda: self.change_game_setting("cube_dimensions"),
                ),
            ],
        )
        separator()
        draw_section(
            "Scramble cube:",
            [
                (
                    "time/move (sec):",
                    self.scramble_moves_speed,
                    lambda: self.change_game_setting("scramble_moves_speed"),
                ),
                (
                    "moves number:",
                    self.random_scramble_moves,
                    lambda: self.change_game_setting("random_scramble_moves"),
                ),
            ],
        )
        draw_action("random scramble", lambda: self.moves_scramble_cube(object()))
        draw_action("draw pattern", lambda: self.draw_scramble_cube())
        separator()
        draw_section(
            "Solve cube:",
            [
                (
                    "time/move (sec):",
                    self.solve_moves_speed,
                    lambda: self.change_game_setting("solve_moves_speed"),
                )
            ],
        )
        draw_action(
            "solve",
            lambda: self.auto_solve_cube("choose_method", None, None, None),
        )

        compact_actions = [
            ("history", self.show_history),
            ("statistics", self.show_stats),
            ("shortcuts", self.show_shortcuts_overlay),
            ("save state", self.save_cube_state),
            ("load state", self.load_cube_state),
            ("export solution", self.export_current_solution),
            (f"tutorial: {'on' if self.tutorial_enabled else 'off'}", self.toggle_tutorial),
            (f"theme: {self.theme_name}", self.change_theme),
            (
                f"smooth turns: {'on' if self.smooth_turns_enabled else 'off'}",
                self.toggle_smooth_turns,
            ),
            (f"turn speed: {self.turn_animation_duration} ms", self.cycle_turn_animation_duration),
        ]
        if y + 2 * (action_height + gap) < footer_y:
            panel.text(
                "Tools:",
                pad,
                y,
                size=title_size,
                color=menu_title,
                bold=True,
                serif=True,
                max_width=width - 2 * pad,
            )
            y += title_size + 3
            half_width = (width - 2 * pad - gap) / 2
            for index, (label, callback) in enumerate(compact_actions):
                column = index % 2
                row = index // 2
                panel.button(
                    f"action:{label}",
                    (
                        pad + column * (half_width + gap),
                        y + row * (action_height + gap // 2),
                        half_width,
                        action_height - 2,
                    ),
                    label,
                    small_size,
                    button_fg,
                    button_bg,
                    callback,
                    hover_bg=button_hover,
                    outline=button_outline,
                )

        panel.text(
            "Created by Printzios Lampros.",
            width / 2,
            footer_y + footer_height / 2,
            size=small_size,
            color=menu_text,
            anchor="center",
            bold=True,
            serif=True,
            max_width=width - 2 * pad,
            max_lines=1,
        )
        panel.finish()

    def _menu_scale(self) -> float:
        width = max(float(self.menu_background_width), 1.0)
        height = max(float(self.menu_background_height), 1.0)
        return max(0.62, min(1.45, min(width / 380.0, height / 760.0)))

    def _menu_font_sizes(self) -> tuple[int, int, int]:
        scale = self._menu_scale()
        return (
            max(11, round(DEFAULT_MENUS_FONT * scale)),
            max(9, round(DEFAULT_OPTIONS_FONT * scale)),
            max(9, round(DEFAULT_BUTTONS_FONT * scale)),
        )

    def bind_events(self) -> None:
        self.cube_background.bind(
            "<Double-Button-2>", lambda event: self.reset_cube_position(event)
        )
        self.cube_background.bind(
            "<Button-2>", lambda event: self.cube_zoom_transfer_mouse_events(event)
        )
        self.cube_background.bind(
            "<B2-Motion>", lambda event: self.cube_zoom_transfer_mouse_events(event)
        )
        self.cube_background.bind(
            "<MouseWheel>", lambda event: self.cube_zoom_transfer_mouse_events(event)
        )
        self.cube_background.bind(
            "<Button-4>", lambda event: self.cube_zoom_transfer_mouse_events(event)
        )
        self.cube_background.bind(
            "<Button-5>", lambda event: self.cube_zoom_transfer_mouse_events(event)
        )
        self.cube_background.bind(
            "<ButtonRelease-1>", lambda event: self.cube_moves_mouse_events(None, event)
        )
        self.cube_background.bind(
            "<Button-3>", lambda event: self.cube_rotations_mouse_events(event)
        )
        self.cube_background.bind(
            "<ButtonRelease-3>", lambda event: self.cube_rotations_mouse_events(event)
        )
        for key, move in MOVE_KEY_BINDINGS:
            self.root.bind(
                f"<Key-{key}>",
                lambda event, m=move: self.make_moves_sequence(self.rubiks_cube, [m], True, event),
            )
        for sequence, move in SPECIAL_MOVE_KEY_BINDINGS:
            self.root.bind(
                sequence,
                lambda event, m=move: self.make_moves_sequence(self.rubiks_cube, [m], True, event),
            )
        for key, move in VIEW_KEY_BINDINGS:
            self.root.bind(
                f"<Key-{key}>",
                lambda event, m=move: self.change_cube_view(self.rubiks_cube, m, event),
            )
        self.root.bind("<Key-5>", lambda event: self.reset_cube_view(event))
        self.root.bind(
            "<Key-1>", lambda event: self.show_previous_next_solve_move("previous", event)
        )
        self.root.bind("<Key-3>", lambda event: self.show_previous_next_solve_move("next", event))
        self.root.bind("<Key-0>", lambda event: self.show_previous_next_solve_move("start", event))
        self.root.bind(
            "<Double-Key-0>", lambda event: self.show_previous_next_solve_move("end", event)
        )

    def cube_size_label(self) -> str:
        return f"{self.cube_size}x{self.cube_size}x{self.cube_size}"

    def change_cube_size(self, event: tk.Event | None = None) -> None:
        size = simpledialog.askinteger(
            "Cube size",
            f"Enter a cube size from {MIN_CUBE_SIZE} to {MAX_CUBE_SIZE}:",
            parent=self.root,
            initialvalue=self.cube_size,
            minvalue=MIN_CUBE_SIZE,
            maxvalue=MAX_CUBE_SIZE,
        )
        if size is None or size == self.cube_size:
            return
        self.animation.cancel()
        self._cancel_pending_graphics()
        self.buttons_bindings_are_activated = True
        self.cube_size = size
        self.piece_side_length = piece_side_length_for_size(size)
        self.create_menus()
        self.reset_game()

    def change_game_setting(self, setting: str) -> None:
        if setting == "scramble_moves_speed":
            self.scramble_moves_speed = self.alternate_matrix_elements(
                MOVE_SPEEDS, self.scramble_moves_speed
            )
            if self.game_state == "moves_scramble":
                self.moves_speed = self.scramble_moves_speed
        elif setting == "random_scramble_moves":
            self.random_scramble_moves = self.alternate_matrix_elements(
                RANDOM_SCRAMBLE_MOVE_COUNTS, self.random_scramble_moves
            )
        elif setting == "scramble_pattern_visibility":
            self.scramble_pattern_visibility = self.alternate_matrix_elements(
                ["on", "off"], self.scramble_pattern_visibility
            )
        elif setting == "solve_moves_speed":
            self.solve_moves_speed = self.alternate_matrix_elements(
                MOVE_SPEEDS, self.solve_moves_speed
            )
            if self.game_state == "auto_solve":
                self.moves_speed = self.solve_moves_speed
        elif setting == "cube_dimensions":
            self.cube_dimensions = self.alternate_matrix_elements(
                CUBE_DIMENSIONS, self.cube_dimensions
            )
            minimum, maximum = piece_side_length_limits(self.cube_size)
            if self.cube_dimensions == "3d":
                self.piece_side_length = min(maximum, 2 * self.piece_side_length)
            elif self.cube_dimensions == "2d":
                self.piece_side_length = max(minimum, 1 / 2 * self.piece_side_length)
        elif setting == "sides_distortion":
            self.sides_distortion = self.alternate_matrix_elements(
                SIDES_DISTORTIONS, self.sides_distortion
            )
        elif setting == "borders_width":
            self.borders_width = self.alternate_matrix_elements(BORDERS_WIDTHS, self.borders_width)
        elif setting == "hidden_sides_visibility":
            self.hidden_sides_visibility = self.alternate_matrix_elements(
                ["on", "off"], self.hidden_sides_visibility
            )
        elif setting == "axis_visibility":
            self.axis_visibility = self.alternate_matrix_elements(
                ["on", "off"], self.axis_visibility
            )
        self.create_menus()
        self.make_cube_graphics(self.rubiks_cube, None)

    def enable_disable_sound(self) -> None:
        self.sound_is_activated = not self.sound_is_activated
        self.create_menus()

    def show_instructions(self, event: tk.Event | None = None) -> None:
        try:
            self.instructions_background.destroy()
        except AttributeError:
            pass

        width = self.right_paned.winfo_width()
        height = self.right_paned.winfo_height()
        if width <= 1:
            width = int(self.cube_background_width)
        if height <= 1:
            height = int(self.cube_background_height + self.down_area_background_height)

        self.instructions_background = tk.Canvas(
            self.right_paned,
            width=width,
            height=height,
            bg="yellow",
            highlightthickness=0,
        )
        self.instructions_background.place(x=0, y=0, relwidth=1, relheight=1)
        tk.Misc.tkraise(self.instructions_background)
        self.instructions_background.create_text(
            width / 2,
            max(25, int(height * 0.05)),
            text="Cube notation",
            font="Arial 30 bold italic",
            fill="darkblue",
        )
        self.cube_notation_picture = Image.open(NOTATION_IMAGE_PATH)
        reduction_factor = 0.75
        picture_width = max(1, int(reduction_factor * width))
        self.cube_notation_picture = self.cube_notation_picture.resize(
            (
                picture_width,
                max(
                    1,
                    int(
                        picture_width
                        * self.cube_notation_picture.height
                        / self.cube_notation_picture.width
                    ),
                ),
            ),
            Image.LANCZOS,
        )
        self.cube_notation_picture = ImageTk.PhotoImage(self.cube_notation_picture)
        self.instructions_background.create_image(
            width / 2,
            self.cube_notation_picture.height() / 2 + 80,
            image=self.cube_notation_picture,
        )
        self.instructions_background.create_text(
            20,
            self.cube_notation_picture.height() + 120,
            text=texts.CUBE_NOTATION_TEXT,
            font="Calibri 15 bold",
            fill="darkblue",
            anchor=tk.NW,
            width=max(100, width - 40),
        )
        self.back_button = self._button(
            self.instructions_background,
            "back",
            "Calibri 25 bold",
            "black",
            "yellow",
            width / 2,
            height - 40,
            self.hide_instructions,
        )

    def hide_instructions(self, event: tk.Event | None = None) -> None:
        self.instructions_background.destroy()
