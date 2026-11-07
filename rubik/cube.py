"""Rubik's cube state and move operations for 2x2, 3x3 and 4x4 cubes.

A cube is a list of six square faces using the :class:`~rubik.config.Face`
order. Each face is indexed as ``[row][column]``. The cube size is inferred
from the face dimensions, so the same model handles every supported cube.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from .config import FACE_COLORS, FACE_SIZE, Face

Cube = list[list[list[str]]]
Move = str
MoveSequence = Sequence[Move]


class InvalidCubeError(ValueError):
    """Raised when a cube is malformed or has impossible color counts."""


def cube_size(cube: Cube) -> int:
    """Return the side length of ``cube``."""
    if not cube or not cube[0]:
        raise InvalidCubeError("A cube must contain at least one facelet.")
    return len(cube[0])


def solved_cube(size: int = FACE_SIZE) -> Cube:
    """Return a solved cube in the default orientation."""
    return [[[FACE_COLORS[x] for _ in range(size)] for _ in range(size)] for x in range(len(Face))]


def blank_cube(fill: str = "c", size: int = FACE_SIZE) -> Cube:
    """Return a cube with every facelet set to ``fill``."""
    return [[[fill for _ in range(size)] for _ in range(size)] for _ in range(len(Face))]


def copy_cube(cube: Cube) -> Cube:
    size = cube_size(cube)
    return [[[cube[x][y][z] for z in range(size)] for y in range(size)] for x in range(len(Face))]


def validate_cube(cube: Cube) -> None:
    """Validate the cube structure and its color distribution.

    This catches malformed patterns and impossible color counts.  It does not
    attempt full cubie-level solvability; the solvers report that separately.
    """
    if len(cube) != len(Face):
        raise InvalidCubeError(f"A cube must have {len(Face)} faces.")

    size = cube_size(cube)
    for face in cube:
        if len(face) != size or any(len(row) != size for row in face):
            raise InvalidCubeError(f"Every face must be {size}x{size}.")

    counts = Counter(color for face in cube for row in face for color in row)
    unknown_colors = set(counts) - set(FACE_COLORS)
    if unknown_colors:
        raise InvalidCubeError(f"Unknown facelet colors: {sorted(unknown_colors)}.")

    for color in FACE_COLORS:
        if counts[color] != size * size:
            raise InvalidCubeError(f"Color {color!r} must appear exactly {size * size} times.")

    if size % 2 == 1:
        centres = face_centres(cube)
        if len(set(centres)) != len(Face):
            raise InvalidCubeError("Every face must have a different centre color.")


def face_centres(cube: Cube) -> list[str]:
    middle = cube_size(cube) // 2
    return [face[middle][middle] for face in cube]


def face_centre(cube: Cube, face: Face) -> str:
    middle = cube_size(cube) // 2
    return cube[face][middle][middle]


def _rotate_face_clockwise(face: list[list[str]]) -> list[list[str]]:
    size = len(face)
    return [[face[size - 1 - j][i] for j in range(size)] for i in range(size)]


def _left_layer(cube: Cube, depth: int, rotate_face: bool) -> Cube:
    size = cube_size(cube)
    last = size - 1
    column = depth
    down_column = last - depth
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.BACK][i][column] = cube[Face.DOWN][last - i][down_column]
        cube2[Face.DOWN][i][down_column] = cube[Face.FRONT][last - i][column]
        cube2[Face.UP][i][column] = cube[Face.BACK][i][column]
        cube2[Face.FRONT][i][column] = cube[Face.UP][i][column]
    if rotate_face:
        cube2[Face.LEFT] = _rotate_face_clockwise(cube[Face.LEFT])
    return cube2


def left(cube: Cube) -> Cube:
    return _left_layer(cube, 0, True)


def _right_layer(cube: Cube, depth: int, rotate_face: bool) -> Cube:
    size = cube_size(cube)
    last = size - 1
    column = last - depth
    down_column = depth
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.UP][i][column] = cube[Face.FRONT][i][column]
        cube2[Face.FRONT][i][column] = cube[Face.DOWN][last - i][down_column]
        cube2[Face.BACK][i][column] = cube[Face.UP][i][column]
        cube2[Face.DOWN][i][down_column] = cube[Face.BACK][last - i][column]
    if rotate_face:
        cube2[Face.RIGHT] = _rotate_face_clockwise(cube[Face.RIGHT])
    return cube2


def right(cube: Cube) -> Cube:
    return _right_layer(cube, 0, True)


def _up_layer(cube: Cube, depth: int, rotate_face: bool) -> Cube:
    size = cube_size(cube)
    last = size - 1
    back_row = last - depth
    front_row = depth
    left_column = last - depth
    right_column = depth
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.BACK][back_row][i] = cube[Face.LEFT][last - i][left_column]
        cube2[Face.LEFT][i][left_column] = cube[Face.FRONT][front_row][i]
        cube2[Face.RIGHT][i][right_column] = cube[Face.BACK][back_row][i]
        cube2[Face.FRONT][front_row][i] = cube[Face.RIGHT][last - i][right_column]
    if rotate_face:
        cube2[Face.UP] = _rotate_face_clockwise(cube[Face.UP])
    return cube2


def up(cube: Cube) -> Cube:
    return _up_layer(cube, 0, True)


def _down_layer(cube: Cube, depth: int, rotate_face: bool) -> Cube:
    size = cube_size(cube)
    last = size - 1
    back_row = depth
    front_row = last - depth
    left_column = depth
    right_column = last - depth
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.BACK][back_row][i] = cube[Face.RIGHT][i][right_column]
        cube2[Face.LEFT][i][left_column] = cube[Face.BACK][back_row][last - i]
        cube2[Face.RIGHT][i][right_column] = cube[Face.FRONT][front_row][last - i]
        cube2[Face.FRONT][front_row][i] = cube[Face.LEFT][i][left_column]
    if rotate_face:
        cube2[Face.DOWN] = _rotate_face_clockwise(cube[Face.DOWN])
    return cube2


def down(cube: Cube) -> Cube:
    return _down_layer(cube, 0, True)


def _front_layer(cube: Cube, depth: int, rotate_face: bool) -> Cube:
    size = cube_size(cube)
    row = size - 1 - depth
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.DOWN][row][i] = cube[Face.RIGHT][row][i]
        cube2[Face.LEFT][row][i] = cube[Face.DOWN][row][i]
        cube2[Face.UP][row][i] = cube[Face.LEFT][row][i]
        cube2[Face.RIGHT][row][i] = cube[Face.UP][row][i]
    if rotate_face:
        cube2[Face.FRONT] = _rotate_face_clockwise(cube[Face.FRONT])
    return cube2


def front(cube: Cube) -> Cube:
    return _front_layer(cube, 0, True)


def _back_layer(cube: Cube, depth: int, rotate_face: bool) -> Cube:
    size = cube_size(cube)
    row = depth
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.DOWN][row][i] = cube[Face.LEFT][row][i]
        cube2[Face.LEFT][row][i] = cube[Face.UP][row][i]
        cube2[Face.UP][row][i] = cube[Face.RIGHT][row][i]
        cube2[Face.RIGHT][row][i] = cube[Face.DOWN][row][i]
    if rotate_face:
        cube2[Face.BACK] = _rotate_face_clockwise(cube[Face.BACK])
    return cube2


def back(cube: Cube) -> Cube:
    return _back_layer(cube, 0, True)


def inner_right(cube: Cube) -> Cube:
    return _right_layer(cube, 1, False)


def inner_left(cube: Cube) -> Cube:
    return _left_layer(cube, 1, False)


def inner_up(cube: Cube) -> Cube:
    return _up_layer(cube, 1, False)


def inner_down(cube: Cube) -> Cube:
    return _down_layer(cube, 1, False)


def inner_front(cube: Cube) -> Cube:
    return _front_layer(cube, 1, False)


def inner_back(cube: Cube) -> Cube:
    return _back_layer(cube, 1, False)


def wide_right(cube: Cube) -> Cube:
    return _right_layer(_right_layer(cube, 0, True), 1, False)


def wide_left(cube: Cube) -> Cube:
    return _left_layer(_left_layer(cube, 0, True), 1, False)


def wide_up(cube: Cube) -> Cube:
    return _up_layer(_up_layer(cube, 0, True), 1, False)


def wide_down(cube: Cube) -> Cube:
    return _down_layer(_down_layer(cube, 0, True), 1, False)


def wide_front(cube: Cube) -> Cube:
    return _front_layer(_front_layer(cube, 0, True), 1, False)


def wide_back(cube: Cube) -> Cube:
    return _back_layer(_back_layer(cube, 0, True), 1, False)


def _middle_index(cube: Cube) -> int:
    size = cube_size(cube)
    if size % 2 == 0:
        raise ValueError("Middle slice moves are not available on even-sized cubes.")
    return size // 2


def midM(cube: Cube) -> Cube:
    return _left_layer(cube, _middle_index(cube), False)


def midE(cube: Cube) -> Cube:
    return _down_layer(cube, _middle_index(cube), False)


def midS(cube: Cube) -> Cube:
    return _front_layer(cube, _middle_index(cube), False)


def rotx(cube: Cube) -> Cube:
    size = cube_size(cube)
    if size == 2:
        cube2 = right(cube)
        for _ in range(3):
            cube2 = left(cube2)
        return cube2
    if size == 4:
        cube2 = _right_layer(cube, 0, True)
        cube2 = _right_layer(cube2, 1, False)
        cube2 = _left_layer(cube2, 0, True)
        cube2 = _left_layer(cube2, 1, False)
        cube2 = _left_layer(cube2, 0, True)
        cube2 = _left_layer(cube2, 1, False)
        cube2 = _left_layer(cube2, 0, True)
        cube2 = _left_layer(cube2, 1, False)
        return cube2
    if size % 2 == 0:
        raise ValueError("Whole-cube rotations support 2x2, 3x3 and 4x4 cubes.")
    cube2 = right(cube)
    for _ in range(3):
        cube2 = left(cube2)
        cube2 = midM(cube2)
    return cube2


def roty(cube: Cube) -> Cube:
    size = cube_size(cube)
    if size == 2:
        cube2 = up(cube)
        for _ in range(3):
            cube2 = down(cube2)
        return cube2
    if size == 4:
        cube2 = _up_layer(cube, 0, True)
        cube2 = _up_layer(cube2, 1, False)
        cube2 = _down_layer(cube2, 0, True)
        cube2 = _down_layer(cube2, 1, False)
        cube2 = _down_layer(cube2, 0, True)
        cube2 = _down_layer(cube2, 1, False)
        cube2 = _down_layer(cube2, 0, True)
        cube2 = _down_layer(cube2, 1, False)
        return cube2
    if size % 2 == 0:
        raise ValueError("Whole-cube rotations support 2x2, 3x3 and 4x4 cubes.")
    cube2 = up(cube)
    for _ in range(3):
        cube2 = down(cube2)
        cube2 = midE(cube2)
    return cube2


def rotz(cube: Cube) -> Cube:
    size = cube_size(cube)
    if size == 2:
        cube2 = front(cube)
        for _ in range(3):
            cube2 = back(cube2)
        return cube2
    if size == 4:
        cube2 = _front_layer(cube, 0, True)
        cube2 = _front_layer(cube2, 1, False)
        cube2 = _back_layer(cube2, 0, True)
        cube2 = _back_layer(cube2, 1, False)
        cube2 = _back_layer(cube2, 0, True)
        cube2 = _back_layer(cube2, 1, False)
        cube2 = _back_layer(cube2, 0, True)
        cube2 = _back_layer(cube2, 1, False)
        return cube2
    if size % 2 == 0:
        raise ValueError("Whole-cube rotations support 2x2, 3x3 and 4x4 cubes.")
    cube2 = front(cube)
    cube2 = midS(cube2)
    for _ in range(3):
        cube2 = back(cube2)
    return cube2


MOVE_FUNCTIONS = {
    "L": left,
    "R": right,
    "U": up,
    "D": down,
    "F": front,
    "B": back,
    "l": inner_left,
    "r": inner_right,
    "u": inner_up,
    "d": inner_down,
    "f": inner_front,
    "b": inner_back,
    "Lw": wide_left,
    "Rw": wide_right,
    "Uw": wide_up,
    "Dw": wide_down,
    "Fw": wide_front,
    "Bw": wide_back,
    "M": midM,
    "E": midE,
    "S": midS,
    "x": rotx,
    "y": roty,
    "z": rotz,
}


def apply_move(cube: Cube, move: Move) -> Cube:
    if move == "":
        return cube
    if move.endswith("'"):
        move_name = move[:-1]
    elif move.endswith("2"):
        move_name = move[:-1]
    else:
        move_name = move
    try:
        move_function = MOVE_FUNCTIONS[move_name]
    except KeyError as exc:
        raise ValueError(f"Unknown move: {move!r}") from exc
    turns = 2 if move.endswith("2") else 3 if move.endswith("'") else 1
    for _ in range(turns):
        cube = move_function(cube)
    return cube


def apply_moves(cube: Cube, moves: MoveSequence) -> Cube:
    for move in moves:
        cube = apply_move(cube, move)
    return cube


def _move_base(move: Move) -> Move:
    if move.endswith("'") or move.endswith("2"):
        return move[:-1]
    return move


def _move_turns(move: Move) -> int:
    if move.endswith("'"):
        return 3
    if move.endswith("2"):
        return 2
    return 1


def improve_moves_sequence(moves_seq: MoveSequence) -> list[str]:
    """Cancel and combine adjacent turns of the same layer."""
    improved_moves_seq: list[str] = []
    for move in moves_seq:
        if not move:
            continue
        if improved_moves_seq and _move_base(improved_moves_seq[-1]) == _move_base(move):
            previous = improved_moves_seq.pop()
            turns = (_move_turns(previous) + _move_turns(move)) % 4
            if turns == 1:
                improved_moves_seq.append(_move_base(move))
            elif turns == 2:
                improved_moves_seq.append(_move_base(move) + "2")
            elif turns == 3:
                improved_moves_seq.append(_move_base(move) + "'")
        else:
            improved_moves_seq.append(move)
    return improved_moves_seq


def get_colors_rubik_solver_library(cube: Cube) -> str:
    size = cube_size(cube)
    last = size - 1
    cube_colors = ""
    for i in [Face.UP, Face.LEFT, Face.FRONT, Face.RIGHT, Face.BACK, Face.DOWN]:
        for j in range(size):
            for k in range(size):
                if i in [Face.UP, Face.FRONT]:
                    cube_colors += cube[i][j][k]
                if i in [Face.BACK, Face.DOWN]:
                    cube_colors += cube[i][last - j][last - k]
                if i == Face.LEFT:
                    cube_colors += cube[i][k][last - j]
                if i == Face.RIGHT:
                    cube_colors += cube[i][last - k][j]
    return cube_colors


def is_solved(cube: Cube) -> bool:
    try:
        face_colors = []
        for face in cube:
            color = face[0][0]
            if any(piece != color for row in face for piece in row):
                return False
            face_colors.append(color)
        return len(set(face_colors)) == len(Face) and set(face_colors) == set(FACE_COLORS)
    except (IndexError, TypeError):
        return False


def cube_signature(cube: Cube) -> tuple[str, ...]:
    """Return a hashable signature for caching solved-state checks."""
    return tuple(color for face in cube for row in face for color in row)


def print_cube(cube: Cube) -> None:
    size = cube_size(cube)
    for i in range(size):
        print("\n" + 14 * " ", end="")
        for piece in cube[Face.BACK][i]:
            print(piece, end=" ")
    for i in range(size):
        print("\n", end="")
        for j in range(4):
            for k in range(size):
                print(cube[j + 1][i][k], end=" ")
            print(" ", end="")
    for i in range(size):
        print("\n" + 14 * " ", end="")
        for piece in cube[-1][i]:
            print(piece, end=" ")
