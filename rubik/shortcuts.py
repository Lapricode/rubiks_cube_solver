"""Persistent keyboard shortcut bindings for GUI actions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DEFAULT_SHORTCUTS

SHORTCUTS_PATH = Path.home() / ".rubiks_cube_solver_shortcuts.json"


def load_shortcuts(path: Path | None = None) -> dict[str, str]:
    shortcuts = dict(DEFAULT_SHORTCUTS)
    shortcut_path = path or SHORTCUTS_PATH
    try:
        data: Any = json.loads(shortcut_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return shortcuts
    if isinstance(data, dict):
        for action, sequence in data.items():
            if action in shortcuts and isinstance(sequence, str) and sequence:
                shortcuts[action] = sequence
    return shortcuts


def save_shortcuts(shortcuts: dict[str, str], path: Path | None = None) -> None:
    shortcut_path = path or SHORTCUTS_PATH
    try:
        shortcut_path.write_text(json.dumps(shortcuts, indent=2), encoding="utf-8")
    except OSError:
        pass
