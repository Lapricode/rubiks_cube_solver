import tkinter as tk
from types import SimpleNamespace

import pytest

from rubik.ui.app import RubiksCubeApp


def make_app(size: int) -> RubiksCubeApp:
    app = RubiksCubeApp.__new__(RubiksCubeApp)
    app.cube_size = size
    app.cube_dimensions = "3d"
    app.rubiks_cube = []
    app.mouse_move_info = None
    app.selected_moves = []
    app.make_moves_sequence = lambda cube, move, *args, **kwargs: (
        app.selected_moves.append(move),
        cube,
    )[1]
    return app


def drag(app: RubiksCubeApp, piece_info: str, dx: int, dy: int) -> list[str]:
    press = SimpleNamespace(type=tk.EventType.ButtonPress, x=100, y=100)
    release = SimpleNamespace(type=tk.EventType.ButtonRelease, x=100 + dx, y=100 + dy)
    app.cube_moves_mouse_events(piece_info, press)
    app.cube_moves_mouse_events(None, release)
    return app.selected_moves[-1]


@pytest.mark.parametrize("size", [12, 100])
def test_multi_digit_rows_and_columns_select_the_dragged_layer(size: int) -> None:
    app = make_app(size)
    assert drag(app, "5:0:0", 30, 0) == ["U'"]
    assert drag(app, f"5:{size - 1}:0", 30, 0) == ["D"]
    assert drag(app, f"5:{size - 2}:0", 30, 0) == ["2D"]
    assert drag(app, "5:0:0", 0, 30) == ["L"]
    assert drag(app, f"5:0:{size - 1}", 0, 30) == ["R'"]


def test_animation_directions_match_turn_geometry() -> None:
    assert RubiksCubeApp._turn_animation_direction("U") == (-1, 0)
    assert RubiksCubeApp._turn_animation_direction("D") == (1, 0)
    assert RubiksCubeApp._turn_animation_direction("R") == (0, -1)
    assert RubiksCubeApp._turn_animation_direction("L") == (0, 1)
    assert RubiksCubeApp._turn_animation_direction("F") == (1, 0)
    assert RubiksCubeApp._turn_animation_direction("B") == (-1, 0)
    assert RubiksCubeApp._turn_animation_direction("3Rw") == (0, -1)
    assert RubiksCubeApp._turn_animation_direction("12U") == (-1, 0)
