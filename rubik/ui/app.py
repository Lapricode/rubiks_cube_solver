"""Main application: state, game flow and event handling."""

from __future__ import annotations

import random
import time
import tkinter as tk
import traceback
from collections.abc import Sequence
from typing import TypeVar

import pygame

from .. import texts
from ..config import (
    BORDERS_WIDTHS,
    COLOR_NAMES,
    CUBE_DIMENSIONS,
    CUBE_SIZES,
    DEFAULT_BUTTONS_FONT,
    DEFAULT_CUBE_SIZE,
    DEFAULT_MENUS_FONT,
    DEFAULT_OPTIONS_FONT,
    ICON_PATH,
    MAX_SCRAMBLE_MOVES,
    MOVE_SPEEDS,
    RANDOM_SCRAMBLE_MOVE_COUNTS,
    SIDES_DISTORTIONS,
    SOUNDS_DIR,
)
from ..cube import (
    Cube,
    InvalidCubeError,
    Move,
    apply_move,
    blank_cube,
    copy_cube,
    cube_signature,
    improve_moves_sequence,
    is_solved,
    solved_cube,
)
from ..solver_2x2 import solve_2x2
from ..solvers import (
    SolverFailedError,
    SolverLibraryNotInstalledError,
    solve_beginner,
    solve_external,
)
from .animation import AnimationController, ReplayController
from .graphics import CubeGraphicsMixin
from .menus import MenusMixin
from .widgets import WidgetFactoryMixin

T = TypeVar("T")


class RubiksCubeApp(WidgetFactoryMixin, MenusMixin, CubeGraphicsMixin):
    def __init__(self, root: tk.Tk) -> None:
        pygame.init()
        self.root = root
        self.root.title("Rubik's cube")
        self.root.iconphoto(True, tk.PhotoImage(file=str(ICON_PATH)))

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = max(900, min(screen_width - 80, int(screen_width * 0.9)))
        window_height = max(640, min(screen_height - 80, int(screen_height * 0.85)))
        self.root.geometry(f"{window_width}x{window_height}+0+0")
        self.root.minsize(720, 520)

        sash_width = 8
        self.menu_background_width = max(280, min(430, int(window_width * 0.24)))
        self.cube_background_width = window_width - self.menu_background_width - sash_width
        self.cube_background_height = max(300, int(window_height * 0.7))
        self.down_area_background_width = self.cube_background_width
        self.down_area_background_height = max(
            150, window_height - self.cube_background_height - sash_width
        )
        self.menu_background_height = window_height

        self.main_paned = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            sashwidth=sash_width,
            sashrelief=tk.RAISED,
            bg="#404040",
            bd=0,
        )
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        self.menu_background = tk.Frame(self.main_paned, bg="black", bd=0)
        self.right_paned = tk.PanedWindow(
            self.main_paned,
            orient=tk.VERTICAL,
            sashwidth=sash_width,
            sashrelief=tk.RAISED,
            bg="#404040",
            bd=0,
        )
        self.cube_background = tk.Canvas(
            self.right_paned,
            width=self.cube_background_width,
            height=self.cube_background_height,
            bg="cyan",
            bd=0,
            relief="solid",
            highlightthickness=0,
        )
        self.down_area_background = tk.Canvas(
            self.right_paned,
            width=self.down_area_background_width,
            height=self.down_area_background_height,
            bg="yellow",
            bd=0,
            relief="solid",
            highlightthickness=0,
        )
        self.main_paned.add(
            self.menu_background,
            minsize=240,
            width=self.menu_background_width,
            stretch="never",
        )
        self.main_paned.add(self.right_paned, minsize=480, stretch="always")
        self.right_paned.add(
            self.cube_background,
            minsize=180,
            height=self.cube_background_height,
            stretch="always",
        )
        self.right_paned.add(
            self.down_area_background,
            minsize=110,
            height=self.down_area_background_height,
            stretch="never",
        )

        # Variables for visible cube.
        self.cube_colors = COLOR_NAMES[:]
        self.cube_size = DEFAULT_CUBE_SIZE
        self.cube_sizes_matrix = CUBE_SIZES
        self.cube_dimensions = "3d"
        self.cube_dimensions_matrix = CUBE_DIMENSIONS
        self.piece_side_length = 150 if self.cube_size == 2 else 100
        self.borders_width = 1
        self.borders_widths_matrix = BORDERS_WIDTHS
        self.sides_distortion = 0.6
        self.sides_distortions_matrix = SIDES_DISTORTIONS
        self.hidden_sides_visibility = "on"
        self.axis_visibility = "on"
        self.scramble_pattern_visibility = "on"
        self.scrambled_pattern_centre_x = self.cube_background_width - 100
        self.scrambled_pattern_centre_y = 80
        self.visible_cube_centre_x = self.cube_background_width / 2
        self.visible_cube_centre_y = self.cube_background_height / 2

        # Variables for hidden sides.
        self.hidden_cube_centre_x = 60
        self.hidden_cube_centre_y = 80
        self.hidden_side_length = 20

        # Variables for scramble moves.
        self.scramble_moves_speed = 0.0
        self.moves_speeds_matrix = MOVE_SPEEDS
        self.random_scramble_moves = 10
        self.random_scramble_moves_matrix = RANDOM_SCRAMBLE_MOVE_COUNTS
        self.max_scramble_moves = MAX_SCRAMBLE_MOVES

        # Variables for draw scramble.
        self.chosen_draw_color = "blue"

        # Variables for solve.
        self.solve_moves_speed = 0.0

        # Variables for instructions and guidelines.
        self.cube_notation_text = texts.CUBE_NOTATION_TEXT
        self.reset_text = texts.RESET_TEXT
        self.moves_scramble_text = texts.MOVES_SCRAMBLE_TEXT.format(
            max_moves=self.max_scramble_moves
        )
        self.draw_scramble_text = texts.DRAW_SCRAMBLE_TEXT
        self.cube_is_solved_text = texts.CUBE_IS_SOLVED_TEXT
        self.wrong_pattern_text = texts.WRONG_PATTERN_TEXT
        self.replay_moves_text = texts.REPLAY_MOVES_TEXT

        # Other variables.
        self.game_state = "moves_scramble"
        self.previous_game_state = "moves_scramble"
        self.mouse_move_info = None
        self.animation = AnimationController(self.root)
        self.replay = ReplayController()
        self._solved_cache: dict[tuple[str, ...], bool] = {}
        self._last_solved_sound_signature: tuple[str, ...] | None = None
        self._pending_graphics: tuple[Cube, str | None] | None = None
        self._pending_graphics_id: str | None = None
        self.sound_is_activated = True
        self.default_menus_font = DEFAULT_MENUS_FONT
        self.menus_font = self.default_menus_font
        self.default_options_font = DEFAULT_OPTIONS_FONT
        self.options_font = self.default_options_font
        self.default_buttons_font = DEFAULT_BUTTONS_FONT
        self.buttons_font = self.default_buttons_font
        self._menu_rebuild_id: str | None = None
        self._cube_center_initialized = False
        self.buttons_bindings_are_activated = True
        self.moves_bindings_are_activated = True

        self.create_menus()
        self.reset_game()
        self.bind_events()
        self.menu_background.bind("<Configure>", self._on_menu_configure)
        self.cube_background.bind("<Configure>", self._on_cube_configure)
        self.down_area_background.bind("<Configure>", self._on_down_area_configure)

    def alternate_matrix_elements(self, matrix: list[T], index_element: T) -> T:
        return (matrix[1:] + [matrix[0]])[matrix.index(index_element)]

    def play_sound(self, sound_file: str, sound_type: str) -> None:
        if not self.sound_is_activated:
            return
        if sound_type == "music":
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.load(str(SOUNDS_DIR / f"{sound_file}.mp3"))
            pygame.mixer.music.play(-1)
        elif sound_type == "sound":
            self.sound = pygame.mixer.Sound(str(SOUNDS_DIR / f"{sound_file}.wav"))
            self.sound.play()

    def _on_menu_configure(self, event: tk.Event) -> None:
        if event.widget is not self.menu_background or event.width <= 1 or event.height <= 1:
            return
        self.menu_background_width = float(event.width)
        self.menu_background_height = float(event.height)
        font_sizes = self._menu_font_sizes()
        if font_sizes != (self.menus_font, self.options_font, self.buttons_font):
            self.menus_font, self.options_font, self.buttons_font = font_sizes
            self._schedule_menu_rebuild()

    def _schedule_menu_rebuild(self) -> None:
        if self._menu_rebuild_id is None:
            self._menu_rebuild_id = self.root.after_idle(self._rebuild_menu)

    def _rebuild_menu(self) -> None:
        self._menu_rebuild_id = None
        self.create_menus()

    def _on_cube_configure(self, event: tk.Event) -> None:
        if event.widget is not self.cube_background or event.width <= 1 or event.height <= 1:
            return
        new_width = float(event.width)
        new_height = float(event.height)
        old_width = self.cube_background_width
        old_height = self.cube_background_height

        if not self._cube_center_initialized or old_width <= 1 or old_height <= 1:
            self.visible_cube_centre_x = new_width / 2
            self.visible_cube_centre_y = new_height / 2
            self._cube_center_initialized = True
        else:
            scale = min(new_width / old_width, new_height / old_height)
            self.piece_side_length = max(10.0, min(200.0, self.piece_side_length * scale))
            self.visible_cube_centre_x += (new_width - old_width) / 2
            self.visible_cube_centre_y += (new_height - old_height) / 2

        self.cube_background_width = new_width
        self.cube_background_height = new_height
        self.scrambled_pattern_centre_x = max(80.0, new_width - 100)
        if hasattr(self, "rubiks_cube"):
            self.request_cube_graphics(self.rubiks_cube, None)

    def _on_down_area_configure(self, event: tk.Event) -> None:
        if event.widget is not self.down_area_background or event.width <= 1 or event.height <= 1:
            return
        new_width = float(event.width)
        new_height = float(event.height)
        old_width = self.down_area_background_width
        old_height = self.down_area_background_height

        if (
            old_width > 1
            and old_height > 1
            and (abs(new_width - old_width) > 1 or abs(new_height - old_height) > 1)
        ):
            scale_x = new_width / old_width
            scale_y = new_height / old_height
            self.down_area_background.scale("all", 0, 0, scale_x, scale_y)
            for child in self.down_area_background.winfo_children():
                info = child.place_info()
                if not info:
                    continue
                try:
                    x = float(info.get("x", "0") or "0")
                    y = float(info.get("y", "0") or "0")
                except ValueError:
                    continue
                child.place_configure(x=x * scale_x, y=y * scale_y)

        self.down_area_background_width = new_width
        self.down_area_background_height = new_height

    def reset_game(self, event: tk.Event | None = None) -> None:
        if self.buttons_bindings_are_activated:
            self.animation.cancel()
            self._cancel_pending_graphics()
            self.buttons_bindings_are_activated = True
            self.moves_bindings_are_activated = True
            self.replay.reset()
            self.destroy_down_area_buttons()
            self.game_state = "moves_scramble"
            self.previous_game_state = "moves_scramble"
            self.down_area_background.delete("all")
            self.down_area_background.create_text(
                self.down_area_background_width / 2,
                self.down_area_background_height / 2,
                text=self.reset_text,
                font="Arial 12 bold",
                fill="brown",
            )
            self.rubiks_cube = solved_cube(self.cube_size)
            self.moves_scrambled_rubiks_cube = copy_cube(self.rubiks_cube)
            self.draw_scrambled_rubiks_cube = blank_cube("c", self.cube_size)
            self.random_scramble_moves_seq = []
            self.self_solve_moves_seq = []
            self.auto_solve_moves_seq = []
            self.adjust_cube_view_moves = []
            self.moves_speed = self.scramble_moves_speed
            self.reset_cube_view()

    def moves_scramble_cube(self, event: tk.Event | None = None) -> None:
        if self.buttons_bindings_are_activated:
            self.animation.cancel()
            self._cancel_pending_graphics()
            self.buttons_bindings_are_activated = False
            self.moves_bindings_are_activated = False
            self.replay.reset()
            self.previous_game_state = self.game_state
            self.game_state = "moves_scramble"
            self.moves_speed = self.scramble_moves_speed
            scramble_moves_before = len(self.random_scramble_moves_seq)
            if event is not None:
                while (
                    len(self.random_scramble_moves_seq) < self.max_scramble_moves
                    and len(self.random_scramble_moves_seq)
                    != scramble_moves_before + self.random_scramble_moves
                ):
                    self.random_scramble_moves_seq.append(
                        random.choice(
                            [
                                "L",
                                "L'",
                                "R",
                                "R'",
                                "U",
                                "U'",
                                "D",
                                "D'",
                                "F",
                                "F'",
                                "B",
                                "B'",
                            ]
                            + (["M", "M'", "E", "E'", "S", "S'"] if self.cube_size == 3 else [])
                        )
                    )
                    self.random_scramble_moves_seq = improve_moves_sequence(
                        self.random_scramble_moves_seq
                    )
            self.write_moves_scramble_text()
            self.rubiks_cube = solved_cube(self.cube_size)
            self.make_moves_sequence(self.rubiks_cube, [""] + self.random_scramble_moves_seq, True)

    def write_moves_scramble_text(self) -> None:
        self.destroy_down_area_buttons()
        self.self_solve_try_yourself_button = self._button(
            self.down_area_background,
            "try yourself",
            "Arial 10 bold",
            "red",
            "yellow",
            self.down_area_background_width / 2,
            self.down_area_background_height - 15,
            self.self_solve_cube,
        )
        self.down_area_background.delete("all")
        self.down_area_background.create_text(
            self.down_area_background_width / 2,
            20,
            text=f"Scramble ({len(self.random_scramble_moves_seq)} moves in total):",
            font="Calibri 18 bold",
            fill="black",
        )
        row_chars = 35
        for index1 in range(len(self.random_scramble_moves_seq) // row_chars + 1):
            index2 = [len(self.random_scramble_moves_seq), row_chars * index1 + row_chars][
                [True, False].index(len(self.random_scramble_moves_seq) // row_chars == 0)
            ]
            self.down_area_background.create_text(
                self.down_area_background_width / 2,
                50 + 20 * index1,
                text=self.random_scramble_moves_seq[(row_chars * index1) : index2],
                font="Arial 14 italic bold",
                fill="darkblue",
            )
        self.down_area_background.create_text(
            self.down_area_background_width / 2,
            self.down_area_background_height - 40,
            text=self.moves_scramble_text,
            font="Arial 10 bold",
            fill="brown",
        )

    def draw_scramble_cube(self, event: tk.Event | None = None) -> None:
        if self.buttons_bindings_are_activated:
            self.animation.cancel()
            self._cancel_pending_graphics()
            self.destroy_down_area_buttons()
            self.buttons_bindings_are_activated = True
            self.moves_bindings_are_activated = False
            self.replay.reset()
            self.previous_game_state = self.game_state
            self.game_state = "draw_scramble"
            self.rubiks_cube = copy_cube(self.draw_scrambled_rubiks_cube)
            self.down_area_background.delete("all")
            self.down_area_background.create_text(
                self.down_area_background_width / 2,
                40,
                text=self.draw_scramble_text,
                font="Arial 14 bold",
                fill="brown",
            )
            rect_side = 70
            edge_offset = 150
            centre_x_offset = (
                (self.down_area_background_width - 2 * edge_offset) - 6 * rect_side
            ) / 10
            centre_y_offset = 30
            rect_x_offset = -80
            for k in range(6):
                self.down_area_background.create_rectangle(
                    [
                        edge_offset + (rect_side + 2 * centre_x_offset) * k + rect_x_offset,
                        self.down_area_background_height / 2 - rect_side / 2 + centre_y_offset,
                        edge_offset
                        + (rect_side + 2 * centre_x_offset) * k
                        + rect_side
                        + rect_x_offset,
                        self.down_area_background_height / 2 + rect_side / 2 + centre_y_offset,
                    ],
                    fill=self.cube_colors[k],
                    activefill="black",
                    width=5,
                    outline="black",
                    tags=self.cube_colors[k],
                )
            for color in self.cube_colors:
                self.down_area_background.tag_bind(
                    color, "<Button-1>", lambda event, c=color: self.change_draw_color(c, event)
                )
            self.clear_cube_draw_button = self._button(
                self.down_area_background,
                "clear cube",
                "Arial 12 bold",
                "red",
                "yellow",
                self.down_area_background_width - 110,
                self.down_area_background_height / 2 + centre_y_offset - 15,
                self.clear_fill_cube_draw,
            )
            self.fill_cube_draw_button = self._button(
                self.down_area_background,
                "fill cube",
                "Arial 12 bold",
                "red",
                "yellow",
                self.down_area_background_width - 110,
                self.down_area_background_height / 2 + centre_y_offset + 15,
                self.clear_fill_cube_draw,
            )
            self.change_draw_color(self.chosen_draw_color)
            self.make_cube_graphics(self.rubiks_cube, None)

    def clear_fill_cube_draw(self, event: tk.Event) -> None:
        if event.widget == self.clear_cube_draw_button:
            self.draw_scrambled_rubiks_cube = blank_cube("c", self.cube_size)
        elif event.widget == self.fill_cube_draw_button:
            self.draw_scrambled_rubiks_cube = solved_cube(self.cube_size)
        self.rubiks_cube = copy_cube(self.draw_scrambled_rubiks_cube)
        self.make_cube_graphics(self.rubiks_cube, None)

    def change_draw_color(self, color_chosen: str, event: tk.Event | None = None) -> None:
        self.chosen_draw_color = color_chosen
        for color in self.cube_colors:
            color_box = self.down_area_background.find_withtag(color)
            self.down_area_background.itemconfigure(color_box, width=5)
        if event is None:
            color_box = self.down_area_background.find_withtag(self.chosen_draw_color)
        else:
            color_box = event.widget.find_closest(event.x, event.y)
        self.down_area_background.itemconfigure(color_box, width=10)
        self.make_cube_graphics(self.rubiks_cube, None)

    def same_scramble_cube(self, event: tk.Event) -> None:
        if self.buttons_bindings_are_activated:
            self.destroy_down_area_buttons()
            if self.previous_game_state in ["moves_scramble", "self_solve"]:
                self.moves_scramble_cube()
            elif self.previous_game_state == "draw_scramble":
                self.draw_scramble_cube()

    def _add_replay_buttons(self) -> None:
        self.go_to_replay_previous_move_button = self._button(
            self.down_area_background,
            "🡄",
            "Arial 14 bold",
            "blue",
            "yellow",
            80,
            20,
            lambda event: self.show_previous_next_solve_move("previous", event),
        )
        self.go_to_replay_next_move_button = self._button(
            self.down_area_background,
            "🡆",
            "Arial 14 bold",
            "blue",
            "yellow",
            130,
            20,
            lambda event: self.show_previous_next_solve_move("next", event),
        )
        self.go_to_replay_start_button = self._button(
            self.down_area_background,
            "⏮",
            "Arial 14 bold",
            "blue",
            "yellow",
            30,
            20,
            lambda event: self.show_previous_next_solve_move("start", event),
        )
        self.go_to_replay_end_button = self._button(
            self.down_area_background,
            "⏭",
            "Arial 14 bold",
            "blue",
            "yellow",
            180,
            20,
            lambda event: self.show_previous_next_solve_move("end", event),
        )

    def self_solve_cube(self, event: tk.Event) -> None:
        if self.buttons_bindings_are_activated:
            self.animation.cancel()
            self._cancel_pending_graphics()
            self.destroy_down_area_buttons()
            self._add_replay_buttons()
            self.self_solve_try_again_button = self._button(
                self.down_area_background,
                "try again",
                "Arial 10 bold",
                "red",
                "yellow",
                self.down_area_background_width - 80,
                20,
                self.self_solve_cube,
            )
            self.previous_game_state = self.game_state
            self.game_state = "self_solve"
            self.buttons_bindings_are_activated = True
            self.moves_bindings_are_activated = True
            self.replay.reset()
            self.self_solve_moves_seq = []
            self.start_timer_self_solving = time.time()
            self.down_area_background.delete("all")
            self.down_area_background.create_text(
                self.down_area_background_width / 2,
                self.down_area_background_height / 2,
                text="Clock just started ticking!",
                font="Calibri 20 bold",
                fill="purple",
            )
            self.down_area_background.create_text(
                self.down_area_background_width / 2,
                20,
                text=f"Self solve ({len(self.self_solve_moves_seq)} moves in total):",
                font="Calibri 18 bold",
                fill="black",
            )
            self.rubiks_cube = copy_cube(self.moves_scrambled_rubiks_cube)
            self.make_cube_graphics(self.rubiks_cube, None)

    def _display_stages(
        self,
        stage_moves: Sequence[Sequence[Move]],
        notes: Sequence[str],
        row_chars: int,
        text_x: float,
    ) -> None:
        self.down_area_background.delete("all")
        line_offset = 0
        for k in range(len(stage_moves)):
            moves = stage_moves[k]
            self.down_area_background.create_text(
                10,
                40 + 15 * (k + line_offset),
                text=notes[k] + f" ({len(moves)} moves):",
                font="Arial 10 bold",
                fill="purple",
                anchor=tk.NW,
            )
            for index1 in range(len(moves) // row_chars + 1):
                index2 = [len(moves), row_chars * index1 + row_chars][
                    [True, False].index(len(moves) // row_chars == 0)
                ]
                self.down_area_background.create_text(
                    text_x,
                    40 + 15 * (k + index1 + line_offset),
                    text=moves[(row_chars * index1) : index2],
                    font="Arial 10 italic bold",
                    fill="darkblue",
                    anchor=tk.NW,
                )
            if len(moves) // row_chars != 0:
                line_offset += 1

    def auto_solve_cube(
        self,
        solve_mode_stage: str,
        solve_method_choose: str | None,
        start_color_choose: str | None,
        event: tk.Event | None,
    ) -> None:
        if solve_mode_stage == "choose_method":
            if self.buttons_bindings_are_activated and self.game_state not in [
                "self_solve",
                "auto_solve",
            ]:
                self.destroy_down_area_buttons()
                self.down_area_background.delete("all")
                self.moves_bindings_are_activated = False
                self.replay.active = False
                if self.cube_is_solved(self.rubiks_cube):
                    if self.game_state != "auto_solve":
                        self.previous_game_state = self.game_state
                    self.down_area_background.create_text(
                        self.down_area_background_width / 2,
                        40,
                        text="The cube is already solved!",
                        font="Arial " + str(self.buttons_font) + " bold",
                        fill="brown",
                    )
                    self.down_area_background.create_text(
                        self.down_area_background_width / 2,
                        90,
                        text=self.cube_is_solved_text,
                        font="Arial 14 bold",
                        fill="brown",
                    )
                    self.down_area_background.create_text(
                        90,
                        self.down_area_background_height - 45,
                        text="Scramble:",
                        font="Arial 8 bold",
                        fill="black",
                        anchor=tk.NW,
                    )
                    if (
                        self.previous_game_state == "moves_scramble"
                        or self.previous_game_state == "self_solve"
                    ):
                        row_chars = 25
                        for index1 in range(len(self.random_scramble_moves_seq) // row_chars + 1):
                            index2 = [
                                len(self.random_scramble_moves_seq),
                                row_chars * index1 + row_chars,
                            ][
                                [True, False].index(
                                    len(self.random_scramble_moves_seq) // row_chars == 0
                                )
                            ]
                            self.down_area_background.create_text(
                                160,
                                self.down_area_background_height - 45 + 10 * index1,
                                text=self.random_scramble_moves_seq[(row_chars * index1) : index2],
                                font="Arial 8 italic bold",
                                fill="black",
                                anchor=tk.NW,
                            )
                    elif self.previous_game_state == "draw_scramble":
                        self.down_area_background.create_text(
                            160,
                            self.down_area_background_height - 45,
                            text='You can see the scrambled cube pattern enabling the cube graphics option "scramble pattern".',
                            font="Arial 8 italic bold",
                            fill="black",
                            anchor=tk.NW,
                        )
                    self.same_scramble_cube_button = self._button(
                        self.down_area_background,
                        "same scramble",
                        "Arial 10 bold",
                        "red",
                        "yellow",
                        self.down_area_background_width - 120,
                        self.down_area_background_height - 30,
                        self.same_scramble_cube,
                    )
                else:
                    self.previous_game_state = self.game_state
                    self.game_state = "auto_solve"
                    self.make_cube_graphics(self.rubiks_cube, None)
                    self.down_area_background.create_text(
                        self.down_area_background_width / 2,
                        30,
                        text="Select the solving method you want to be used:",
                        font="Arial " + str(self.buttons_font) + " bold",
                        fill="brown",
                    )
                    if self.cube_size == 2:
                        self.down_area_background.create_text(
                            self.down_area_background_width / 2,
                            self.down_area_background_height / 2,
                            text="2x2 optimal solver (short solution, no fixed centres needed)",
                            font="Arial " + str(self.options_font) + " bold",
                            fill="red",
                            activefill="blue",
                            tags="2x2",
                        )
                        self.down_area_background.tag_bind(
                            "2x2",
                            "<Button-1>",
                            lambda event: self.auto_solve_cube("solve_cube", "2x2", None, event),
                        )
                        return
                    self.down_area_background.create_text(
                        self.down_area_background_width / 2,
                        self.down_area_background_height / 2 - 10,
                        text="Beginner's method (simple and slow, many moves needed)",
                        font="Arial " + str(self.options_font) + " bold",
                        fill="red",
                        activefill="blue",
                        tags="Beginner",
                    )
                    self.down_area_background.create_text(
                        self.down_area_background_width / 2,
                        self.down_area_background_height / 2 + 25,
                        text="CFOP method (advanced and fast, used in speedcubing)",
                        font="Arial " + str(self.options_font) + " bold",
                        fill="red",
                        activefill="blue",
                        tags="CFOP",
                    )
                    self.down_area_background.create_text(
                        self.down_area_background_width / 2,
                        self.down_area_background_height / 2 + 60,
                        text="Kociemba's algorithm (the fastest way, 20 moves in average)",
                        font="Arial " + str(self.options_font) + " bold",
                        fill="red",
                        activefill="blue",
                        tags="Kociemba",
                    )
                    self.down_area_background.tag_bind(
                        "Beginner",
                        "<Button-1>",
                        lambda event: self.auto_solve_cube("choose_color", "Beginner", None, event),
                    )
                    self.down_area_background.tag_bind(
                        "CFOP",
                        "<Button-1>",
                        lambda event: self.auto_solve_cube("solve_cube", "CFOP", None, event),
                    )
                    self.down_area_background.tag_bind(
                        "Kociemba",
                        "<Button-1>",
                        lambda event: self.auto_solve_cube("solve_cube", "Kociemba", None, event),
                    )
        elif solve_mode_stage == "choose_color":
            self.destroy_down_area_buttons()
            self.down_area_background.delete("all")
            rect_side = 90
            edge_offset = 140
            centre_x_offset = (
                (self.down_area_background_width - 2 * edge_offset) - 6 * rect_side
            ) / 10
            centre_y_offset = 20
            self.down_area_background.create_text(
                self.down_area_background_width / 2,
                30,
                text="Choose the cube side you want to be solved first:",
                font="Arial " + str(self.buttons_font) + " bold",
                fill="brown",
            )
            for k in range(6):
                self.down_area_background.create_rectangle(
                    [
                        edge_offset + (rect_side + 2 * centre_x_offset) * k,
                        self.down_area_background_height / 2 - rect_side / 2 + centre_y_offset,
                        edge_offset + (rect_side + 2 * centre_x_offset) * k + rect_side,
                        self.down_area_background_height / 2 + rect_side / 2 + centre_y_offset,
                    ],
                    fill=self.cube_colors[k],
                    activefill="black",
                    width=5,
                    outline="black",
                    tags=self.cube_colors[k],
                )
            for color in self.cube_colors:
                self.down_area_background.tag_bind(
                    color,
                    "<Button-1>",
                    lambda event, c=color: self.auto_solve_cube(
                        "solve_cube", solve_method_choose, c[0], event
                    ),
                )
        elif solve_mode_stage == "solve_cube":
            try:
                if self.buttons_bindings_are_activated:
                    self.animation.cancel()
                    self._cancel_pending_graphics()
                    self.buttons_bindings_are_activated = False
                    self.moves_bindings_are_activated = False
                    self.moves_speed = self.solve_moves_speed
                    if self.cube_size == 2:
                        self.down_area_background.delete("all")
                        self.down_area_background.create_text(
                            self.down_area_background_width / 2,
                            self.down_area_background_height / 2,
                            text="Solving...",
                            font="Arial 18 bold",
                            fill="brown",
                        )
                        self.root.update_idletasks()
                        flat_moves, _stage_moves, _solved_cube_state = solve_2x2(self.rubiks_cube)
                        self.down_area_background.delete("all")
                        self.down_area_background.create_text(
                            self.down_area_background_width / 2,
                            self.down_area_background_height / 2,
                            text=flat_moves,
                            font="Arial 18 italic bold",
                            fill="darkblue",
                            width=max(100, self.down_area_background_width - 40),
                        )
                        self.auto_solve_moves_seq = flat_moves
                    elif solve_method_choose == "Beginner":
                        stage_moves, _solved_cube_state = solve_beginner(
                            self.rubiks_cube, start_color_choose
                        )
                        initial_solved_color = start_color_choose
                        final_solved_color = ["b", "r", "y", "g", "o", "w"][
                            (["b", "r", "y", "g", "o", "w"].index(initial_solved_color) + 3) % 6
                        ]
                        solving_notes = [
                            "Solving {} centre".format(
                                self.cube_colors[
                                    ["b", "y", "o", "w", "r", "g"].index(initial_solved_color)
                                ]
                            ),
                            "Solving {} cross".format(
                                self.cube_colors[
                                    ["b", "y", "o", "w", "r", "g"].index(initial_solved_color)
                                ]
                            ),
                            "Solving down corners",
                            "Solving middle edges",
                            "Solving {} cross".format(
                                self.cube_colors[
                                    ["b", "y", "o", "w", "r", "g"].index(final_solved_color)
                                ]
                            ),
                            "Solving up corners",
                        ]
                        self._display_stages(stage_moves, solving_notes, 50, 250)
                        self.auto_solve_moves_seq = [
                            move for stage in stage_moves for move in stage
                        ]
                    elif solve_method_choose in ["CFOP", "Kociemba"]:
                        flat_moves, stage_moves, _solved_cube_state = solve_external(
                            self.rubiks_cube, solve_method_choose
                        )
                        self.down_area_background.delete("all")
                        if solve_method_choose == "CFOP" and stage_moves is not None:
                            solving_notes = [
                                "Cross - white cross",
                                "F2L - First 2 Layers",
                                "OLL - Orient Last Layer",
                                "PLL - Permute Last Layer",
                            ]
                            self._display_stages(stage_moves, solving_notes, 30, 270)
                        elif solve_method_choose == "Kociemba":
                            self.down_area_background.create_text(
                                self.down_area_background_width / 2,
                                self.down_area_background_height / 2,
                                text=flat_moves,
                                font="Arial 20 italic bold",
                                fill="darkblue",
                            )
                        self.auto_solve_moves_seq = flat_moves
                    # Write scramble moves and show solution.
                    self.down_area_background.create_text(
                        self.down_area_background_width / 2,
                        20,
                        text=f"{solve_method_choose} solve ({len(self.auto_solve_moves_seq)} moves in total):",
                        font="Calibri 18 bold",
                        fill="black",
                    )
                    self.down_area_background.create_text(
                        10,
                        self.down_area_background_height - 23,
                        text="Scramble:",
                        font="Arial 8 bold",
                        fill="black",
                        anchor=tk.NW,
                    )
                    if self.previous_game_state in ["moves_scramble", "self_solve"]:
                        row_chars = 50
                        for index1 in range(len(self.random_scramble_moves_seq) // row_chars + 1):
                            index2 = [
                                len(self.random_scramble_moves_seq),
                                row_chars * index1 + row_chars,
                            ][
                                [True, False].index(
                                    len(self.random_scramble_moves_seq) // row_chars == 0
                                )
                            ]
                            self.down_area_background.create_text(
                                80,
                                self.down_area_background_height - 23 + 10 * index1,
                                text=self.random_scramble_moves_seq[(row_chars * index1) : index2],
                                font="Arial 8 italic bold",
                                fill="black",
                                anchor=tk.NW,
                            )
                    elif self.previous_game_state == "draw_scramble":
                        self.down_area_background.create_text(
                            80,
                            self.down_area_background_height - 23,
                            text='You can see the scrambled cube pattern enabling the cube graphics option "scramble pattern".',
                            font="Arial 8 italic bold",
                            fill="black",
                            anchor=tk.NW,
                        )
                    self.same_scramble_cube_button = self._button(
                        self.down_area_background,
                        "same scramble",
                        "Arial 10 bold",
                        "red",
                        "yellow",
                        self.down_area_background_width - 120,
                        20,
                        self.same_scramble_cube,
                    )
                    self._add_replay_buttons()
                    self.make_moves_sequence(
                        self.rubiks_cube,
                        [""] + self.auto_solve_moves_seq,
                        True,
                    )
            except SolverLibraryNotInstalledError as exc:
                self._show_solver_error(
                    "Solver package missing",
                    str(exc),
                    action_text="back",
                )
            except InvalidCubeError as exc:
                self._show_solver_error(
                    "This cube pattern is not valid!",
                    f"{self.wrong_pattern_text}\n{exc}",
                )
            except SolverFailedError as exc:
                self._show_solver_error(
                    "The solver could not solve this cube.",
                    str(exc),
                )
            except Exception as exc:
                traceback.print_exc()
                self._show_solver_error(
                    "Unexpected solving error",
                    str(exc),
                )

    def _show_solver_error(
        self, title: str, message: str, action_text: str = "fix scramble"
    ) -> None:
        self.buttons_bindings_are_activated = True
        self.down_area_background.delete("all")
        self.down_area_background.create_text(
            self.down_area_background_width / 2,
            40,
            text=title,
            font="Arial " + str(self.buttons_font) + " bold",
            fill="brown",
        )
        self.down_area_background.create_text(
            self.down_area_background_width / 2,
            90,
            text=message,
            font="Arial 14 bold",
            fill="brown",
            width=self.down_area_background_width - 40,
        )
        self.down_area_background.create_text(
            90,
            self.down_area_background_height - 45,
            text="Scramble:",
            font="Arial 8 bold",
            fill="black",
            anchor=tk.NW,
        )
        self.down_area_background.create_text(
            160,
            self.down_area_background_height - 45,
            text='You can see the scrambled cube pattern enabling the cube graphics option "scramble pattern".',
            font="Arial 8 italic bold",
            fill="black",
            anchor=tk.NW,
        )
        self.same_scramble_cube_button = self._button(
            self.down_area_background,
            action_text,
            "Arial 10 bold",
            "red",
            "yellow",
            self.down_area_background_width - 200,
            self.down_area_background_height - 30,
            self.same_scramble_cube,
        )

    def cube_is_solved(self, cube: Cube) -> bool:
        signature = cube_signature(cube)
        if signature not in self._solved_cache:
            if len(self._solved_cache) >= 512:
                self._solved_cache.clear()
            self._solved_cache[signature] = is_solved(cube)
        solved = self._solved_cache[signature]
        if (
            solved
            and self.game_state in ["self_solve", "auto_solve"]
            and signature != self._last_solved_sound_signature
        ):
            self._last_solved_sound_signature = signature
            self.play_sound("solved_cube_sound", "sound")
        return solved

    def request_cube_graphics(self, main_cube: Cube, move: str | None) -> None:
        """Coalesce high-frequency redraw requests into one idle callback."""
        self._pending_graphics = (main_cube, move)
        if self._pending_graphics_id is None:
            self._pending_graphics_id = self.root.after_idle(self._render_pending_graphics)

    def _render_pending_graphics(self) -> None:
        self._pending_graphics_id = None
        if self._pending_graphics is None:
            return
        main_cube, move = self._pending_graphics
        self._pending_graphics = None
        self.make_cube_graphics(main_cube, move)

    def _cancel_pending_graphics(self) -> None:
        if self._pending_graphics_id is not None:
            try:
                self.root.after_cancel(self._pending_graphics_id)
            except tk.TclError:
                pass
            self._pending_graphics_id = None
        self._pending_graphics = None

    def show_previous_next_solve_move(self, direction: str, event: tk.Event | None = None) -> None:
        if (
            self.buttons_bindings_are_activated
            and self.replay.active
            and self.game_state in ["self_solve", "auto_solve"]
        ):
            self.animation.cancel()
            move = ""
            if direction == "start":
                initial_cube = [
                    self.moves_scrambled_rubiks_cube,
                    self.draw_scrambled_rubiks_cube,
                ][[True, False].index(self.previous_game_state in ["moves_scramble", "self_solve"])]
                self.rubiks_cube = self.replay.jump_to_start(initial_cube)
            elif direction == "end":
                self.rubiks_cube = self.replay.jump_to_end(self.rubiks_cube)
            elif direction == "previous":
                move = self.replay.previous_move()
            elif direction == "next":
                move = self.replay.next_move()
            self.make_moves_sequence(self.rubiks_cube, [move], True)
            self.make_cube_graphics(self.rubiks_cube, move)

    def make_moves_sequence(
        self,
        cube: Cube,
        moves_seq: Sequence[Move],
        make_changes_to_main_cube: bool,
        event: tk.Event | None = None,
    ) -> Cube:
        move = moves_seq[0] if len(moves_seq) != 0 else ""
        if self.cube_size == 2 and move and move[0] in "MES":
            move = ""
        if (
            (event is None) or (event is not None and self.moves_bindings_are_activated)
        ) and move != "":
            cube = apply_move(cube, move)
            if make_changes_to_main_cube:
                self.play_sound("make_move_sound", "sound")
        if make_changes_to_main_cube:
            self.rubiks_cube = cube
            if event is None and not self.replay.active:
                self.buttons_bindings_are_activated = False
                self.moves_bindings_are_activated = False
                if len(moves_seq) != 0:
                    self.animation.schedule(
                        int(1000 * self.moves_speed),
                        lambda: self.make_moves_sequence(self.rubiks_cube, moves_seq[1:], True),
                    )
                elif len(moves_seq) == 0:
                    self.buttons_bindings_are_activated = True
                    if self.game_state == "moves_scramble":
                        self.moves_scrambled_rubiks_cube = copy_cube(self.rubiks_cube)
                        self.moves_bindings_are_activated = True
                        if len(self.random_scramble_moves_seq) == self.max_scramble_moves:
                            self.moves_bindings_are_activated = False
                    elif self.game_state == "auto_solve" and not self.replay.active:
                        self.replay.start(self.auto_solve_moves_seq)
                        self.moves_bindings_are_activated = False
                self.make_cube_graphics(self.rubiks_cube, move)
            if (
                self.buttons_bindings_are_activated
                and self.moves_bindings_are_activated
                and not self.replay.active
            ):
                if self.game_state == "moves_scramble":
                    self.moves_scrambled_rubiks_cube = copy_cube(self.rubiks_cube)
                    if move != "":
                        if len(self.random_scramble_moves_seq) != self.max_scramble_moves:
                            self.random_scramble_moves_seq = improve_moves_sequence(
                                self.random_scramble_moves_seq + [move]
                            )
                        if len(self.random_scramble_moves_seq) == self.max_scramble_moves:
                            self.moves_bindings_are_activated = False
                    self.write_moves_scramble_text()
                    self.make_cube_graphics(self.rubiks_cube, move)
                elif self.game_state == "self_solve":
                    self.self_solve_moves_seq = self.self_solve_moves_seq + [move]
                    self.down_area_background.delete("all")
                    self.down_area_background.create_text(
                        self.down_area_background_width / 2,
                        20,
                        text=f"Self solve ({len(self.self_solve_moves_seq)} moves in total):",
                        font="Calibri 18 bold",
                        fill="black",
                    )
                    row_chars = 50
                    for index1 in range(len(self.self_solve_moves_seq) // row_chars + 1):
                        index2 = [len(self.self_solve_moves_seq), row_chars * index1 + row_chars][
                            [True, False].index(len(self.self_solve_moves_seq) // row_chars == 0)
                        ]
                        self.down_area_background.create_text(
                            self.down_area_background_width / 2,
                            50 + 15 * index1,
                            text=self.self_solve_moves_seq[(row_chars * index1) : index2],
                            font="Arial 10 italic bold",
                            fill="darkblue",
                        )
                    if self.cube_is_solved(self.rubiks_cube):
                        self.stop_timer_self_solving = time.time()
                        self.time_self_solving = (
                            self.stop_timer_self_solving - self.start_timer_self_solving
                        )
                        self.down_area_background.delete("all")
                        self.down_area_background.create_text(
                            20,
                            self.down_area_background_height / 2 - 40,
                            text=self.replay_moves_text,
                            font="Arial 10 bold",
                            fill="brown",
                            anchor=tk.NW,
                        )
                        self.down_area_background.create_text(
                            self.down_area_background_width / 2,
                            self.down_area_background_height / 2 - 40,
                            text="Congratulations, you solved the cube!!!",
                            font="Calibri 20 bold",
                            fill="purple",
                        )
                        self.down_area_background.create_text(
                            self.down_area_background_width / 2,
                            self.down_area_background_height / 2 - 10,
                            text=f"Moves needed: {len(self.self_solve_moves_seq)}",
                            font="Calibri 20 bold",
                            fill="purple",
                        )
                        self.down_area_background.create_text(
                            self.down_area_background_width / 2,
                            self.down_area_background_height / 2 + 20,
                            text=f"Solving time: {int(self.time_self_solving) // 60} minutes and {int(self.time_self_solving) % 60} seconds",
                            font="Calibri 20 bold",
                            fill="purple",
                        )
                        self.down_area_background.create_text(
                            10,
                            self.down_area_background_height - 23,
                            text="Scramble:",
                            font="Arial 8 bold",
                            fill="black",
                            anchor=tk.NW,
                        )
                        for index1 in range(len(self.random_scramble_moves_seq) // row_chars + 1):
                            index2 = [
                                len(self.random_scramble_moves_seq),
                                row_chars * index1 + row_chars,
                            ][
                                [True, False].index(
                                    len(self.random_scramble_moves_seq) // row_chars == 0
                                )
                            ]
                            self.down_area_background.create_text(
                                80,
                                self.down_area_background_height - 23 + 10 * index1,
                                text=self.random_scramble_moves_seq[(row_chars * index1) : index2],
                                font="Arial 8 italic bold",
                                fill="black",
                                anchor=tk.NW,
                            )
                        self.replay.start(self.self_solve_moves_seq)
                        self.moves_bindings_are_activated = False
                    self.make_cube_graphics(self.rubiks_cube, move)
        else:
            if len(moves_seq) != 0:
                return self.make_moves_sequence(cube, moves_seq[1:], False)
            return cube

    def cube_zoom_transfer_mouse_events(self, event: tk.Event) -> None:
        if event.type == tk.EventType.MouseWheel:
            if event.delta > 0 and self.piece_side_length < 200:
                self.piece_side_length += 5
            elif event.delta < 0 and self.piece_side_length > 10:
                self.piece_side_length -= 5
        elif event.type == tk.EventType.ButtonPress:
            if event.num == 4 and self.piece_side_length < 200:
                self.piece_side_length += 5
            elif event.num == 5 and self.piece_side_length > 10:
                self.piece_side_length -= 5
            else:
                self.lastx = event.x
                self.lasty = event.y
        elif event.type == tk.EventType.Motion:
            self.visible_cube_centre_x = self.visible_cube_centre_x + event.x - self.lastx
            self.visible_cube_centre_y = self.visible_cube_centre_y + event.y - self.lasty
            self.lastx = event.x
            self.lasty = event.y
        self.request_cube_graphics(self.rubiks_cube, None)

    def cube_moves_mouse_events(self, piece_info: str | None, event: tk.Event) -> None:
        if self.cube_dimensions != "3d":
            return
        if event.type == tk.EventType.ButtonPress:
            self.lastx2 = event.x
            self.lasty2 = event.y
            self.mouse_move_info = piece_info
            return
        if event.type != tk.EventType.ButtonRelease or self.mouse_move_info is None:
            return

        index1 = [True, False].index(abs(event.x - self.lastx2) >= abs(event.y - self.lasty2))
        index2 = [True, False].index(event.x >= self.lastx2)
        index3 = [True, False].index(event.y >= self.lasty2)
        side = int(self.mouse_move_info[0])
        row = int(self.mouse_move_info[1])
        column = int(self.mouse_move_info[2])
        move = None
        if self.cube_size == 2:
            if side == 5:
                rows = [[["U'"], ["U"]], [["D"], ["D'"]]]
                columns = [[["L"], ["L'"]], [["R'"], ["R"]]]
                move = [rows[row][index2], columns[column][index3]][index1]
            elif side == 3:
                rows = [[["B'"], ["B"]], [["F"], ["F'"]]]
                columns = [[["L"], ["L'"]], [["R'"], ["R"]]]
                move = [rows[row][index2], columns[column][index3]][index1]
            elif side == 4:
                rows = [[["U'"], ["U"]], [["D"], ["D'"]]]
                columns = [[["F"], ["F'"]], [["B'"], ["B"]]]
                move = [rows[row][index2], columns[column][index3]][index1]
        else:
            if side == 5:
                rows = [[["U'"], ["U"]], [["E"], ["E'"]], [["D"], ["D'"]]]
                columns = [[["L"], ["L'"]], [["M"], ["M'"]], [["R'"], ["R"]]]
                move = [rows[row][index2], columns[column][index3]][index1]
            elif side == 3:
                rows = [[["B'"], ["B"]], [["S"], ["S'"]], [["F"], ["F'"]]]
                columns = [[["L"], ["L'"]], [["M"], ["M'"]], [["R'"], ["R"]]]
                move = [rows[row][index2], columns[column][index3]][index1]
            elif side == 4:
                rows = [[["U'"], ["U"]], [["E"], ["E'"]], [["D"], ["D'"]]]
                columns = [[["F"], ["F'"]], [["S"], ["S'"]], [["B'"], ["B"]]]
                move = [rows[row][index2], columns[column][index3]][index1]
        if move is not None:
            self.make_moves_sequence(self.rubiks_cube, move, True, event)
        self.mouse_move_info = None

    def cube_rotations_mouse_events(self, event: tk.Event) -> None:
        if self.cube_dimensions == "3d":
            if event.type == tk.EventType.ButtonPress:
                self.lastx3 = event.x
                self.lasty3 = event.y
            elif event.type == tk.EventType.ButtonRelease:
                index1 = [True, False].index(
                    abs(event.x - self.lastx3) >= abs(event.y - self.lasty3)
                )
                index2 = [True, False].index(event.x >= self.lastx3)
                index3 = [True, False].index(event.y >= self.lasty3)
                if self.game_state == "draw_scramble":
                    self.change_cube_view(
                        self.rubiks_cube, [["y'", "y"][index2], ["x'", "x"][index3]][index1], event
                    )
                else:
                    self.make_moves_sequence(
                        self.rubiks_cube,
                        [[["y'"], ["y"]][index2], [["x'"], ["x"]][index3]][index1],
                        True,
                        event,
                    )

    def reset_cube_position(self, event: tk.Event) -> None:
        self.visible_cube_centre_x = self.cube_background_width / 2
        self.visible_cube_centre_y = self.cube_background_height / 2
        self.make_cube_graphics(self.rubiks_cube, None)

    def destroy_down_area_buttons(self) -> None:
        for name in (
            "clear_cube_draw_button",
            "fill_cube_draw_button",
            "same_scramble_cube_button",
            "self_solve_try_yourself_button",
            "self_solve_try_again_button",
            "go_to_replay_previous_move_button",
            "go_to_replay_next_move_button",
            "go_to_replay_start_button",
            "go_to_replay_end_button",
        ):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.destroy()
