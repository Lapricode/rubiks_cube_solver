"""Cube rendering and view controls."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Sequence

from ..config import Face
from ..cube import Cube, Move, copy_cube


class CubeGraphicsMixin:
    def change_cube_view(self, cube: Cube, move: Move, event: tk.Event) -> None:
        try:
            self.reset_cube_view_button.destroy()
        except AttributeError:
            pass
        self.reset_cube_view_button = self._button(
            self.cube_background,
            "reset cube view",
            "Arial 12 bold",
            "red",
            "cyan",
            self.cube_background_width / 2,
            18,
            self.reset_cube_view,
        )
        self.adjust_cube_view_moves.append(move)
        self.make_cube_graphics(cube, None)

    def reset_cube_view(self, event: tk.Event | None = None) -> None:
        try:
            self.reset_cube_view_button.destroy()
        except AttributeError:
            pass
        self.adjust_cube_view_moves = []
        self.make_cube_graphics(self.rubiks_cube, None)

    def draw_cube_side(
        self,
        background: tk.Canvas,
        tags_are_binded: bool,
        cube_side_info: str,
        cube_face_oriented: list[list[str]],
        borders_width: float,
        piece_left_side_length: float,
        piece_down_side_length: float,
        piece_left_side_angle: float,
        piece_down_side_angle: float,
        cube_face_down_left_point: Sequence[float],
    ) -> None:
        cf = cube_face_oriented
        size = len(cf)
        cfdl = cube_face_down_left_point
        ps1 = piece_left_side_length
        ps2 = piece_down_side_length
        pa1 = math.radians(piece_left_side_angle)
        pa2 = math.radians(piece_down_side_angle)
        color_names = self.cube_colors + ["cyan"]
        cf_colors = [
            [color_names[["b", "y", "o", "w", "r", "g", "c"].index(cf[i][j])] for j in range(size)]
            for i in range(size)
        ]
        left_x = ps1 * math.cos(pa1)
        left_y = -ps1 * math.sin(pa1)
        down_x = ps2 * math.cos(pa2)
        down_y = -ps2 * math.sin(pa2)

        for row in range(size):
            row_offset = size - 1 - row
            for column in range(size):
                x = cfdl[0] + row_offset * left_x + column * down_x
                y = cfdl[1] + row_offset * left_y + column * down_y
                color = cf_colors[row][column]
                background.create_polygon(
                    [
                        x,
                        y,
                        x + down_x,
                        y + down_y,
                        x + down_x + left_x,
                        y + down_y + left_y,
                        x + left_x,
                        y + left_y,
                    ],
                    fill=color,
                    activefill=self.highlight_cube_piece(color),
                    width=borders_width,
                    outline="black",
                    tags=f"piece_{row}_{column}_{cube_side_info}",
                )

        if not tags_are_binded:
            return
        for row in range(size):
            for column in range(size):
                tag = f"piece_{row}_{column}_{cube_side_info}"
                position = f"{row}{column}"
                if self.game_state == "draw_scramble":
                    background.tag_bind(
                        tag,
                        "<Button-1>",
                        lambda event, side=cube_side_info, p=position, bg=background: (
                            self.draw_scramble_piece_pressed(bg, f"{side}{p}", event)
                        ),
                    )
                else:
                    background.tag_bind(
                        tag,
                        "<Button-1>",
                        lambda event, side=cube_side_info, p=position: self.cube_moves_mouse_events(
                            f"{side}{p}", event
                        ),
                    )

    def draw_scramble_piece_pressed(
        self, background: tk.Canvas, cube_side_info: str, event: tk.Event
    ) -> None:
        adjust_cube_view_moves_copy = self.adjust_cube_view_moves[:]
        self.reset_cube_view()
        self.rubiks_cube = self.make_moves_sequence(
            self.rubiks_cube, adjust_cube_view_moves_copy, False
        )
        piece = event.widget.find_closest(event.x, event.y)
        background.itemconfigure(piece, fill=self.chosen_draw_color)
        piece_loc_0, piece_loc_1, piece_loc_2 = (
            int(cube_side_info[0]),
            int(cube_side_info[1]),
            int(cube_side_info[2]),
        )
        if piece_loc_0 == 4 and self.cube_dimensions == "3d":
            piece_loc_1_copy = piece_loc_1
            piece_loc_1 = self.cube_size - 1 - piece_loc_2
            piece_loc_2 = piece_loc_1_copy
        self.rubiks_cube[piece_loc_0][piece_loc_1][piece_loc_2] = self.chosen_draw_color[0]
        self.draw_scrambled_rubiks_cube = copy_cube(self.rubiks_cube)
        self.play_sound("draw_cube_sound", "sound")
        self.make_cube_graphics(self.rubiks_cube, None)

    def highlight_cube_piece(self, color: str) -> str:
        if self.game_state != "draw_scramble":
            return ["#0000aa", "#cccc00", "#cd8500", "#cccccc", "#aa0000", "#00aa00", "cyan"][
                (self.cube_colors + ["cyan"]).index(color)
            ]
        return self.chosen_draw_color

    def make_cube_graphics(self, main_cube: Cube, move: Move | None) -> None:
        n = self.cube_size
        if self.game_state in ["moves_scramble", "self_solve"] or (
            self.game_state == "auto_solve"
            and self.previous_game_state in ["moves_scramble", "self_solve"]
        ):
            scrambled_cube = self.moves_scrambled_rubiks_cube
        elif self.game_state == "draw_scramble" or (
            self.game_state == "auto_solve" and self.previous_game_state == "draw_scramble"
        ):
            scrambled_cube = self.draw_scrambled_rubiks_cube
        self.cube_background.delete("all")
        rubiks_cube_view = self.make_moves_sequence(main_cube, self.adjust_cube_view_moves, False)
        scrambled_rubiks_cube_view = self.make_moves_sequence(
            scrambled_cube, self.adjust_cube_view_moves, False
        )
        if self.cube_dimensions == "3d":
            # For visible_cube.
            centre_offset = n / 2 * self.sides_distortion * self.piece_side_length / math.sqrt(2)
            self.front_cube_side_centre = [
                self.visible_cube_centre_x - centre_offset,
                self.visible_cube_centre_y + centre_offset,
            ]
            self.draw_cube_side(
                self.cube_background,
                True,
                "5",
                rubiks_cube_view[Face.FRONT],
                5 * self.borders_width,
                self.piece_side_length,
                self.piece_side_length,
                90,
                0,
                [
                    self.front_cube_side_centre[0] - n * self.piece_side_length / 2,
                    self.front_cube_side_centre[1] + n * self.piece_side_length / 2,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                True,
                "3",
                rubiks_cube_view[Face.UP],
                5 * self.borders_width,
                self.piece_side_length * self.sides_distortion,
                self.piece_side_length,
                45,
                0,
                [
                    self.front_cube_side_centre[0] - n * self.piece_side_length / 2,
                    self.front_cube_side_centre[1] - n * self.piece_side_length / 2,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                True,
                "4",
                [[rubiks_cube_view[Face.RIGHT][n - 1 - j][i] for j in range(n)] for i in range(n)],
                5 * self.borders_width,
                self.piece_side_length,
                self.piece_side_length * self.sides_distortion,
                90,
                45,
                [
                    self.front_cube_side_centre[0] + n * self.piece_side_length / 2,
                    self.front_cube_side_centre[1] + n * self.piece_side_length / 2,
                ],
            )
            if self.axis_visibility == "on":
                self.cube_background.create_line(
                    self.front_cube_side_centre[0]
                    - n * self.piece_side_length * (1 / 2 - self.sides_distortion / math.sqrt(2)),
                    self.front_cube_side_centre[1]
                    - n * self.piece_side_length * (1 / 2 + self.sides_distortion / math.sqrt(2)),
                    self.front_cube_side_centre[0]
                    - n * self.piece_side_length * (1 / 2 - self.sides_distortion / math.sqrt(2)),
                    self.front_cube_side_centre[1]
                    - n * self.piece_side_length * (1 / 2 + self.sides_distortion / math.sqrt(2))
                    - 50,
                    width=5,
                    fill="black",
                    activefill="white",
                )
                self.cube_background.create_text(
                    self.front_cube_side_centre[0]
                    - n * self.piece_side_length * (1 / 2 - self.sides_distortion / math.sqrt(2))
                    - 10,
                    self.front_cube_side_centre[1]
                    - n * self.piece_side_length * (1 / 2 + self.sides_distortion / math.sqrt(2))
                    - 50,
                    text="z",
                    font="Times 20 bold",
                    fill="black",
                    activefill="purple",
                )
                self.cube_background.create_line(
                    self.front_cube_side_centre[0]
                    + n * self.piece_side_length * (1 / 2 + self.sides_distortion / math.sqrt(2)),
                    self.front_cube_side_centre[1]
                    + n * self.piece_side_length * (1 / 2 - self.sides_distortion / math.sqrt(2)),
                    self.front_cube_side_centre[0]
                    + n * self.piece_side_length * (1 / 2 + self.sides_distortion / math.sqrt(2))
                    + 50,
                    self.front_cube_side_centre[1]
                    + n * self.piece_side_length * (1 / 2 - self.sides_distortion / math.sqrt(2)),
                    width=5,
                    fill="black",
                    activefill="white",
                )
                self.cube_background.create_text(
                    self.front_cube_side_centre[0]
                    + n * self.piece_side_length * (1 / 2 + self.sides_distortion / math.sqrt(2))
                    + 60,
                    self.front_cube_side_centre[1]
                    + n * self.piece_side_length * (1 / 2 - self.sides_distortion / math.sqrt(2))
                    - 5,
                    text="y",
                    font="Times 20 bold",
                    fill="black",
                    activefill="purple",
                )
                self.cube_background.create_line(
                    self.front_cube_side_centre[0] - n * self.piece_side_length / 2,
                    self.front_cube_side_centre[1] + n * self.piece_side_length / 2,
                    self.front_cube_side_centre[0]
                    - n * self.piece_side_length / 2
                    - 50 / math.sqrt(2),
                    self.front_cube_side_centre[1]
                    + n * self.piece_side_length / 2
                    + 50 / math.sqrt(2),
                    width=5,
                    fill="black",
                    activefill="white",
                )
                self.cube_background.create_text(
                    self.front_cube_side_centre[0]
                    - n * self.piece_side_length / 2
                    - 50 / math.sqrt(2),
                    self.front_cube_side_centre[1]
                    + n * self.piece_side_length / 2
                    + 50 / math.sqrt(2)
                    + 10,
                    text="x",
                    font="Times 20 bold",
                    fill="black",
                    activefill="purple",
                )
            # For hidden_layers.
            if self.hidden_sides_visibility == "on":
                self.draw_cube_side(
                    self.cube_background,
                    False,
                    "None",
                    [
                        [rubiks_cube_view[Face.BACK][n - 1 - i][j] for j in range(n)]
                        for i in range(n)
                    ],
                    0,
                    self.hidden_side_length,
                    self.hidden_side_length,
                    90,
                    0,
                    [self.hidden_cube_centre_x, self.hidden_cube_centre_y],
                )
                self.draw_cube_side(
                    self.cube_background,
                    False,
                    "None",
                    [
                        [rubiks_cube_view[Face.DOWN][i][n - 1 - j] for j in range(n)]
                        for i in range(n)
                    ],
                    0,
                    self.hidden_side_length * self.sides_distortion,
                    self.hidden_side_length,
                    45,
                    0,
                    [
                        self.hidden_cube_centre_x
                        - n * self.hidden_side_length * self.sides_distortion / math.sqrt(2),
                        self.hidden_cube_centre_y
                        + n * self.hidden_side_length * self.sides_distortion / math.sqrt(2),
                    ],
                )
                self.draw_cube_side(
                    self.cube_background,
                    False,
                    "None",
                    [
                        [rubiks_cube_view[Face.LEFT][n - 1 - j][n - 1 - i] for j in range(n)]
                        for i in range(n)
                    ],
                    0,
                    self.hidden_side_length,
                    self.hidden_side_length * self.sides_distortion,
                    90,
                    45,
                    [
                        self.hidden_cube_centre_x
                        - n * self.hidden_side_length * self.sides_distortion / math.sqrt(2),
                        self.hidden_cube_centre_y
                        + n * self.hidden_side_length * self.sides_distortion / math.sqrt(2),
                    ],
                )
            if self.hidden_sides_visibility == "on" and self.axis_visibility == "on":
                self.cube_background.create_line(
                    self.hidden_cube_centre_x,
                    self.hidden_cube_centre_y,
                    self.hidden_cube_centre_x,
                    self.hidden_cube_centre_y - n * self.hidden_side_length - 10,
                    width=3,
                    fill="black",
                    activefill="white",
                )
                self.cube_background.create_text(
                    self.hidden_cube_centre_x - 10,
                    self.hidden_cube_centre_y - n * self.hidden_side_length - 10,
                    text="z",
                    font="Times 15 bold",
                    fill="black",
                    activefill="purple",
                )
                self.cube_background.create_line(
                    self.hidden_cube_centre_x,
                    self.hidden_cube_centre_y,
                    self.hidden_cube_centre_x + n * self.hidden_side_length + 10,
                    self.hidden_cube_centre_y,
                    width=3,
                    fill="black",
                    activefill="white",
                )
                self.cube_background.create_text(
                    self.hidden_cube_centre_x + n * self.hidden_side_length + 20,
                    self.hidden_cube_centre_y - 5,
                    text="y",
                    font="Times 15 bold",
                    fill="black",
                    activefill="purple",
                )
                self.cube_background.create_line(
                    self.hidden_cube_centre_x,
                    self.hidden_cube_centre_y,
                    self.hidden_cube_centre_x
                    - (n * self.hidden_side_length * self.sides_distortion + 10) / math.sqrt(2),
                    self.hidden_cube_centre_y
                    + (n * self.hidden_side_length * self.sides_distortion + 10) / math.sqrt(2),
                    width=3,
                    fill="black",
                    activefill="white",
                )
                self.cube_background.create_text(
                    self.hidden_cube_centre_x
                    - (n * self.hidden_side_length * self.sides_distortion + 10) / math.sqrt(2),
                    self.hidden_cube_centre_y
                    + (n * self.hidden_side_length * self.sides_distortion + 10) / math.sqrt(2)
                    + 10,
                    text="x",
                    font="Times 15 bold",
                    fill="black",
                    activefill="purple",
                )
                self.cube_background.create_line(
                    self.hidden_cube_centre_x,
                    self.hidden_cube_centre_y,
                    self.hidden_cube_centre_x,
                    self.hidden_cube_centre_y,
                    width=5,
                    fill="black",
                    capstyle="round",
                    activefill="white",
                )
        elif self.cube_dimensions == "2d":
            gap = 10
            self.draw_cube_side(
                self.cube_background,
                True,
                "0",
                rubiks_cube_view[Face.BACK],
                5 * self.borders_width,
                self.piece_side_length,
                self.piece_side_length,
                90,
                0,
                [
                    self.visible_cube_centre_x,
                    self.visible_cube_centre_y - n * self.piece_side_length / 2 - gap,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                True,
                "1",
                rubiks_cube_view[Face.DOWN],
                5 * self.borders_width,
                self.piece_side_length,
                self.piece_side_length,
                90,
                0,
                [
                    self.visible_cube_centre_x - 2 * n * self.piece_side_length - 2 * gap,
                    self.visible_cube_centre_y + n * self.piece_side_length / 2,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                True,
                "2",
                rubiks_cube_view[Face.LEFT],
                5 * self.borders_width,
                self.piece_side_length,
                self.piece_side_length,
                90,
                0,
                [
                    self.visible_cube_centre_x - n * self.piece_side_length - gap,
                    self.visible_cube_centre_y + n * self.piece_side_length / 2,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                True,
                "3",
                rubiks_cube_view[Face.UP],
                5 * self.borders_width,
                self.piece_side_length,
                self.piece_side_length,
                90,
                0,
                [
                    self.visible_cube_centre_x,
                    self.visible_cube_centre_y + n * self.piece_side_length / 2,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                True,
                "4",
                rubiks_cube_view[Face.RIGHT],
                5 * self.borders_width,
                self.piece_side_length,
                self.piece_side_length,
                90,
                0,
                [
                    self.visible_cube_centre_x + n * self.piece_side_length + gap,
                    self.visible_cube_centre_y + n * self.piece_side_length / 2,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                True,
                "5",
                rubiks_cube_view[Face.FRONT],
                5 * self.borders_width,
                self.piece_side_length,
                self.piece_side_length,
                90,
                0,
                [
                    self.visible_cube_centre_x,
                    self.visible_cube_centre_y + 3 * n * self.piece_side_length / 2 + gap,
                ],
            )
        if self.scramble_pattern_visibility == "on":
            gap = 2
            self.draw_cube_side(
                self.cube_background,
                False,
                "None",
                scrambled_rubiks_cube_view[Face.BACK],
                1,
                15,
                15,
                90,
                0,
                [
                    self.scrambled_pattern_centre_x,
                    self.scrambled_pattern_centre_y - n * 15 / 2 - gap,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                False,
                "None",
                scrambled_rubiks_cube_view[Face.DOWN],
                1,
                15,
                15,
                90,
                0,
                [
                    self.scrambled_pattern_centre_x - 2 * n * 15 - 2 * gap,
                    self.scrambled_pattern_centre_y + n * 15 / 2,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                False,
                "None",
                scrambled_rubiks_cube_view[Face.LEFT],
                1,
                15,
                15,
                90,
                0,
                [
                    self.scrambled_pattern_centre_x - n * 15 - gap,
                    self.scrambled_pattern_centre_y + n * 15 / 2,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                False,
                "None",
                scrambled_rubiks_cube_view[Face.UP],
                1,
                15,
                15,
                90,
                0,
                [self.scrambled_pattern_centre_x, self.scrambled_pattern_centre_y + n * 15 / 2],
            )
            self.draw_cube_side(
                self.cube_background,
                False,
                "None",
                scrambled_rubiks_cube_view[Face.RIGHT],
                1,
                15,
                15,
                90,
                0,
                [
                    self.scrambled_pattern_centre_x + n * 15 + gap,
                    self.scrambled_pattern_centre_y + n * 15 / 2,
                ],
            )
            self.draw_cube_side(
                self.cube_background,
                False,
                "None",
                scrambled_rubiks_cube_view[Face.FRONT],
                1,
                15,
                15,
                90,
                0,
                [
                    self.scrambled_pattern_centre_x,
                    self.scrambled_pattern_centre_y + 3 * n * 15 / 2 + gap,
                ],
            )
        if move is not None:
            self.cube_background.create_text(
                self.cube_background_width / 2,
                self.cube_background_height - 20,
                text=move,
                font="Calibri 20 bold",
                fill="black",
            )
        if self.cube_is_solved(self.rubiks_cube):
            self.cube_background.create_text(
                self.cube_background_width - 75,
                self.cube_background_height - 20,
                text="solved",
                font="Calibri 25 bold",
                fill="green",
            )
        else:
            self.cube_background.create_text(
                self.cube_background_width - 75,
                self.cube_background_height - 20,
                text="scrambled",
                font="Calibri 25 bold",
                fill="red",
            )
