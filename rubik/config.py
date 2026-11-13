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

MIN_CUBE_SIZE = 2
MAX_CUBE_SIZE = 100
CUBE_SIZES = list(range(MIN_CUBE_SIZE, MAX_CUBE_SIZE + 1))
DEFAULT_CUBE_SIZE = 3


def piece_side_length_for_size(size: int) -> float:
    return max(3.0, min(150.0, 300.0 / size))


def piece_side_length_limits(size: int) -> tuple[float, float]:
    return max(0.8, 80.0 / size), max(4.0, min(200.0, 600.0 / size))


def auxiliary_piece_side_length(size: int, footprint: float = 60.0, maximum: float = 20.0) -> float:
    return max(0.5, min(maximum, footprint / size))


CUBE_DIMENSIONS = ["2d", "3d"]
BORDERS_WIDTHS = [0, 1, 2, 3]
SIDES_DISTORTIONS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
MOVE_SPEEDS = [0.0, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
REPLAY_SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0]
TURN_ANIMATION_DURATIONS = [0, 60, 100, 160, 240, 400]
RANDOM_SCRAMBLE_MOVE_COUNTS = [0, 1, 5, 10, 25, 50, 100]
MAX_SCRAMBLE_MOVES = 100

THEMES = {
    "classic": {
        "menu_bg": "black",
        "menu_title": "#ffeb3b",
        "menu_label": "#ff5a5a",
        "menu_text": "#ffffff",
        "button_bg": "#000000",
        "button_fg": "#ffffff",
        "button_hover": "#262626",
        "button_outline": "#5a5a5a",
        "bottom_bg": "yellow",
        "bottom_title": "#8b4513",
        "bottom_text": "#000000",
        "bottom_muted": "#800080",
        "bottom_accent": "#00006e",
        "cube_bg": "cyan",
        "colors": COLOR_NAMES,
    },
    "dark": {
        "menu_bg": "#101418",
        "menu_title": "#ffd166",
        "menu_label": "#ff7b72",
        "menu_text": "#f2f5f7",
        "button_bg": "#26313d",
        "button_fg": "#f2f5f7",
        "button_hover": "#354456",
        "button_outline": "#66788d",
        "bottom_bg": "#1b222b",
        "bottom_title": "#ffd166",
        "bottom_text": "#f2f5f7",
        "bottom_muted": "#c792ea",
        "bottom_accent": "#8be9fd",
        "cube_bg": "#0b0f14",
        "colors": COLOR_NAMES,
    },
    "high contrast": {
        "menu_bg": "#000000",
        "menu_title": "#ffff00",
        "menu_label": "#ff3333",
        "menu_text": "#ffffff",
        "button_bg": "#000000",
        "button_fg": "#ffffff",
        "button_hover": "#333333",
        "button_outline": "#ffffff",
        "bottom_bg": "#000000",
        "bottom_title": "#ffff00",
        "bottom_text": "#ffffff",
        "bottom_muted": "#00ffff",
        "bottom_accent": "#00ff00",
        "cube_bg": "#202020",
        "colors": ["#0000ff", "#ffff00", "#ff8000", "#ffffff", "#ff0000", "#00ff00"],
    },
    "colorblind": {
        "menu_bg": "#101820",
        "menu_title": "#f0e442",
        "menu_label": "#e69f00",
        "menu_text": "#ffffff",
        "button_bg": "#1f2d3d",
        "button_fg": "#ffffff",
        "button_hover": "#2f4358",
        "button_outline": "#8fa8bf",
        "bottom_bg": "#e8eef2",
        "bottom_title": "#005b7f",
        "bottom_text": "#111111",
        "bottom_muted": "#7a3e00",
        "bottom_accent": "#005b7f",
        "cube_bg": "#d9e2e8",
        "colors": ["#0072b2", "#f0e442", "#e69f00", "#ffffff", "#d55e00", "#009e73"],
    },
}
THEME_NAMES = list(THEMES)

DEFAULT_SHORTCUTS = {
    "undo": "<Control-z>",
    "redo": "<Control-y>",
    "save": "<Control-s>",
    "load": "<Control-o>",
    "export": "<Control-e>",
    "stats": "<Control-t>",
    "shortcuts": "<F1>",
    "tutorial": "<Control-g>",
    "theme": "<Control-Shift-T>",
    "smooth": "<Control-m>",
}
SHORTCUT_LABELS = {
    "undo": "Undo move",
    "redo": "Redo move",
    "save": "Save cube state",
    "load": "Load cube state",
    "export": "Export solution",
    "stats": "Show statistics",
    "shortcuts": "Shortcut overlay",
    "tutorial": "Toggle tutorial hints",
    "theme": "Cycle theme",
    "smooth": "Toggle smooth turns",
}

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
