"""Menu construction and menu-related event handlers."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageTk

from .. import texts
from ..config import (
    BORDERS_WIDTHS,
    CUBE_DIMENSIONS,
    DEFAULT_BUTTONS_FONT,
    DEFAULT_MENUS_FONT,
    DEFAULT_OPTIONS_FONT,
    MOVE_KEY_BINDINGS,
    MOVE_SPEEDS,
    NOTATION_IMAGE_PATH,
    RANDOM_SCRAMBLE_MOVE_COUNTS,
    SIDES_DISTORTIONS,
    SPECIAL_MOVE_KEY_BINDINGS,
    VIEW_KEY_BINDINGS,
)


class MenusMixin:
    def create_menus(self) -> None:
        for child in self.menu_background.winfo_children():
            child.destroy()

        scale = self._menu_scale()
        pad = max(3, int(7 * scale))
        title_font = f"Times {self.menus_font} bold"
        option_font = f"Arial {self.options_font} bold"
        button_font = f"Arial {self.buttons_font} bold"

        footer = self._menu_label(
            self.menu_background,
            "Created by Printzios Lampros.",
            f"Times {max(9, self.options_font - 2)} bold",
            "white",
            "black",
        )
        footer.configure(wraplength=max(120, int(self.menu_background_width - 2 * pad)))
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=max(2, pad // 2))

        content = tk.Frame(self.menu_background, bg="black")
        content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=pad, pady=pad)

        header = tk.Frame(content, bg="black")
        header.pack(fill=tk.X, pady=(0, pad))
        self.reset_button = self._menu_button(
            header, "reset", button_font, "white", "black", self.reset_game
        )
        self.reset_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, pad // 2))
        self.show_instructions_button = self._menu_button(
            header, "ⓘ", button_font, "white", "black", self.show_instructions
        )
        self.show_instructions_button.pack(side=tk.LEFT, padx=(0, pad // 2))
        self.sound_button = self._menu_button(
            header, "🔊", button_font, "white", "black", self.enable_disable_sound
        )
        self.sound_button.pack(side=tk.LEFT)

        cube_graphics = self._add_menu_section(content, "Cube graphics:", title_font, pad)
        self.borders_width_button = self._add_menu_setting(
            cube_graphics,
            0,
            "borders width:",
            self.borders_width,
            self.change_game_settings_cube_graphics,
            option_font,
            button_font,
            pad,
        )
        self.sides_distortion_button = self._add_menu_setting(
            cube_graphics,
            1,
            "sides distortion:",
            self.sides_distortion,
            self.change_game_settings_cube_graphics,
            option_font,
            button_font,
            pad,
        )
        self.hidden_sides_visibility_button = self._add_menu_setting(
            cube_graphics,
            2,
            "hidden sides:",
            self.hidden_sides_visibility,
            self.change_game_settings_cube_graphics,
            option_font,
            button_font,
            pad,
        )
        self.axis_visibility_button = self._add_menu_setting(
            cube_graphics,
            3,
            "3d axis:",
            self.axis_visibility,
            self.change_game_settings_cube_graphics,
            option_font,
            button_font,
            pad,
        )
        self.scramble_pattern_visibility_button = self._add_menu_setting(
            cube_graphics,
            4,
            "scramble pattern:",
            self.scramble_pattern_visibility,
            self.change_game_settings_cube_graphics,
            option_font,
            button_font,
            pad,
        )
        self.cube_dimensions_button = self._add_menu_setting(
            cube_graphics,
            5,
            "dimensions:",
            self.cube_dimensions,
            self.change_game_settings_cube_graphics,
            option_font,
            button_font,
            pad,
        )

        self._add_menu_separator(content, pad)

        scramble_cube = self._add_menu_section(content, "Scramble cube:", title_font, pad)
        self.scramble_moves_speed_button = self._add_menu_setting(
            scramble_cube,
            0,
            "time/move (sec):",
            self.scramble_moves_speed,
            self.change_game_settings_cube_graphics,
            option_font,
            button_font,
            pad,
        )
        self.moves_number_button = self._add_menu_setting(
            scramble_cube,
            1,
            "moves number:",
            self.random_scramble_moves,
            self.change_game_settings_cube_graphics,
            option_font,
            button_font,
            pad,
        )
        self.scramble_cube_button = self._add_menu_action(
            scramble_cube, 2, "random scramble", self.moves_scramble_cube, button_font, pad
        )
        self.draw_scramble_pattern_button = self._add_menu_action(
            scramble_cube, 3, "draw pattern", self.draw_scramble_cube, button_font, pad
        )

        self._add_menu_separator(content, pad)

        solve_cube = self._add_menu_section(content, "Solve cube:", title_font, pad)
        self.solve_moves_speed_button = self._add_menu_setting(
            solve_cube,
            0,
            "time/move (sec):",
            self.solve_moves_speed,
            self.change_game_settings_cube_graphics,
            option_font,
            button_font,
            pad,
        )
        self.auto_solve_cube_button = self._add_menu_action(
            solve_cube,
            1,
            "solve",
            lambda event: self.auto_solve_cube("choose_method", None, None, event),
            button_font,
            pad,
        )

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

    def _add_menu_section(self, parent: tk.Misc, title: str, title_font: str, pad: int) -> tk.Frame:
        section = tk.Frame(parent, bg="black")
        section.pack(fill=tk.X, pady=(0, pad))

        title_label = self._menu_label(section, title, title_font, "yellow", "black")
        title_label.pack(anchor="w")

        grid = tk.Frame(section, bg="black")
        grid.pack(fill=tk.X, pady=(max(2, pad // 2), 0))
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=0)
        return grid

    def _add_menu_setting(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        value: str | int | float,
        callback: Callable[[tk.Event], None],
        label_font: str,
        button_font: str,
        pad: int,
    ) -> tk.Label:
        label_widget = self._menu_label(parent, label, label_font, "red", "black")
        label_widget.grid(row=row, column=0, sticky="w", pady=max(1, pad // 2))

        button = self._menu_button(parent, value, button_font, "white", "black", callback)
        button.grid(
            row=row,
            column=1,
            sticky="e",
            padx=(pad, 0),
            pady=max(1, pad // 2),
        )
        return button

    def _add_menu_action(
        self,
        parent: tk.Frame,
        row: int,
        text: str,
        callback: Callable[[tk.Event], None],
        button_font: str,
        pad: int,
    ) -> tk.Label:
        button = self._menu_button(parent, text, button_font, "white", "black", callback)
        button.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(max(2, pad // 2), 0),
        )
        return button

    def _add_menu_separator(self, parent: tk.Misc, pad: int) -> None:
        separator = tk.Frame(parent, bg="#555555", height=1)
        separator.pack(fill=tk.X, pady=(0, pad))

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

    def change_game_settings_cube_graphics(self, event: tk.Event) -> None:
        if event.widget == self.scramble_moves_speed_button:
            self.scramble_moves_speed = self.alternate_matrix_elements(
                MOVE_SPEEDS, self.scramble_moves_speed
            )
            self.scramble_moves_speed_button.configure(text=self.scramble_moves_speed)
            if self.game_state == "moves_scramble":
                self.moves_speed = self.scramble_moves_speed
        elif event.widget == self.moves_number_button:
            self.random_scramble_moves = self.alternate_matrix_elements(
                RANDOM_SCRAMBLE_MOVE_COUNTS, self.random_scramble_moves
            )
            self.moves_number_button.configure(text=self.random_scramble_moves)
        elif event.widget == self.scramble_pattern_visibility_button:
            self.scramble_pattern_visibility = self.alternate_matrix_elements(
                ["on", "off"], self.scramble_pattern_visibility
            )
            self.scramble_pattern_visibility_button.configure(text=self.scramble_pattern_visibility)
        elif event.widget == self.solve_moves_speed_button:
            self.solve_moves_speed = self.alternate_matrix_elements(
                MOVE_SPEEDS, self.solve_moves_speed
            )
            self.solve_moves_speed_button.configure(text=self.solve_moves_speed)
            if self.game_state == "auto_solve":
                self.moves_speed = self.solve_moves_speed
        elif event.widget == self.cube_dimensions_button:
            self.cube_dimensions = self.alternate_matrix_elements(
                CUBE_DIMENSIONS, self.cube_dimensions
            )
            self.cube_dimensions_button.configure(text=self.cube_dimensions)
            if self.cube_dimensions == "3d":
                self.piece_side_length = min(200, 2 * self.piece_side_length)
            elif self.cube_dimensions == "2d":
                self.piece_side_length = max(10, 1 / 2 * self.piece_side_length)
        elif event.widget == self.sides_distortion_button:
            self.sides_distortion = self.alternate_matrix_elements(
                SIDES_DISTORTIONS, self.sides_distortion
            )
            self.sides_distortion_button.configure(text=self.sides_distortion)
        elif event.widget == self.borders_width_button:
            self.borders_width = self.alternate_matrix_elements(BORDERS_WIDTHS, self.borders_width)
            self.borders_width_button.configure(text=self.borders_width)
        elif event.widget == self.hidden_sides_visibility_button:
            self.hidden_sides_visibility = self.alternate_matrix_elements(
                ["on", "off"], self.hidden_sides_visibility
            )
            self.hidden_sides_visibility_button.configure(text=self.hidden_sides_visibility)
        elif event.widget == self.axis_visibility_button:
            self.axis_visibility = self.alternate_matrix_elements(
                ["on", "off"], self.axis_visibility
            )
            self.axis_visibility_button.configure(text=self.axis_visibility)
        self.make_cube_graphics(self.rubiks_cube, None)

    def enable_disable_sound(self, event: tk.Event) -> None:
        if self.sound_is_activated:
            self.sound_button.configure(text="🔇")
        else:
            self.sound_button.configure(text="🔊")
        self.sound_is_activated = not self.sound_is_activated

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
