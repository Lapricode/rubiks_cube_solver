import random

import pytest

from rubik.cube import apply_moves, is_solved, solved_cube
from rubik.solver_5x5 import ALL_MOVES, solve_5x5, solve_5x5_detailed
from rubik.solvers import SolverFailedError


def random_scramble(seed: int) -> list[str]:
    randomizer = random.Random(seed)
    return [randomizer.choice(ALL_MOVES) for _ in range(40)]


def test_solver_5x5_already_solved() -> None:
    moves, stages, solved = solve_5x5(solved_cube(5))

    assert moves == []
    assert stages == []
    assert is_solved(solved)


def test_solver_5x5_rejects_other_sizes() -> None:
    with pytest.raises(SolverFailedError, match="only supports 5x5"):
        solve_5x5(solved_cube(4))


@pytest.mark.parametrize("seed", [20, 21, 22, 23])
def test_solver_5x5_solves_random_scrambles(seed: int) -> None:
    cube = apply_moves(solved_cube(5), random_scramble(seed))
    moves, stages, notes, solved = solve_5x5_detailed(cube)

    assert is_solved(solved)
    assert is_solved(apply_moves(cube, moves))
    assert moves
    assert len(stages) == len(notes)
    assert all(stages)
    assert "Solving centres" in notes
    assert "Solving wings" in notes
    assert "Finishing as a 3x3" in notes
