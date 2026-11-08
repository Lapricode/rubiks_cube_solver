"""Save, load and export helpers for cube states and solutions."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .config import Face
from .cube import Cube, InvalidCubeError, cube_size, validate_cube

STATE_VERSION = 1


def cube_to_data(cube: Cube) -> dict[str, Any]:
    return {
        "size": cube_size(cube),
        "faces": ["".join("".join(row) for row in face) for face in cube],
    }


def cube_from_data(data: Any) -> Cube:
    if not isinstance(data, dict):
        raise InvalidCubeError("Saved cube data is malformed.")
    size = data.get("size")
    faces = data.get("faces")
    if not isinstance(size, int) or size < 2:
        raise InvalidCubeError("Saved cube size is invalid.")
    if not isinstance(faces, list) or len(faces) != len(Face):
        raise InvalidCubeError("Saved cube must contain six faces.")
    cube: Cube = []
    for index, face in enumerate(faces):
        if not isinstance(face, str) or len(face) != size * size:
            raise InvalidCubeError(f"Saved face {index} does not match the cube size.")
        cube.append([list(face[row * size : (row + 1) * size]) for row in range(size)])
    try:
        validate_cube(cube)
    except InvalidCubeError:
        if any(cell == "c" for face in cube for row in face for cell in row):
            return cube
        raise
    return cube


def save_state(path: str | Path, cube: Cube, moves: Sequence[str] | None = None) -> None:
    data = {
        "version": STATE_VERSION,
        "cube": cube_to_data(cube),
        "moves": list(moves or []),
    }
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_state(path: str | Path) -> tuple[Cube, list[str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise InvalidCubeError("Saved file is malformed.")
    cube = cube_from_data(data.get("cube"))
    raw_moves = data.get("moves", [])
    moves = (
        [move for move in raw_moves if isinstance(move, str)] if isinstance(raw_moves, list) else []
    )
    return cube, moves


def export_solution(
    path: str | Path,
    moves: Sequence[str],
    method: str = "Solution",
    stages: Sequence[Sequence[str]] | None = None,
    notes: Sequence[str] | None = None,
) -> None:
    lines = [f"{method}", "", "Moves:", " ".join(moves) or "(none)"]
    if stages and notes and len(stages) == len(notes):
        lines.extend(["", "Stages:"])
        for note, stage_moves in zip(notes, stages, strict=True):
            lines.append(f"- {note}: {' '.join(stage_moves) or '(none)'}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
