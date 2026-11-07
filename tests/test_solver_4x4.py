import random

import pytest

from rubik.cube import apply_moves, is_solved, solved_cube
from rubik.solver_4x4 import solve_4x4, solve_4x4_detailed
from rubik.solvers import SolverFailedError

PARITY_SCRAMBLE = [
    "Rw",
    "U'",
    "Lw",
    "Dw",
    "D'",
    "Dw2",
    "L",
    "B'",
    "Fw2",
    "D2",
    "Fw2",
    "U",
    "Lw'",
    "Fw2",
    "F",
    "D",
    "Rw2",
    "D'",
    "Bw'",
    "Bw",
    "L",
    "Lw2",
    "Fw'",
    "L'",
    "U'",
    "Rw2",
    "Lw'",
    "B",
    "R",
    "B",
    "R2",
    "R2",
    "Fw'",
    "R'",
    "Bw'",
    "U2",
    "U2",
    "Fw",
    "Bw2",
    "D'",
]

SCRAMBLE_MOVES = [
    face + suffix for face in ["L", "R", "U", "D", "F", "B"] for suffix in ("", "'", "2")
] + [face + "w" + suffix for face in ["L", "R", "U", "D", "F", "B"] for suffix in ("", "'", "2")]


def random_scramble(seed: int) -> list[str]:
    randomizer = random.Random(seed)
    return [randomizer.choice(SCRAMBLE_MOVES) for _ in range(40)]


def test_solver_4x4_solves_parity_scramble() -> None:
    cube = apply_moves(solved_cube(4), PARITY_SCRAMBLE)
    moves, stages, notes, solved = solve_4x4_detailed(cube)

    assert is_solved(solved)
    assert is_solved(apply_moves(cube, moves))
    assert moves
    assert len(stages) == len(notes)
    assert all(stages)
    assert "Fixing wing parity" in notes
    assert "Fixing 3x3 parity" in notes


def test_solver_4x4_already_solved() -> None:
    moves, stages, solved = solve_4x4(solved_cube(4))

    assert moves == []
    assert stages == []
    assert is_solved(solved)


def test_solver_4x4_rejects_other_sizes() -> None:
    with pytest.raises(SolverFailedError, match="only supports 4x4"):
        solve_4x4(solved_cube(3))


@pytest.mark.parametrize("seed", [10, 11, 12, 13])
def test_solver_4x4_solves_random_scrambles(seed: int) -> None:
    cube = apply_moves(solved_cube(4), random_scramble(seed))
    moves, _stages, solved = solve_4x4(cube)

    assert is_solved(solved)
    assert is_solved(apply_moves(cube, moves))
