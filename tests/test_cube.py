import pytest

from rubik.config import Face
from rubik.cube import (
    InvalidCubeError,
    apply_move,
    apply_moves,
    blank_cube,
    cube_signature,
    face_centres,
    improve_moves_sequence,
    is_solved,
    solved_cube,
    validate_cube,
)


def test_solved_cube_is_solved() -> None:
    cube = solved_cube()
    validate_cube(cube)
    assert is_solved(cube)
    assert face_centres(cube) == ["b", "y", "o", "w", "r", "g"]


def test_every_move_has_an_inverse() -> None:
    moves = [
        "R",
        "L",
        "U",
        "D",
        "F",
        "B",
        "M",
        "E",
        "S",
        "x",
        "y",
        "z",
    ]
    for move in moves:
        cube = apply_moves(solved_cube(), [move, move, move, move])
        assert is_solved(cube), move


def test_unknown_move_raises() -> None:
    with pytest.raises(ValueError, match="Unknown move"):
        apply_move(solved_cube(), "Q")


def test_validate_rejects_bad_color_counts() -> None:
    with pytest.raises(InvalidCubeError):
        validate_cube(blank_cube())


def test_validate_rejects_duplicate_centres() -> None:
    cube = solved_cube()
    cube[Face.FRONT][1][1] = cube[Face.UP][1][1]
    with pytest.raises(InvalidCubeError):
        validate_cube(cube)


def test_validate_rejects_bad_face_shape() -> None:
    cube = solved_cube()
    cube[Face.FRONT].pop()
    with pytest.raises(InvalidCubeError):
        validate_cube(cube)


def test_cube_signature_changes_with_state() -> None:
    cube = solved_cube()
    assert cube_signature(cube) == cube_signature(solved_cube())
    assert cube_signature(cube) != cube_signature(apply_move(cube, "R"))


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [
        (["R", "R"], ["R2"]),
        (["R", "R'"], []),
        (["R", "R", "R", "R"], []),
        (["R", "R", "R"], ["R'"]),
        (["R'", "R'"], ["R2"]),
        (["R", "L"], ["R", "L"]),
    ],
)
def test_improve_moves_sequence(sequence: list[str], expected: list[str]) -> None:
    assert improve_moves_sequence(sequence) == expected


def test_solved_2x2_cube() -> None:
    cube = solved_cube(2)
    validate_cube(cube)
    assert is_solved(cube)
    assert face_centres(cube) == ["b", "y", "o", "w", "r", "g"]
    assert not is_solved(blank_cube("c", 2))


def test_2x2_outer_moves_have_inverses() -> None:
    for move in ["R", "L", "U", "D", "F", "B"]:
        cube = apply_moves(solved_cube(2), [move, move, move, move])
        assert is_solved(cube), move


def test_2x2_rejects_middle_slice_moves() -> None:
    with pytest.raises(ValueError, match="even-sized"):
        apply_move(solved_cube(2), "M")
    with pytest.raises(ValueError, match="even-sized"):
        apply_move(solved_cube(2), "E")
    with pytest.raises(ValueError, match="even-sized"):
        apply_move(solved_cube(2), "S")


def test_2x2_rotations_have_order_four() -> None:
    for move in ["x", "y", "z"]:
        cube = apply_moves(solved_cube(2), [move, move, move, move])
        assert is_solved(cube), move
