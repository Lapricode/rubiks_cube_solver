"""Main application: state, game flow and event handling."""

from __future__ import annotations

import random
import time
import tkinter as tk
import traceback
from collections.abc import Callable, Sequence
from tkinter import filedialog, messagebox
from typing import TypeVar

import pygame

from .. import texts
from ..config import (
    BORDERS_WIDTHS,
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
    REPLAY_SPEEDS,
    SHORTCUT_LABELS,
    SIDES_DISTORTIONS,
    SOUNDS_DIR,
    THEME_NAMES,
    THEMES,
    TURN_ANIMATION_DURATIONS,
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
from ..persistence import export_solution, load_state, save_state
from ..shortcuts import load_shortcuts, save_shortcuts
from ..solver_2x2 import solve_2x2
from ..solver_4x4 import solve_4x4_detailed
from ..solvers import (
    SolverFailedError,
    SolverLibraryNotInstalledError,
    solve_beginner,
    solve_external,
)
from ..stats import format_seconds, load_stats, record_solve, summarize
from .animation import AnimationController, ReplayController, invert_move
from .graphics import CubeGraphicsMixin
from .menus import MenusMixin
from .pygame_panels import PygamePanel
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
        self.down_area_background = tk.Frame(
            self.right_paned,
            width=self.down_area_background_width,
            height=self.down_area_background_height,
            bg="yellow",
            bd=0,
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
        self.menu_panel = PygamePanel(
            self.menu_background,
            self.menu_background_width,
            self.menu_background_height,
            "black",
            self.play_sound,
        )
        self.menu_panel.frame.pack(fill=tk.BOTH, expand=True)
        self.bottom_panel = PygamePanel(
            self.down_area_background,
            self.down_area_background_width,
            self.down_area_background_height,
            "yellow",
            self.play_sound,
        )
        self.bottom_panel.frame.pack(fill=tk.BOTH, expand=True)

        # Appearance, persistence and tutorial state.
        self.theme_name = "classic"
        self.theme = THEMES[self.theme_name]
        self.stats = load_stats()
        self.session_history: list[dict[str, object]] = []
        self.shortcuts = load_shortcuts()
        self._shortcut_sequences: list[str] = []
        self._shortcut_overlay: tk.Toplevel | None = None
        self._shortcut_capture_action: str | None = None
        self.tutorial_enabled = True
        self._tutorial_label_text = ""

        # Variables for visible cube.
        self.cube_colors = list(self.theme["colors"])
        self.cube_size = DEFAULT_CUBE_SIZE
        self.cube_sizes_matrix = CUBE_SIZES
        self.cube_dimensions = "3d"
        self.cube_dimensions_matrix = CUBE_DIMENSIONS
        self.piece_side_length = {2: 150, 3: 100, 4: 80}[self.cube_size]
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
        self.chosen_draw_color = self.cube_colors[0]

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
        self.bottom_mode = "reset"
        self.pending_solve_method: str | None = None
        self.auto_solve_stage_moves: list[list[Move]] = []
        self.auto_solve_stage_notes: list[str] = []
        self.solver_error: tuple[str, str, str] | None = None
        self.mouse_move_info = None
        self.animation = AnimationController(self.root)
        self.replay = ReplayController()
        self._solved_cache: dict[tuple[str, ...], bool] = {}
        self._last_solved_sound_signature: tuple[str, ...] | None = None
        self._pending_graphics: tuple[Cube, str | None] | None = None
        self._pending_graphics_id: str | None = None
        self.sound_is_activated = True
        self.move_history: list[Move] = []
        self.redo_stack: list[Move] = []
        self.replay_speed = 1.0
        self.replay_playing = False
        self._replay_after_id: str | None = None
        self._timer_after_id: str | None = None
        self.smooth_turns_enabled = True
        self.turn_animation_duration = 100
        self._turn_animation_id: str | None = None
        self._turn_animation_offset = (0, 0)
        self.default_menus_font = DEFAULT_MENUS_FONT
        self.menus_font = self.default_menus_font
        self.default_options_font = DEFAULT_OPTIONS_FONT
        self.options_font = self.default_options_font
        self.default_buttons_font = DEFAULT_BUTTONS_FONT
        self.buttons_font = self.default_buttons_font
        self._menu_rebuild_id: str | None = None
        self._cube_center_initialized = False
        self.tutorial_label = tk.Label(
            self.cube_background,
            text="",
            justify=tk.CENTER,
            anchor="n",
            font="Arial 10 bold",
            bd=1,
            relief=tk.SOLID,
            padx=7,
            pady=4,
            wraplength=360,
        )
        self.tutorial_label.place(relx=0.5, y=8, anchor="n")
        self.tutorial_label.lift()
        self.buttons_bindings_are_activated = True
        self.moves_bindings_are_activated = True
        self.menu_panel.on_redraw = self.create_menus
        self.bottom_panel.on_redraw = self.render_bottom_panel

        self.create_menus()
        self.reset_game()
        self.bind_events()
        self.bind_custom_shortcuts()
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
        self.menu_panel.resize(int(event.width), int(event.height))
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
        self._update_auxiliary_positions()
        if hasattr(self, "rubiks_cube"):
            self.request_cube_graphics(self.rubiks_cube, None)

    def _update_auxiliary_positions(self) -> None:
        width = max(1.0, self.cube_background_width)
        height = max(1.0, self.cube_background_height)
        top_y = max(118.0, height * 0.14)
        self.hidden_cube_centre_x = max(118.0, width * 0.135)
        self.hidden_cube_centre_y = top_y
        self.scrambled_pattern_centre_x = width - max(150.0, width * 0.13)
        self.scrambled_pattern_centre_y = top_y

    def _on_down_area_configure(self, event: tk.Event) -> None:
        if event.widget is not self.down_area_background or event.width <= 1 or event.height <= 1:
            return
        self.down_area_background_width = float(event.width)
        self.down_area_background_height = float(event.height)
        self.bottom_panel.resize(int(event.width), int(event.height))
        self.render_bottom_panel()

    def render_bottom_panel(self) -> None:
        panel = self.bottom_panel
        width, height = panel.width, panel.height
        if width <= 1 or height <= 1:
            return

        panel.begin(self.theme["bottom_bg"])
        scale = max(0.72, min(1.35, min(width / 620.0, height / 175.0)))
        pad = max(6, int(10 * scale))
        title_size = max(11, int(18 * scale))
        body_size = max(10, int(14 * scale))
        small_size = max(9, int(11 * scale))
        button_size = max(9, int(12 * scale))
        button_h = max(22, min(34, int(26 * scale)))
        gap = max(4, int(7 * scale))
        title_line_height = max(title_size + 4, int(title_size * 1.4))
        body_line_height = max(body_size + 5, int(body_size * 1.5))
        small_line_height = max(small_size + 4, int(small_size * 1.5))
        text_color = self.theme["bottom_text"]
        title_color = self.theme["bottom_title"]
        muted_color = self.theme["bottom_muted"]
        accent_color = self.theme["bottom_accent"]
        button_fg = self.theme["button_fg"]
        button_bg = self.theme["button_bg"]
        button_hover = self.theme["button_hover"]
        button_outline = self.theme["button_outline"]

        def draw_button(
            key: str,
            rect: tuple[float, float, float, float],
            text: str,
            callback: Callable[[], None],
        ) -> None:
            panel.button(
                key,
                rect,
                text,
                button_size,
                button_fg,
                button_bg,
                callback,
                hover_bg=button_hover,
                outline=button_outline,
            )

        def centered(
            text: str,
            y: float,
            size: int = title_size,
            color: str = text_color,
            max_lines: int | None = None,
            line_height: float | None = None,
            anchor: str = "n",
        ) -> float:
            return panel.text(
                text,
                width / 2,
                y,
                size=size,
                color=color,
                anchor=anchor,
                bold=True,
                max_width=width - 2 * pad,
                max_lines=max_lines,
                line_height=line_height or title_line_height,
            )

        def draw_replay_buttons(y: float) -> None:
            button_width = max(24, int(30 * scale))
            x = pad
            for direction, label in (
                ("start", "|<"),
                ("previous", "<"),
                ("next", ">"),
                ("end", ">|"),
            ):
                draw_button(
                    f"replay:{direction}",
                    (x, y, button_width, button_h),
                    label,
                    lambda d=direction: self.show_previous_next_solve_move(d),
                )
                x += button_width + gap
            draw_button(
                "replay:play",
                (x, y, max(42, int(54 * scale)), button_h),
                "pause" if self.replay_playing else "play",
                self.toggle_replay_playback,
            )
            x += max(42, int(54 * scale)) + gap
            if self.auto_solve_stage_moves:
                draw_button(
                    "replay:stage_prev",
                    (x, y, max(40, int(50 * scale)), button_h),
                    "stage -",
                    lambda: self.jump_replay_stage("previous"),
                )
                x += max(40, int(50 * scale)) + gap
                draw_button(
                    "replay:stage_next",
                    (x, y, max(40, int(50 * scale)), button_h),
                    "stage +",
                    lambda: self.jump_replay_stage("next"),
                )

        def draw_replay_timeline(y: float) -> None:
            if not self.replay.active:
                return
            total = max(1, len(self.replay.moves))
            fraction = self.replay.pointer / total
            move_label = (
                f"Move {self.replay.pointer}/{len(self.replay.moves)}"
                f"    speed {self.replay_speed:g}x"
            )
            panel.text(
                move_label,
                pad,
                y + small_size / 2,
                size=small_size,
                color=muted_color,
                anchor="w",
                bold=True,
                line_height=small_line_height,
            )
            slider_x = max(
                pad + panel.font(small_size).size(move_label)[0] + 2 * gap,
                width * 0.38,
            )
            slider_height = max(16, int(18 * scale))
            panel.slider(
                "replay:seek",
                (slider_x, y, width - pad - slider_x, slider_height),
                fraction,
                self.seek_replay_fraction,
                track_color=button_bg,
                fill_color=accent_color,
                knob_color=button_fg,
                outline=button_outline,
            )
            speed_y = y + max(small_line_height + 2, int(22 * scale))
            panel.text(
                "replay speed",
                pad,
                speed_y + small_size / 2,
                size=small_size,
                color=muted_color,
                anchor="w",
                bold=True,
                line_height=small_line_height,
            )
            speed_index = REPLAY_SPEEDS.index(self.replay_speed)
            panel.slider(
                "replay:speed",
                (slider_x, speed_y, width - pad - slider_x, max(14, int(16 * scale))),
                speed_index / (len(REPLAY_SPEEDS) - 1),
                self.set_replay_speed_fraction,
                track_color=button_bg,
                fill_color=accent_color,
                knob_color=button_fg,
                outline=button_outline,
            )

        def draw_same_scramble(
            y: float,
            text: str = "same scramble",
            key: str = "same_scramble",
            callback: Callable[[], None] | None = None,
        ) -> None:
            button_width = max(86, int(112 * scale))
            draw_button(
                key,
                (width - pad - button_width, y, button_width, button_h),
                text,
                callback or self.same_scramble_cube,
            )

        def draw_color_swatches(
            y: float,
            callback: Callable[[str], None],
            key_prefix: str,
            selected_color: str | None = None,
        ) -> None:
            swatch_size = max(16, min(32, int(min(height * 0.22, width / 10))))
            swatch_gap = max(3, int(5 * scale))
            total_width = 6 * swatch_size + 5 * swatch_gap
            x = max(pad, (width - total_width) / 2)
            y = max(y, pad + title_size + gap)
            for color in self.cube_colors:
                selected = color == selected_color
                panel.button(
                    f"{key_prefix}:{color}",
                    (x, y, swatch_size, swatch_size),
                    "",
                    button_size,
                    (0, 0, 0),
                    color,
                    lambda c=color: callback(c),
                    outline=(0, 0, 0) if selected else (90, 90, 90),
                )
                if selected:
                    panel.rect((x, y, swatch_size, swatch_size), (0, 0, 0), width=3)
                x += swatch_size + swatch_gap

        mode = self.bottom_mode
        if mode == "reset":
            centered(
                self.reset_text,
                height / 2,
                body_size,
                title_color,
                max_lines=4,
                line_height=body_line_height,
                anchor="center",
            )
        elif mode == "moves_scramble":
            scramble = self.random_scramble_moves_seq
            title_height = centered(
                f"Scramble ({len(scramble)} moves in total):",
                pad,
                title_size,
                text_color,
            )
            body_y = pad + title_height + gap
            available_lines = max(
                1, int((height - pad - button_h - gap - body_y) / body_line_height)
            )
            panel.text(
                " ".join(scramble) if scramble else "No moves yet.",
                width / 2,
                body_y,
                size=body_size,
                color=accent_color,
                anchor="n",
                max_width=width - 2 * pad,
                max_lines=available_lines,
                line_height=body_line_height,
            )
            button_width = max(86, int(112 * scale))
            draw_button(
                "try_yourself",
                (width - pad - button_width, height - pad - button_h, button_width, button_h),
                "try yourself",
                self.self_solve_cube,
            )
        elif mode == "draw_scramble":
            centered(
                self.draw_scramble_text,
                pad,
                body_size,
                title_color,
                max_lines=3,
                line_height=body_line_height,
            )
            draw_color_swatches(
                height * 0.46,
                self.change_draw_color,
                "draw_color",
                selected_color=self.chosen_draw_color,
            )
            button_width = max(76, int(96 * scale))
            draw_button(
                "draw:clear",
                (width - pad - button_width, height - pad - button_h, button_width, button_h),
                "clear cube",
                lambda: self.clear_fill_cube_draw(False),
            )
            draw_button(
                "draw:fill",
                (
                    width - pad - button_width,
                    height - pad - 2 * button_h - gap,
                    button_width,
                    button_h,
                ),
                "fill cube",
                lambda: self.clear_fill_cube_draw(True),
            )
        elif mode == "self_solve":
            title_height = centered(
                f"Self solve ({len(self.self_solve_moves_seq)} moves in total):",
                pad,
                title_size,
                text_color,
            )
            elapsed = time.time() - getattr(self, "start_timer_self_solving", time.time())
            panel.text(
                f"Time {format_seconds(elapsed)}    " "Solve the cube with the mouse or keyboard.",
                width / 2,
                pad + title_height + gap,
                size=body_size,
                color=muted_color,
                anchor="n",
                bold=True,
                max_width=width - 2 * pad,
                max_lines=2,
                line_height=body_line_height,
            )
            button_width = max(86, int(112 * scale))
            draw_button(
                "try_again",
                (width - pad - button_width, height - pad - button_h, button_width, button_h),
                "try again",
                self.self_solve_cube,
            )
            if self.replay.active:
                draw_replay_buttons(height - pad - button_h)
        elif mode == "self_solve_done":
            title_height = centered(
                "Congratulations, you solved the cube!!!",
                pad,
                title_size,
                muted_color,
                max_lines=2,
            )
            minutes = int(getattr(self, "time_self_solving", 0)) // 60
            seconds = int(getattr(self, "time_self_solving", 0)) % 60
            panel.text(
                f"Moves needed: {len(self.self_solve_moves_seq)}    "
                f"Solving time: {minutes} min {seconds} sec",
                width / 2,
                pad + title_height + gap,
                size=body_size,
                color=muted_color,
                anchor="n",
                bold=True,
                max_width=width - 2 * pad,
                max_lines=1,
                line_height=body_line_height,
            )
            summary = summarize(self.stats, self.cube_size)
            panel.text(
                f"Best {format_seconds(summary['best'])}    "
                f"Average {format_seconds(summary['average'])}    "
                f"Solves {summary['count']}",
                width / 2,
                pad + title_height + gap + body_line_height,
                size=small_size,
                color=accent_color,
                anchor="n",
                bold=True,
                max_width=width - 2 * pad,
                max_lines=1,
                line_height=small_line_height,
            )
            timeline_y = height - pad - 3 * button_h - gap
            draw_replay_timeline(max(pad + title_height + gap, timeline_y))
            draw_replay_buttons(height - pad - button_h)
            button_width = max(86, int(112 * scale))
            draw_button(
                "try_again",
                (width - pad - button_width, height - pad - button_h, button_width, button_h),
                "try again",
                self.self_solve_cube,
            )
        elif mode == "choose_method":
            title_height = centered(
                "Select the solving method you want to be used:",
                pad,
                title_size,
                title_color,
                max_lines=2,
            )
            if self.cube_size == 2:
                options = [
                    (
                        "2x2 optimal solver",
                        "2x2",
                        lambda: self.auto_solve_cube("solve_cube", "2x2", None, None),
                    )
                ]
            elif self.cube_size == 4:
                options = [
                    (
                        "4x4 reduction (centres, wings, parity, then 3x3)",
                        "4x4",
                        lambda: self.auto_solve_cube("solve_cube", "4x4 reduction", None, None),
                    )
                ]
            else:
                options = [
                    (
                        "Beginner's method",
                        "Beginner",
                        lambda: self.auto_solve_cube("choose_color", "Beginner", None, None),
                    ),
                    (
                        "CFOP method",
                        "CFOP",
                        lambda: self.auto_solve_cube("solve_cube", "CFOP", None, None),
                    ),
                    (
                        "Kociemba's algorithm",
                        "Kociemba",
                        lambda: self.auto_solve_cube("solve_cube", "Kociemba", None, None),
                    ),
                ]
            top = pad + title_height + gap
            row_gap = max(2, gap // 2)
            row_height = min(
                max(24, int(30 * scale)),
                max(20, int((height - pad - top - (len(options) - 1) * row_gap) / len(options))),
            )
            for index, (label, key, callback) in enumerate(options):
                draw_button(
                    f"method:{key}",
                    (pad, top + index * (row_height + row_gap), width - 2 * pad, row_height),
                    label,
                    callback,
                )
        elif mode == "already_solved":
            title_height = centered(
                "The cube is already solved!",
                pad,
                title_size,
                title_color,
                max_lines=2,
            )
            panel.text(
                self.cube_is_solved_text,
                width / 2,
                pad + title_height + gap,
                size=body_size,
                color=title_color,
                anchor="n",
                max_width=width - 2 * pad,
                max_lines=2,
                line_height=body_line_height,
            )
            draw_same_scramble(height - pad - button_h)
        elif mode == "choose_color":
            centered(
                "Choose the cube side you want to be solved first:",
                pad,
                title_size,
                title_color,
                max_lines=2,
            )
            method = self.pending_solve_method or "Beginner"
            draw_color_swatches(
                height * 0.48,
                lambda color: self.auto_solve_cube("solve_cube", method, color[0], None),
                "solve_color",
            )
            draw_same_scramble(height - pad - button_h, "back", "back")
        elif mode == "solving":
            centered(
                "Solving...",
                height / 2,
                title_size,
                title_color,
                max_lines=1,
                anchor="center",
            )
        elif mode == "solve_result":
            method = self.pending_solve_method or "Cube"
            title_height = centered(
                f"{method} solve ({len(self.auto_solve_moves_seq)} moves in total):",
                pad,
                title_size,
                text_color,
                max_lines=1,
            )
            top = pad + title_height + gap
            bottom = height - pad - 3 * button_h - 2 * gap
            line_height = small_line_height
            available_lines = max(1, int((bottom - top) / line_height))
            small_font = panel.font(small_size)
            overflow = False
            if self.auto_solve_stage_moves and self.auto_solve_stage_notes:
                stage_texts = [
                    f"{note}: {' '.join(moves)}"
                    for note, moves in zip(
                        self.auto_solve_stage_notes,
                        self.auto_solve_stage_moves,
                        strict=False,
                    )
                ]
                fits = len(stage_texts) <= available_lines and all(
                    small_font.size(text)[0] <= width - 2 * pad for text in stage_texts
                )
                if fits:
                    for index, text in enumerate(stage_texts):
                        panel.text(
                            text,
                            width / 2,
                            top + index * line_height,
                            size=small_size,
                            color=muted_color,
                            anchor="n",
                            max_width=width - 2 * pad,
                            max_lines=1,
                            line_height=line_height,
                        )
                else:
                    overflow = True
                    display_count = min(len(self.auto_solve_stage_notes), available_lines)
                    if len(self.auto_solve_stage_notes) > display_count:
                        display_count = max(1, display_count - 1)
                    for index in range(display_count):
                        moves = self.auto_solve_stage_moves[index]
                        note = self.auto_solve_stage_notes[index]
                        panel.text(
                            f"{note} ({len(moves)} moves)",
                            width / 2,
                            top + index * line_height,
                            size=small_size,
                            color=muted_color,
                            anchor="n",
                            max_width=width - 2 * pad,
                            max_lines=1,
                            line_height=line_height,
                        )
                    if display_count < len(self.auto_solve_stage_notes):
                        panel.text(
                            "...",
                            width / 2,
                            top + display_count * line_height,
                            size=small_size,
                            color=muted_color,
                            anchor="n",
                            line_height=line_height,
                        )
            else:
                all_moves_text = " ".join(self.auto_solve_moves_seq)
                available_body_lines = max(1, int((bottom - top) / body_line_height))
                wrapped_lines = panel._wrap(all_moves_text, panel.font(body_size), width - 2 * pad)
                panel.text(
                    all_moves_text,
                    width / 2,
                    top,
                    size=body_size,
                    color=accent_color,
                    anchor="n",
                    max_width=width - 2 * pad,
                    max_lines=available_body_lines,
                    line_height=body_line_height,
                )
                overflow = len(wrapped_lines) > available_body_lines
            if overflow:
                all_width = max(78, int(96 * scale))
                same_width = max(86, int(112 * scale))
                draw_button(
                    "solution:all_moves",
                    (
                        width - pad - same_width - gap - all_width,
                        height - pad - button_h,
                        all_width,
                        button_h,
                    ),
                    "all moves",
                    self.show_solution_moves_overlay,
                )
            draw_replay_timeline(height - pad - 3 * button_h - gap)
            draw_replay_buttons(height - pad - button_h)
            draw_same_scramble(height - pad - button_h)
        elif mode == "history":
            title_height = centered(
                f"Move history ({len(self.move_history)} moves)",
                pad,
                title_size,
                title_color,
                max_lines=1,
            )
            recent = self.move_history[-14:]
            start_index = len(self.move_history) - len(recent) + 1
            history_text = (
                "  ".join(f"{start_index + index}. {move}" for index, move in enumerate(recent))
                if recent
                else "No interactive moves yet."
            )
            panel.text(
                history_text,
                width / 2,
                pad + title_height + gap,
                size=body_size,
                color=accent_color,
                anchor="n",
                max_width=width - 2 * pad,
                max_lines=3,
                line_height=body_line_height,
            )
            draw_button(
                "history:undo",
                (pad, height - pad - button_h, max(56, int(72 * scale)), button_h),
                "undo",
                self.undo_move,
            )
            draw_button(
                "history:redo",
                (
                    pad + max(56, int(72 * scale)) + gap,
                    height - pad - button_h,
                    max(56, int(72 * scale)),
                    button_h,
                ),
                "redo",
                self.redo_move,
            )
            draw_same_scramble(height - pad - button_h, "back", "history:back", self.show_history)
        elif mode == "stats":
            title_height = centered(
                f"Statistics ({self.cube_size}x{self.cube_size})",
                pad,
                title_size,
                title_color,
                max_lines=1,
            )
            summary = summarize(self.stats, self.cube_size)
            lines = [
                f"Solves: {summary['count']}    Best: {format_seconds(summary['best'])}    "
                f"Average: {format_seconds(summary['average'])}",
                "Recent: "
                + (
                    "  ".join(format_seconds(value) for value in summary["last_times"])
                    if summary["last_times"]
                    else "no solves yet"
                ),
                "Session: "
                + (
                    "  ".join(
                        f"{entry['size']}x{entry['size']} {format_seconds(float(entry['seconds']))}"
                        for entry in self.session_history[-4:]
                    )
                    if self.session_history
                    else "no solves yet"
                ),
            ]
            panel.text(
                "\n".join(lines),
                width / 2,
                pad + title_height + gap,
                size=body_size,
                color=accent_color,
                anchor="n",
                max_width=width - 2 * pad,
                max_lines=4,
                line_height=body_line_height,
            )
            draw_same_scramble(height - pad - button_h, "back", "stats:back", self.show_stats)
        elif mode == "error":
            title, message, action_text = self.solver_error or (
                "Solving error",
                "An unknown error occurred.",
                "back",
            )
            title_height = centered(title, pad, title_size, title_color, max_lines=1)
            panel.text(
                message,
                width / 2,
                pad + title_height + gap,
                size=body_size,
                color=title_color,
                anchor="n",
                max_width=width - 2 * pad,
                max_lines=2,
                line_height=body_line_height,
            )
            draw_same_scramble(height - pad - button_h, action_text, "error_action")
        panel.finish()
        self.update_tutorial_hint()

    def show_solution_moves_overlay(self, event: tk.Event | None = None) -> str:
        existing = getattr(self, "_solution_overlay", None)
        if existing is not None:
            existing.lift()
            return "break"
        overlay = tk.Toplevel(self.root)
        self._solution_overlay = overlay
        overlay.title("Solution moves")
        overlay.transient(self.root)
        overlay.configure(bg=self.theme["menu_bg"])
        overlay.geometry("900x520")
        header = tk.Label(
            overlay,
            text=f"{self.pending_solve_method or 'Solution'}: all moves",
            bg=self.theme["menu_bg"],
            fg=self.theme["menu_title"],
            font="Arial 14 bold",
            padx=10,
            pady=8,
        )
        header.pack(fill=tk.X)
        frame = tk.Frame(overlay, bg=self.theme["menu_bg"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
        text_widget = tk.Text(
            frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            bg=self.theme["button_bg"],
            fg=self.theme["button_fg"],
            insertbackground=self.theme["button_fg"],
            font="Arial 11",
            padx=8,
            pady=8,
        )
        scrollbar.configure(command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lines: list[str] = []
        if self.auto_solve_stage_moves and self.auto_solve_stage_notes:
            for index, (note, moves) in enumerate(
                zip(
                    self.auto_solve_stage_notes,
                    self.auto_solve_stage_moves,
                    strict=False,
                ),
                start=1,
            ):
                lines.append(f"{index}. {note} ({len(moves)} moves)")
                lines.append(f"   {' '.join(moves) or '(none)'}")
                lines.append("")
        lines.append("All moves:")
        lines.append(" ".join(self.auto_solve_moves_seq) or "(none)")
        text_widget.insert("1.0", "\n".join(lines))
        text_widget.configure(state=tk.DISABLED)
        close_button = tk.Button(
            overlay,
            text="close",
            command=self.close_solution_moves_overlay,
            bg=self.theme["button_bg"],
            fg=self.theme["button_fg"],
        )
        close_button.pack(pady=(0, 10))
        overlay.bind("<Escape>", lambda event: self.close_solution_moves_overlay())
        overlay.protocol("WM_DELETE_WINDOW", self.close_solution_moves_overlay)
        return "break"

    def close_solution_moves_overlay(self) -> None:
        overlay = getattr(self, "_solution_overlay", None)
        if overlay is not None:
            overlay.destroy()
        self._solution_overlay = None

    def _mode_for_game_state(self) -> str:
        if self.game_state == "self_solve":
            return (
                "self_solve_done"
                if getattr(self, "bottom_mode", "") == "self_solve_done"
                else "self_solve"
            )
        if self.game_state == "draw_scramble":
            return "draw_scramble"
        if self.game_state == "auto_solve":
            return "solve_result"
        return "moves_scramble"

    def _push_move_history(self, move: Move) -> None:
        if not move:
            return
        self.move_history.append(move)
        self.redo_stack.clear()

    def undo_move(self, event: tk.Event | None = None) -> str:
        if (
            not self.buttons_bindings_are_activated
            or self.replay.active
            or self.game_state not in ("moves_scramble", "self_solve")
            or self.bottom_mode not in ("moves_scramble", "self_solve", "history")
            or not self.move_history
        ):
            return "break"
        self.animation.cancel()
        was_history = self.bottom_mode == "history"
        move = self.move_history.pop()
        inverse = invert_move(move)
        self.redo_stack.append(move)
        self.rubiks_cube = apply_move(self.rubiks_cube, inverse)
        if self.game_state == "moves_scramble":
            if self.random_scramble_moves_seq and self.random_scramble_moves_seq[-1] == move:
                self.random_scramble_moves_seq.pop()
            self.moves_scrambled_rubiks_cube = copy_cube(self.rubiks_cube)
            self.write_moves_scramble_text()
        else:
            if self.self_solve_moves_seq and self.self_solve_moves_seq[-1] == move:
                self.self_solve_moves_seq.pop()
            self.bottom_mode = "self_solve"
            self.render_bottom_panel()
        if was_history:
            self.bottom_mode = "history"
            self.render_bottom_panel()
        self.make_cube_graphics(self.rubiks_cube, inverse)
        return "break"

    def redo_move(self, event: tk.Event | None = None) -> str:
        if (
            not self.buttons_bindings_are_activated
            or self.replay.active
            or self.game_state not in ("moves_scramble", "self_solve")
            or self.bottom_mode
            not in ("moves_scramble", "self_solve", "self_solve_done", "history")
            or not self.redo_stack
        ):
            return "break"
        self.animation.cancel()
        was_history = self.bottom_mode == "history"
        move = self.redo_stack.pop()
        self.rubiks_cube = apply_move(self.rubiks_cube, move)
        self.move_history.append(move)
        if self.game_state == "moves_scramble":
            self.random_scramble_moves_seq.append(move)
            self.moves_scrambled_rubiks_cube = copy_cube(self.rubiks_cube)
            self.write_moves_scramble_text()
        else:
            self.self_solve_moves_seq.append(move)
            self.bottom_mode = "self_solve"
            if self.cube_is_solved(self.rubiks_cube):
                self._finish_self_solve()
            self.render_bottom_panel()
        if was_history:
            self.bottom_mode = "history"
            self.render_bottom_panel()
        self.make_cube_graphics(self.rubiks_cube, move)
        return "break"

    def show_history(self, event: tk.Event | None = None) -> str:
        if self.bottom_mode == "history":
            self.bottom_mode = self._mode_for_game_state()
        else:
            self.bottom_mode = "history"
        self.render_bottom_panel()
        return "break"

    def show_stats(self, event: tk.Event | None = None) -> str:
        if self.bottom_mode == "stats":
            self.bottom_mode = self._mode_for_game_state()
        else:
            self.bottom_mode = "stats"
        self.render_bottom_panel()
        return "break"

    def tutorial_hint(self) -> str:
        return texts.TUTORIAL_HINTS.get(self.bottom_mode, texts.TUTORIAL_HINTS["default"])

    def update_tutorial_hint(self) -> None:
        if not self.tutorial_enabled:
            self.tutorial_label.place_forget()
            self._tutorial_label_text = ""
            return
        hint = self.tutorial_hint()
        if hint != self._tutorial_label_text:
            self._tutorial_label_text = hint
            self.tutorial_label.configure(
                text=hint,
                bg=self.theme["bottom_bg"],
                fg=self.theme["bottom_text"],
                highlightbackground=self.theme["bottom_accent"],
            )
        self.tutorial_label.configure(
            wraplength=max(220, min(640, self.cube_background_width - 40))
        )
        self.tutorial_label.place(relx=0.5, y=8, anchor="n")
        self.tutorial_label.lift()

    def toggle_tutorial(self, event: tk.Event | None = None) -> str:
        self.tutorial_enabled = not self.tutorial_enabled
        self.update_tutorial_hint()
        if hasattr(self, "reset_cube_view_button"):
            self.reset_cube_view_button.place_configure(y=56 if self.tutorial_enabled else 18)
        self.create_menus()
        return "break"

    def change_theme(self, event: tk.Event | None = None) -> str:
        index = THEME_NAMES.index(self.theme_name)
        self.theme_name = THEME_NAMES[(index + 1) % len(THEME_NAMES)]
        self.theme = THEMES[self.theme_name]
        self.cube_colors = list(self.theme["colors"])
        if self.chosen_draw_color not in self.cube_colors:
            self.chosen_draw_color = self.cube_colors[0]
        self.menu_background.configure(bg=self.theme["menu_bg"])
        self.down_area_background.configure(bg=self.theme["bottom_bg"])
        self.cube_background.configure(bg=self.theme["cube_bg"])
        for panel, background in (
            (self.menu_panel, self.theme["menu_bg"]),
            (self.bottom_panel, self.theme["bottom_bg"]),
        ):
            panel.background = background
            panel.frame.configure(bg=background)
            panel.label.configure(bg=background)
        self.create_menus()
        self.render_bottom_panel()
        self.make_cube_graphics(self.rubiks_cube, None)
        self.update_tutorial_hint()
        return "break"

    def toggle_smooth_turns(self, event: tk.Event | None = None) -> str:
        self.smooth_turns_enabled = not self.smooth_turns_enabled
        self.create_menus()
        return "break"

    def cycle_turn_animation_duration(self, event: tk.Event | None = None) -> str:
        self.turn_animation_duration = self.alternate_matrix_elements(
            TURN_ANIMATION_DURATIONS, self.turn_animation_duration
        )
        self.create_menus()
        return "break"

    def _event_to_shortcut(self, event: tk.Event) -> str | None:
        if event.keysym in (
            "Control_L",
            "Control_R",
            "Shift_L",
            "Shift_R",
            "Alt_L",
            "Alt_R",
            "Super_L",
            "Super_R",
        ):
            return None
        modifiers: list[str] = []
        if event.state & 0x4:
            modifiers.append("Control")
        if event.state & 0x8:
            modifiers.append("Alt")
        if event.state & 0x1:
            modifiers.append("Shift")
        key = event.keysym
        if len(key) == 1:
            key = key.lower()
        return "<" + "-".join([*modifiers, key]) + ">"

    def _start_shortcut_capture(self, action: str) -> None:
        if self._shortcut_overlay is None:
            return
        self._shortcut_capture_action = action
        self._shortcut_status_var.set(
            f"Press the new shortcut for {SHORTCUT_LABELS[action]} (Esc cancels)."
        )
        self._shortcut_overlay.bind("<KeyPress>", self._capture_shortcut)

    def _capture_shortcut(self, event: tk.Event) -> str:
        action = self._shortcut_capture_action
        if action is None or self._shortcut_overlay is None:
            return ""
        if event.keysym == "Escape":
            self._shortcut_capture_action = None
            self._shortcut_overlay.unbind("<KeyPress>")
            self._shortcut_status_var.set("Shortcut change cancelled.")
            return "break"
        sequence = self._event_to_shortcut(event)
        if sequence is None:
            return "break"
        for other_action, other_sequence in self.shortcuts.items():
            if other_action != action and other_sequence == sequence:
                self._shortcut_status_var.set(
                    f"{sequence} is already used by {SHORTCUT_LABELS[other_action]}."
                )
                return "break"
        self.shortcuts[action] = sequence
        save_shortcuts(self.shortcuts)
        self.bind_custom_shortcuts()
        self._shortcut_vars[action].set(sequence)
        self._shortcut_capture_action = None
        self._shortcut_overlay.unbind("<KeyPress>")
        self._shortcut_status_var.set(f"Saved {sequence}.")
        return "break"

    def show_shortcuts_overlay(self, event: tk.Event | None = None) -> str:
        if self._shortcut_overlay is not None:
            self._shortcut_overlay.lift()
            return "break"
        overlay = tk.Toplevel(self.root)
        self._shortcut_overlay = overlay
        overlay.title("Keyboard shortcuts")
        overlay.transient(self.root)
        overlay.configure(bg=self.theme["menu_bg"])
        overlay.resizable(False, False)
        self._shortcut_vars: dict[str, tk.StringVar] = {}
        self._shortcut_status_var = tk.StringVar(
            value="Click change, then press a key combination."
        )
        for row, action in enumerate(self.shortcuts):
            tk.Label(
                overlay,
                text=SHORTCUT_LABELS[action],
                bg=self.theme["menu_bg"],
                fg=self.theme["menu_text"],
                anchor="w",
                padx=8,
                pady=4,
            ).grid(row=row, column=0, sticky="ew")
            variable = tk.StringVar(value=self.shortcuts[action])
            self._shortcut_vars[action] = variable
            tk.Label(
                overlay,
                textvariable=variable,
                bg=self.theme["button_bg"],
                fg=self.theme["button_fg"],
                width=18,
                padx=6,
                pady=4,
            ).grid(row=row, column=1, padx=4, pady=2)
            tk.Button(
                overlay,
                text="change",
                command=lambda a=action: self._start_shortcut_capture(a),
            ).grid(row=row, column=2, padx=6, pady=2)
        tk.Label(
            overlay,
            textvariable=self._shortcut_status_var,
            bg=self.theme["menu_bg"],
            fg=self.theme["menu_title"],
            anchor="w",
            padx=8,
            pady=6,
        ).grid(row=len(self.shortcuts), column=0, columnspan=3, sticky="ew")
        overlay.bind("<Escape>", lambda event: self.close_shortcuts_overlay())
        overlay.protocol("WM_DELETE_WINDOW", self.close_shortcuts_overlay)
        return "break"

    def close_shortcuts_overlay(self) -> None:
        if self._shortcut_overlay is not None:
            self._shortcut_overlay.destroy()
        self._shortcut_overlay = None
        self._shortcut_capture_action = None

    def run_shortcut(self, action: str) -> str:
        callbacks = {
            "undo": self.undo_move,
            "redo": self.redo_move,
            "save": self.save_cube_state,
            "load": self.load_cube_state,
            "export": self.export_current_solution,
            "stats": self.show_stats,
            "shortcuts": self.show_shortcuts_overlay,
            "tutorial": self.toggle_tutorial,
            "theme": self.change_theme,
            "smooth": self.toggle_smooth_turns,
        }
        callback = callbacks.get(action)
        if callback is not None:
            return callback()
        return ""

    def bind_custom_shortcuts(self) -> None:
        for sequence in self._shortcut_sequences:
            try:
                self.root.unbind(sequence)
            except tk.TclError:
                pass
        self._shortcut_sequences = []
        for action, sequence in self.shortcuts.items():
            try:
                self.root.bind(sequence, lambda event, a=action: self.run_shortcut(a))
            except tk.TclError:
                continue
            self._shortcut_sequences.append(sequence)

    def save_cube_state(self, event: tk.Event | None = None) -> str:
        path = filedialog.asksaveasfilename(
            title="Save cube state",
            defaultextension=".json",
            filetypes=[("Cube state", "*.json"), ("All files", "*.*")],
        )
        if path:
            try:
                if self.game_state == "self_solve":
                    moves = self.self_solve_moves_seq
                elif self.game_state == "auto_solve":
                    moves = self.auto_solve_moves_seq
                else:
                    moves = self.random_scramble_moves_seq
                save_state(path, self.rubiks_cube, moves)
            except OSError as exc:
                messagebox.showerror("Save failed", str(exc), parent=self.root)
        return "break"

    def load_cube_state(self, event: tk.Event | None = None) -> str:
        path = filedialog.askopenfilename(
            title="Load cube state",
            filetypes=[("Cube state", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return "break"
        try:
            cube, moves = load_state(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Load failed", str(exc), parent=self.root)
            return "break"
        size = len(cube[0])
        if size not in CUBE_SIZES:
            messagebox.showerror("Load failed", f"Unsupported cube size: {size}", parent=self.root)
            return "break"
        self.animation.cancel()
        self._cancel_pending_graphics()
        self._stop_replay_playback(render=False)
        self._stop_live_timer()
        self.replay.reset()
        self.cube_size = size
        self.piece_side_length = {2: 150, 3: 100, 4: 80}[size]
        self.rubiks_cube = copy_cube(cube)
        self.moves_scrambled_rubiks_cube = copy_cube(cube)
        self.random_scramble_moves_seq = list(moves)
        self.self_solve_moves_seq = []
        self.auto_solve_moves_seq = []
        self.auto_solve_stage_moves = []
        self.auto_solve_stage_notes = []
        self.move_history = []
        self.redo_stack = []
        self.game_state = "moves_scramble"
        self.previous_game_state = "moves_scramble"
        self.bottom_mode = "moves_scramble"
        self.buttons_bindings_are_activated = True
        self.moves_bindings_are_activated = True
        self.adjust_cube_view_moves = []
        self.create_menus()
        self.render_bottom_panel()
        self.make_cube_graphics(self.rubiks_cube, None)
        return "break"

    def export_current_solution(self, event: tk.Event | None = None) -> str:
        stages: Sequence[Sequence[Move]] = []
        notes: Sequence[str] = []
        if self.game_state == "self_solve":
            moves = self.self_solve_moves_seq
            method = "Self solve"
        elif self.game_state == "auto_solve":
            moves = self.auto_solve_moves_seq
            method = self.pending_solve_method or "Solution"
            stages = self.auto_solve_stage_moves
            notes = self.auto_solve_stage_notes
        else:
            moves = self.auto_solve_moves_seq or self.random_scramble_moves_seq
            method = self.pending_solve_method or "Scramble"
        path = filedialog.asksaveasfilename(
            title="Export solution",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
        )
        if path:
            try:
                export_solution(
                    path,
                    moves,
                    method=method,
                    stages=stages,
                    notes=notes,
                )
            except OSError as exc:
                messagebox.showerror("Export failed", str(exc), parent=self.root)
        return "break"

    def _finish_self_solve(self) -> None:
        self.stop_timer_self_solving = time.time()
        self.time_self_solving = self.stop_timer_self_solving - self.start_timer_self_solving
        self._stop_live_timer()
        record_solve(
            self.stats,
            self.cube_size,
            self.time_self_solving,
            len(self.self_solve_moves_seq),
        )
        self.session_history.append(
            {
                "size": self.cube_size,
                "seconds": self.time_self_solving,
                "moves": len(self.self_solve_moves_seq),
            }
        )
        self.bottom_mode = "self_solve_done"
        self.replay.start(self.self_solve_moves_seq)
        self.moves_bindings_are_activated = False

    def _start_live_timer(self) -> None:
        self._stop_live_timer()
        self._timer_after_id = self.root.after(250, self._tick_live_timer)

    def _tick_live_timer(self) -> None:
        self._timer_after_id = None
        if self.game_state != "self_solve" or self.bottom_mode != "self_solve":
            return
        self.render_bottom_panel()
        self._timer_after_id = self.root.after(250, self._tick_live_timer)

    def _stop_live_timer(self) -> None:
        if self._timer_after_id is not None:
            try:
                self.root.after_cancel(self._timer_after_id)
            except tk.TclError:
                pass
            self._timer_after_id = None

    def _replay_initial_cube(self) -> Cube:
        if self.previous_game_state == "draw_scramble":
            return self.draw_scrambled_rubiks_cube
        return self.moves_scrambled_rubiks_cube

    def _replay_stage_bounds(self) -> list[int]:
        bounds = [0]
        for stage in self.auto_solve_stage_moves:
            bounds.append(bounds[-1] + len(stage))
        if bounds[-1] != len(self.replay.moves):
            return [0, len(self.replay.moves)]
        return bounds

    def _apply_replay_index(self, index: int) -> None:
        self.rubiks_cube = self.replay.seek(index, self._replay_initial_cube())
        self.make_cube_graphics(self.rubiks_cube, None)
        self.render_bottom_panel()

    def seek_replay_fraction(self, fraction: float) -> None:
        if not self.replay.active:
            return
        self._stop_replay_playback(render=False)
        index = round(fraction * len(self.replay.moves))
        self._apply_replay_index(index)

    def jump_replay_stage(self, direction: str) -> None:
        if not self.replay.active:
            return
        self._stop_replay_playback(render=False)
        bounds = self._replay_stage_bounds()
        target = self.replay.pointer
        if direction == "next":
            for bound in bounds:
                if bound > self.replay.pointer:
                    target = bound
                    break
        else:
            for bound in reversed(bounds):
                if bound < self.replay.pointer:
                    target = bound
                    break
        self._apply_replay_index(target)

    def set_replay_speed_fraction(self, fraction: float) -> None:
        index = round(fraction * (len(REPLAY_SPEEDS) - 1))
        self.replay_speed = REPLAY_SPEEDS[min(max(0, index), len(REPLAY_SPEEDS) - 1)]
        if self.replay_playing:
            self._schedule_replay_tick()
        self.render_bottom_panel()

    def _schedule_replay_tick(self) -> None:
        if self._replay_after_id is not None:
            try:
                self.root.after_cancel(self._replay_after_id)
            except tk.TclError:
                pass
        delay = int(1000 / max(0.25, self.replay_speed))
        self._replay_after_id = self.root.after(delay, self._replay_tick)

    def _replay_tick(self) -> None:
        self._replay_after_id = None
        if not self.replay_playing or not self.replay.active:
            return
        if self.replay.pointer >= len(self.replay.moves):
            self._stop_replay_playback()
            return
        move = self.replay.next_move()
        self.rubiks_cube = apply_move(self.rubiks_cube, move)
        self.make_cube_graphics(self.rubiks_cube, move)
        self.render_bottom_panel()
        if self.replay.pointer >= len(self.replay.moves):
            self._stop_replay_playback()
        else:
            self._schedule_replay_tick()

    def toggle_replay_playback(self, event: tk.Event | None = None) -> None:
        if self.replay_playing:
            self._stop_replay_playback()
            return
        if not self.replay.active:
            return
        if self.replay.pointer >= len(self.replay.moves):
            self._apply_replay_index(0)
        self.replay_playing = True
        self.render_bottom_panel()
        self._schedule_replay_tick()

    def _stop_replay_playback(self, render: bool = True) -> None:
        self.replay_playing = False
        if self._replay_after_id is not None:
            try:
                self.root.after_cancel(self._replay_after_id)
            except tk.TclError:
                pass
            self._replay_after_id = None
        if render and self.bottom_mode in ("self_solve", "self_solve_done", "solve_result"):
            self.render_bottom_panel()

    def reset_game(self, event: tk.Event | None = None) -> None:
        if self.buttons_bindings_are_activated:
            self.animation.cancel()
            self._cancel_pending_graphics()
            self._stop_replay_playback(render=False)
            self._stop_live_timer()
            self.replay.reset()
            self.move_history = []
            self.redo_stack = []
            self.buttons_bindings_are_activated = True
            self.moves_bindings_are_activated = True
            self.game_state = "moves_scramble"
            self.previous_game_state = "moves_scramble"
            self.bottom_mode = "reset"
            self.pending_solve_method = None
            self.auto_solve_stage_moves = []
            self.auto_solve_stage_notes = []
            self.solver_error = None
            self._update_auxiliary_positions()
            self.render_bottom_panel()
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
            self._stop_replay_playback(render=False)
            self._stop_live_timer()
            self.replay.reset()
            self.move_history = []
            self.redo_stack = []
            self.buttons_bindings_are_activated = False
            self.moves_bindings_are_activated = False
            self.previous_game_state = self.game_state
            self.game_state = "moves_scramble"
            self.moves_speed = self.scramble_moves_speed
            scramble_moves_before = len(self.random_scramble_moves_seq)
            if event is not None:
                faces = ["L", "R", "U", "D", "F", "B"]
                if self.cube_size == 4:
                    move_pool = [face + suffix for face in faces for suffix in ("", "'", "2")] + [
                        face + "w" + suffix for face in faces for suffix in ("", "'", "2")
                    ]
                else:
                    move_pool = [face + suffix for face in faces for suffix in ("", "'")]
                    if self.cube_size == 3:
                        move_pool += ["M", "M'", "E", "E'", "S", "S'"]
                while (
                    len(self.random_scramble_moves_seq) < self.max_scramble_moves
                    and len(self.random_scramble_moves_seq)
                    != scramble_moves_before + self.random_scramble_moves
                ):
                    self.random_scramble_moves_seq.append(random.choice(move_pool))
                    self.random_scramble_moves_seq = improve_moves_sequence(
                        self.random_scramble_moves_seq
                    )
            self.write_moves_scramble_text()
            self.rubiks_cube = solved_cube(self.cube_size)
            self.make_moves_sequence(self.rubiks_cube, [""] + self.random_scramble_moves_seq, True)

    def write_moves_scramble_text(self) -> None:
        self.bottom_mode = "moves_scramble"
        self.render_bottom_panel()

    def draw_scramble_cube(self, event: tk.Event | None = None) -> None:
        if self.buttons_bindings_are_activated:
            self.animation.cancel()
            self._cancel_pending_graphics()
            self._stop_replay_playback(render=False)
            self._stop_live_timer()
            self.buttons_bindings_are_activated = True
            self.moves_bindings_are_activated = False
            self.replay.reset()
            self.move_history = []
            self.redo_stack = []
            self.previous_game_state = self.game_state
            self.game_state = "draw_scramble"
            self.bottom_mode = "draw_scramble"
            self.rubiks_cube = copy_cube(self.draw_scrambled_rubiks_cube)
            self.render_bottom_panel()
            self.make_cube_graphics(self.rubiks_cube, None)

    def clear_fill_cube_draw(self, fill: bool) -> None:
        if fill:
            self.draw_scrambled_rubiks_cube = solved_cube(self.cube_size)
        else:
            self.draw_scrambled_rubiks_cube = blank_cube("c", self.cube_size)
        self.rubiks_cube = copy_cube(self.draw_scrambled_rubiks_cube)
        self.make_cube_graphics(self.rubiks_cube, None)

    def change_draw_color(self, color_chosen: str, event: tk.Event | None = None) -> None:
        self.chosen_draw_color = color_chosen
        self.render_bottom_panel()
        self.make_cube_graphics(self.rubiks_cube, None)

    def same_scramble_cube(self, event: tk.Event | None = None) -> None:
        if self.buttons_bindings_are_activated:
            if self.previous_game_state in ["moves_scramble", "self_solve"]:
                self.moves_scramble_cube()
            elif self.previous_game_state == "draw_scramble":
                self.draw_scramble_cube()

    def self_solve_cube(self, event: tk.Event | None = None) -> None:
        if self.buttons_bindings_are_activated:
            self.animation.cancel()
            self._cancel_pending_graphics()
            self._stop_replay_playback(render=False)
            self._stop_live_timer()
            self.previous_game_state = self.game_state
            self.game_state = "self_solve"
            self.bottom_mode = "self_solve"
            self.buttons_bindings_are_activated = True
            self.moves_bindings_are_activated = True
            self.replay.reset()
            self.move_history = []
            self.redo_stack = []
            self.self_solve_moves_seq = []
            self.start_timer_self_solving = time.time()
            self.rubiks_cube = copy_cube(self.moves_scrambled_rubiks_cube)
            self.render_bottom_panel()
            self.make_cube_graphics(self.rubiks_cube, None)
            self._start_live_timer()

    def _display_stages(
        self,
        stage_moves: Sequence[Sequence[Move]],
        notes: Sequence[str],
        row_chars: int,
        text_x: float,
    ) -> None:
        self.auto_solve_stage_moves = [list(moves) for moves in stage_moves]
        self.auto_solve_stage_notes = list(notes)

    def _display_stage_summary(
        self,
        stage_moves: Sequence[Sequence[Move]],
        notes: Sequence[str],
    ) -> None:
        self.auto_solve_stage_moves = [list(moves) for moves in stage_moves]
        self.auto_solve_stage_notes = list(notes)

    def auto_solve_cube(
        self,
        solve_mode_stage: str,
        solve_method_choose: str | None,
        start_color_choose: str | None,
        event: tk.Event | None,
    ) -> None:
        if solve_mode_stage == "choose_method":
            if not self.buttons_bindings_are_activated or self.game_state in [
                "self_solve",
                "auto_solve",
            ]:
                return
            self.moves_bindings_are_activated = False
            self.replay.active = False
            if self.cube_is_solved(self.rubiks_cube):
                if self.game_state != "auto_solve":
                    self.previous_game_state = self.game_state
                self.solver_error = None
                self.bottom_mode = "already_solved"
                self.render_bottom_panel()
                return
            self.previous_game_state = self.game_state
            self.game_state = "auto_solve"
            self.pending_solve_method = None
            self.auto_solve_stage_moves = []
            self.auto_solve_stage_notes = []
            self.auto_solve_moves_seq = []
            self.bottom_mode = "choose_method"
            self.render_bottom_panel()
            self.make_cube_graphics(self.rubiks_cube, None)
            return
        if solve_mode_stage == "choose_color":
            self.pending_solve_method = solve_method_choose
            self.moves_bindings_are_activated = False
            self.bottom_mode = "choose_color"
            self.render_bottom_panel()
            return
        if solve_mode_stage != "solve_cube" or not self.buttons_bindings_are_activated:
            return
        try:
            self.animation.cancel()
            self._cancel_pending_graphics()
            if self.game_state != "auto_solve":
                self.previous_game_state = self.game_state
                self.game_state = "auto_solve"
            self.buttons_bindings_are_activated = False
            self.moves_bindings_are_activated = False
            self.moves_speed = self.solve_moves_speed
            self.auto_solve_stage_moves = []
            self.auto_solve_stage_notes = []
            self.solver_error = None
            self.bottom_mode = "solving"
            self.render_bottom_panel()
            self.root.update_idletasks()
            if self.cube_size == 2:
                flat_moves, _stage_moves, _solved_cube_state = solve_2x2(self.rubiks_cube)
                self.auto_solve_moves_seq = flat_moves
                self.pending_solve_method = "2x2"
            elif self.cube_size == 4:
                flat_moves, stage_moves, stage_notes, _solved_cube_state = solve_4x4_detailed(
                    self.rubiks_cube
                )
                self.auto_solve_moves_seq = flat_moves
                self._display_stage_summary(stage_moves, stage_notes)
                self.pending_solve_method = "4x4 reduction"
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
                        self.cube_colors[["b", "y", "o", "w", "r", "g"].index(initial_solved_color)]
                    ),
                    "Solving {} cross".format(
                        self.cube_colors[["b", "y", "o", "w", "r", "g"].index(initial_solved_color)]
                    ),
                    "Solving down corners",
                    "Solving middle edges",
                    "Solving {} cross".format(
                        self.cube_colors[["b", "y", "o", "w", "r", "g"].index(final_solved_color)]
                    ),
                    "Solving up corners",
                ]
                self._display_stages(stage_moves, solving_notes, 50, 250)
                self.auto_solve_moves_seq = [move for stage in stage_moves for move in stage]
                self.pending_solve_method = "Beginner"
            elif solve_method_choose in ["CFOP", "Kociemba"]:
                flat_moves, stage_moves, _solved_cube_state = solve_external(
                    self.rubiks_cube, solve_method_choose
                )
                self.auto_solve_moves_seq = flat_moves
                if solve_method_choose == "CFOP" and stage_moves is not None:
                    solving_notes = [
                        "Cross - white cross",
                        "F2L - First 2 Layers",
                        "OLL - Orient Last Layer",
                        "PLL - Permute Last Layer",
                    ]
                    self._display_stages(stage_moves, solving_notes, 30, 270)
                self.pending_solve_method = solve_method_choose
            self.bottom_mode = "solve_result"
            self.render_bottom_panel()
            self.make_moves_sequence(self.rubiks_cube, [""] + self.auto_solve_moves_seq, True)
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
        self.solver_error = (title, message, action_text)
        self.bottom_mode = "error"
        self.render_bottom_panel()

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
            self._stop_replay_playback(render=False)
            if direction == "start":
                index = 0
            elif direction == "end":
                index = len(self.replay.moves)
            elif direction == "previous":
                index = max(0, self.replay.pointer - 1)
            elif direction == "next":
                index = min(len(self.replay.moves), self.replay.pointer + 1)
            else:
                return
            self._apply_replay_index(index)

    def make_moves_sequence(
        self,
        cube: Cube,
        moves_seq: Sequence[Move],
        make_changes_to_main_cube: bool,
        event: tk.Event | None = None,
    ) -> Cube:
        move = moves_seq[0] if len(moves_seq) != 0 else ""
        if self.cube_size % 2 == 0 and move and move[0] in "MES":
            move = ""
        if (
            (event is None) or (event is not None and self.moves_bindings_are_activated)
        ) and move != "":
            cube = apply_move(cube, move)
            if make_changes_to_main_cube:
                self.play_sound("make_move_sound", "sound")
                if event is not None and self.game_state in ("moves_scramble", "self_solve"):
                    self._push_move_history(move)
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
                        self.render_bottom_panel()
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
                    if move:
                        self.self_solve_moves_seq = self.self_solve_moves_seq + [move]
                    if self.cube_is_solved(self.rubiks_cube):
                        self._finish_self_solve()
                    else:
                        self.bottom_mode = "self_solve"
                    self.render_bottom_panel()
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
        elif self.cube_size == 3:
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
        else:
            if side == 5:
                rows = [
                    [["U'"], ["U"]],
                    [["u'"], ["u"]],
                    [["d"], ["d'"]],
                    [["D"], ["D'"]],
                ]
                columns = [
                    [["L"], ["L'"]],
                    [["l"], ["l'"]],
                    [["r'"], ["r"]],
                    [["R'"], ["R"]],
                ]
                move = [rows[row][index2], columns[column][index3]][index1]
            elif side == 3:
                rows = [
                    [["B'"], ["B"]],
                    [["b'"], ["b"]],
                    [["f"], ["f'"]],
                    [["F"], ["F'"]],
                ]
                columns = [
                    [["L"], ["L'"]],
                    [["l"], ["l'"]],
                    [["r'"], ["r"]],
                    [["R'"], ["R"]],
                ]
                move = [rows[row][index2], columns[column][index3]][index1]
            elif side == 4:
                rows = [
                    [["U'"], ["U"]],
                    [["u'"], ["u"]],
                    [["d"], ["d'"]],
                    [["D"], ["D'"]],
                ]
                columns = [
                    [["F"], ["F'"]],
                    [["f"], ["f'"]],
                    [["b'"], ["b"]],
                    [["B'"], ["B"]],
                ]
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
