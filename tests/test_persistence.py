import json

import pytest

from rubik.cube import InvalidCubeError, apply_moves, solved_cube
from rubik.persistence import (
    cube_from_data,
    cube_to_data,
    export_solution,
    load_state,
    save_state,
)


def test_cube_state_round_trip(tmp_path) -> None:
    cube = apply_moves(solved_cube(4), ["Rw", "U2", "F'", "r"])
    path = tmp_path / "state.json"

    save_state(path, cube, ["R", "U"])
    loaded, moves = load_state(path)

    assert loaded == cube
    assert moves == ["R", "U"]


def test_cube_data_round_trip_preserves_blank_draw_cube() -> None:
    cube = solved_cube(2)
    cube[0][0][0] = "c"
    data = cube_to_data(cube)

    assert cube_from_data(data) == cube


def test_load_state_rejects_malformed_data(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"cube": {"size": 9, "faces": []}}), encoding="utf-8")

    with pytest.raises(InvalidCubeError):
        load_state(path)


def test_export_solution_writes_stages(tmp_path) -> None:
    path = tmp_path / "solution.txt"
    export_solution(
        path,
        ["R", "U"],
        method="Test method",
        stages=[["R"], ["U"]],
        notes=["First", "Second"],
    )

    content = path.read_text(encoding="utf-8")
    assert "Test method" in content
    assert "R U" in content
    assert "First: R" in content
    assert "Second: U" in content
