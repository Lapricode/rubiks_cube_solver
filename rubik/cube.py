"""Rubik's cube state and move operations for 2x2 and 3x3 cubes.

A cube is a list of six square faces using the :class:`~rubik.config.Face`
order. Each face is indexed as ``[row][column]``. The cube size is inferred
from the face dimensions, so the same model handles both 2x2 and 3x3 cubes.
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


def left(cube: Cube) -> Cube:
    size = cube_size(cube)
    last = size - 1
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.BACK][i][0] = [cube[Face.DOWN][x][last] for x in range(last, -1, -1)][i]
        cube2[Face.DOWN][i][last] = [cube[Face.FRONT][x][0] for x in range(last, -1, -1)][i]
        cube2[Face.UP][i][0] = [cube[Face.BACK][x][0] for x in range(size)][i]
        cube2[Face.FRONT][i][0] = [cube[Face.UP][x][0] for x in range(size)][i]
    cube2[Face.LEFT] = _rotate_face_clockwise(cube[Face.LEFT])
    return cube2


def right(cube: Cube) -> Cube:
    size = cube_size(cube)
    last = size - 1
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.UP][i][last] = [cube[Face.FRONT][x][last] for x in range(size)][i]
        cube2[Face.FRONT][i][last] = [cube[Face.DOWN][x][0] for x in range(last, -1, -1)][i]
        cube2[Face.BACK][i][last] = [cube[Face.UP][x][last] for x in range(size)][i]
        cube2[Face.DOWN][i][0] = [cube[Face.BACK][x][last] for x in range(last, -1, -1)][i]
    cube2[Face.RIGHT] = _rotate_face_clockwise(cube[Face.RIGHT])
    return cube2


def up(cube: Cube) -> Cube:
    size = cube_size(cube)
    last = size - 1
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.BACK][last][i] = [cube[Face.LEFT][x][last] for x in range(last, -1, -1)][i]
        cube2[Face.LEFT][i][last] = [cube[Face.FRONT][0][x] for x in range(size)][i]
        cube2[Face.RIGHT][i][0] = [cube[Face.BACK][last][x] for x in range(size)][i]
        cube2[Face.FRONT][0][i] = [cube[Face.RIGHT][x][0] for x in range(last, -1, -1)][i]
    cube2[Face.UP] = _rotate_face_clockwise(cube[Face.UP])
    return cube2


def down(cube: Cube) -> Cube:
    size = cube_size(cube)
    last = size - 1
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.BACK][0][i] = [cube[Face.RIGHT][x][last] for x in range(size)][i]
        cube2[Face.LEFT][i][0] = [cube[Face.BACK][0][x] for x in range(last, -1, -1)][i]
        cube2[Face.RIGHT][i][last] = [cube[Face.FRONT][last][x] for x in range(last, -1, -1)][i]
        cube2[Face.FRONT][last][i] = [cube[Face.LEFT][x][0] for x in range(size)][i]
    cube2[Face.DOWN] = _rotate_face_clockwise(cube[Face.DOWN])
    return cube2


def front(cube: Cube) -> Cube:
    size = cube_size(cube)
    last = size - 1
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.DOWN][last][i] = [cube[Face.RIGHT][last][x] for x in range(size)][i]
        cube2[Face.LEFT][last][i] = [cube[Face.DOWN][last][x] for x in range(size)][i]
        cube2[Face.UP][last][i] = [cube[Face.LEFT][last][x] for x in range(size)][i]
        cube2[Face.RIGHT][last][i] = [cube[Face.UP][last][x] for x in range(size)][i]
    cube2[Face.FRONT] = _rotate_face_clockwise(cube[Face.FRONT])
    return cube2


def back(cube: Cube) -> Cube:
    size = cube_size(cube)
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.DOWN][0][i] = [cube[Face.LEFT][0][x] for x in range(size)][i]
        cube2[Face.LEFT][0][i] = [cube[Face.UP][0][x] for x in range(size)][i]
        cube2[Face.UP][0][i] = [cube[Face.RIGHT][0][x] for x in range(size)][i]
        cube2[Face.RIGHT][0][i] = [cube[Face.DOWN][0][x] for x in range(size)][i]
    cube2[Face.BACK] = _rotate_face_clockwise(cube[Face.BACK])
    return cube2


def _middle_index(cube: Cube) -> int:
    size = cube_size(cube)
    if size % 2 == 0:
        raise ValueError("Middle slice moves are not available on even-sized cubes.")
    return size // 2


def midM(cube: Cube) -> Cube:
    size = cube_size(cube)
    last = size - 1
    middle = _middle_index(cube)
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.BACK][i][middle] = [cube[Face.DOWN][x][middle] for x in range(last, -1, -1)][i]
        cube2[Face.DOWN][i][middle] = [cube[Face.FRONT][x][middle] for x in range(last, -1, -1)][i]
        cube2[Face.UP][i][middle] = [cube[Face.BACK][x][middle] for x in range(size)][i]
        cube2[Face.FRONT][i][middle] = [cube[Face.UP][x][middle] for x in range(size)][i]
    return cube2


def midE(cube: Cube) -> Cube:
    size = cube_size(cube)
    last = size - 1
    middle = _middle_index(cube)
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.BACK][middle][i] = [cube[Face.RIGHT][x][middle] for x in range(size)][i]
        cube2[Face.LEFT][i][middle] = [cube[Face.BACK][middle][x] for x in range(last, -1, -1)][i]
        cube2[Face.RIGHT][i][middle] = [cube[Face.FRONT][middle][x] for x in range(last, -1, -1)][i]
        cube2[Face.FRONT][middle][i] = [cube[Face.LEFT][x][middle] for x in range(size)][i]
    return cube2


def midS(cube: Cube) -> Cube:
    size = cube_size(cube)
    middle = _middle_index(cube)
    cube2 = copy_cube(cube)
    for i in range(size):
        cube2[Face.DOWN][middle][i] = [cube[Face.RIGHT][middle][x] for x in range(size)][i]
        cube2[Face.LEFT][middle][i] = [cube[Face.DOWN][middle][x] for x in range(size)][i]
        cube2[Face.UP][middle][i] = [cube[Face.LEFT][middle][x] for x in range(size)][i]
        cube2[Face.RIGHT][middle][i] = [cube[Face.UP][middle][x] for x in range(size)][i]
    return cube2


def rotx(cube: Cube) -> Cube:
    size = cube_size(cube)
    if size == 2:
        cube2 = right(cube)
        for _ in range(3):
            cube2 = left(cube2)
        return cube2
    if size % 2 == 0:
        raise ValueError("Whole-cube rotations support 2x2 and odd-sized cubes.")
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
    if size % 2 == 0:
        raise ValueError("Whole-cube rotations support 2x2 and odd-sized cubes.")
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
    if size % 2 == 0:
        raise ValueError("Whole-cube rotations support 2x2 and odd-sized cubes.")
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
    try:
        move_function = MOVE_FUNCTIONS[move[0]]
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


def improve_moves_sequence(moves_seq: MoveSequence) -> list[str]:
    if len(moves_seq) == 1:
        return list(moves_seq)
    improved_moves_seq: list[str] = []
    improvements_done = False
    loops_counter = 0
    while loops_counter != len(moves_seq):
        if improved_moves_seq == []:
            improved_moves_seq.append(moves_seq[loops_counter])
        else:
            moves_k0_k1 = [improved_moves_seq[-1], moves_seq[loops_counter]]
            if moves_k0_k1[0][0] == moves_k0_k1[1][0]:
                moves_k0_k1_lengths = [len(moves_k0_k1[0]), len(moves_k0_k1[1])]
                improved_moves_seq.pop()
                if moves_k0_k1_lengths.count(1) == 2:
                    improved_moves_seq.append(moves_k0_k1[0][0] + "2")
                elif (
                    moves_k0_k1_lengths.count(2) == 1
                    and moves_k0_k1[moves_k0_k1_lengths.index(2)][1] == "2"
                ):
                    improved_moves_seq.append(moves_k0_k1[1 - moves_k0_k1_lengths.index(2)] + "'")
                elif moves_k0_k1_lengths.count(2) == 2:
                    if moves_k0_k1[0][1] == "'" and moves_k0_k1[1][1] == "'":
                        improved_moves_seq.append(moves_k0_k1[0][0] + "2")
                    elif [moves_k0_k1[0][1], moves_k0_k1[1][1]] in [["'", "2"], ["2", "'"]]:
                        improved_moves_seq.append(moves_k0_k1[0][0])
                improvements_done = True
            else:
                improved_moves_seq.append(moves_k0_k1[1])
        loops_counter += 1
    if improvements_done:
        return improve_moves_sequence(improved_moves_seq)
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
