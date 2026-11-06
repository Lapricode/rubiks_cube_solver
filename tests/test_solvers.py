import sys
import types

import pytest

from rubik.cube import (
    InvalidCubeError,
    apply_moves,
    blank_cube,
    is_solved,
    solved_cube,
)
from rubik.solvers import (
    SolverFailedError,
    SolverLibraryNotInstalledError,
    solve_beginner,
    solve_external,
)

SCRAMBLE = [
    "R",
    "U",
    "R'",
    "U'",
    "F",
    "R",
    "F'",
    "L",
    "D",
    "B'",
    "R2",
    "U2",
    "F'",
    "L'",
    "D2",
]


@pytest.mark.parametrize("initial_color", ["b", "y", "o", "w", "r", "g"])
def test_beginner_solver_solves_from_every_centre(initial_color: str) -> None:
    cube = apply_moves(solved_cube(), SCRAMBLE)
    stages, solved = solve_beginner(cube, initial_color)

    assert len(stages) == 6
    assert is_solved(solved)
    assert is_solved(apply_moves(cube, [move for stage in stages for move in stage]))


def test_beginner_solver_rejects_invalid_cube() -> None:
    with pytest.raises(InvalidCubeError):
        solve_beginner(blank_cube(), "g")


def test_external_solver_reports_missing_library(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "rubik_solver", None)

    with pytest.raises(SolverLibraryNotInstalledError):
        solve_external(solved_cube(), "Kociemba")


def test_external_solver_returns_solved_cube(monkeypatch) -> None:
    fake = types.ModuleType("rubik_solver")
    fake.utils = types.SimpleNamespace(solve=lambda cube, method: [])
    monkeypatch.setitem(sys.modules, "rubik_solver", fake)

    moves, stages, solved = solve_external(solved_cube(), "Kociemba")

    assert moves == ["x2", "y"]
    assert stages is None
    assert is_solved(solved)


def test_cfop_solver_returns_stages(monkeypatch) -> None:
    fake = types.ModuleType("rubik_solver")
    fake.utils = types.SimpleNamespace(solve=lambda cube, method: [])
    monkeypatch.setitem(sys.modules, "rubik_solver", fake)

    moves, stages, solved = solve_external(solved_cube(), "CFOP")

    assert moves == ["x2", "y"]
    assert stages is not None
    assert len(stages) == 4
    assert is_solved(solved)


def test_external_solver_wraps_library_errors(monkeypatch) -> None:
    def fail(cube, method):
        raise RuntimeError("library failure")

    fake = types.ModuleType("rubik_solver")
    fake.utils = types.SimpleNamespace(solve=fail)
    monkeypatch.setitem(sys.modules, "rubik_solver", fake)

    with pytest.raises(SolverFailedError, match="library failure"):
        solve_external(solved_cube(), "Kociemba")


def test_external_solver_rejects_invalid_solution(monkeypatch) -> None:
    fake = types.ModuleType("rubik_solver")
    fake.utils = types.SimpleNamespace(solve=lambda cube, method: ["R"])
    monkeypatch.setitem(sys.modules, "rubik_solver", fake)

    with pytest.raises(SolverFailedError, match="invalid solution"):
        solve_external(solved_cube(), "Kociemba")


def test_beginner_solver_rejects_2x2() -> None:
    with pytest.raises(SolverFailedError, match="only supports 3x3"):
        solve_beginner(solved_cube(2), "g")


def test_external_solvers_reject_2x2() -> None:
    with pytest.raises(SolverFailedError, match="only support 3x3"):
        solve_external(solved_cube(2), "Kociemba")
