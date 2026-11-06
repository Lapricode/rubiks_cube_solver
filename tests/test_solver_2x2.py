from rubik.cube import apply_moves, is_solved, solved_cube
from rubik.solver_2x2 import solve_2x2

SCRAMBLE = ["R", "U", "R'", "U'", "F2", "L", "D'", "B", "R2", "F"]


def test_solver_2x2_solves_scramble() -> None:
    cube = apply_moves(solved_cube(2), SCRAMBLE)
    moves, stages, solved = solve_2x2(cube)

    assert stages == [moves]
    assert is_solved(solved)
    assert is_solved(apply_moves(cube, moves))


def test_solver_2x2_already_solved() -> None:
    moves, stages, solved = solve_2x2(solved_cube(2))

    assert moves == []
    assert stages == []
    assert is_solved(solved)


def test_solver_2x2_handles_cube_rotation() -> None:
    cube = apply_moves(solved_cube(2), ["x", "y'", "z2"])
    moves, _stages, solved = solve_2x2(cube)

    assert is_solved(solved)
    assert is_solved(apply_moves(cube, moves))
