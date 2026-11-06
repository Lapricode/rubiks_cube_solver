"""Shared constants and asset locations for the application."""

from enum import IntEnum
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SOUNDS_DIR = BASE_DIR / "game_sounds"
ICON_PATH = BASE_DIR / "rubiks_cube_icon.png"
NOTATION_IMAGE_PATH = BASE_DIR / "rubiks_cube_notation.jpg"


# Face order used by the cube model: back, down, left, up, right, front.
class Face(IntEnum):
    BACK = 0
    DOWN = 1
    LEFT = 2
    UP = 3
    RIGHT = 4
    FRONT = 5


FACE_COLORS = ["b", "y", "o", "w", "r", "g"]
FACE_SIZE = 3
CENTER = 1
COLOR_NAMES = ["blue", "yellow", "orange", "white", "red", "green"]

CUBE_SIZES = [2, 3]
DEFAULT_CUBE_SIZE = 3
CUBE_DIMENSIONS = ["2d", "3d"]
BORDERS_WIDTHS = [0, 1, 2, 3]
SIDES_DISTORTIONS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
MOVE_SPEEDS = [0.0, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
RANDOM_SCRAMBLE_MOVE_COUNTS = [0, 1, 5, 10, 25, 50, 100]
MAX_SCRAMBLE_MOVES = 100

DEFAULT_MENUS_FONT = 20
DEFAULT_OPTIONS_FONT = 16
DEFAULT_BUTTONS_FONT = 14

MOVE_KEY_BINDINGS = [
    ("r", "R"),
    ("R", "R'"),
    ("l", "L"),
    ("L", "L'"),
    ("u", "U"),
    ("U", "U'"),
    ("d", "D"),
    ("D", "D'"),
    ("f", "F"),
    ("F", "F'"),
    ("b", "B"),
    ("B", "B'"),
    ("m", "M"),
    ("M", "M'"),
    ("e", "E"),
    ("E", "E'"),
    ("s", "S"),
    ("S", "S'"),
    ("x", "x"),
    ("X", "x'"),
    ("y", "y"),
    ("Y", "y'"),
    ("z", "z"),
    ("Z", "z'"),
]

SPECIAL_MOVE_KEY_BINDINGS = [
    ("<Key-Left>", "y"),
    ("<Key-Right>", "y'"),
    ("<Key-Up>", "x"),
    ("<Key-Down>", "x'"),
]

VIEW_KEY_BINDINGS = [
    ("4", "y"),
    ("6", "y'"),
    ("8", "x"),
    ("2", "x'"),
]
