"""Pure 3x3 Rubik's cube state and move operations.

A cube is a list of six 3x3 faces using the :class:`~rubik.config.Face` order.
Each face is indexed as ``[row][column]``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from .config import CENTER, FACE_COLORS, FACE_SIZE, Face

Cube = list[list[list[str]]]
Move = str
MoveSequence = Sequence[Move]


class InvalidCubeError(ValueError):
    """Raised when a cube is malformed or has impossible color counts."""


def solved_cube() -> Cube:
    """Return a solved cube in the default orientation."""
    return [
        [[FACE_COLORS[x] for _ in range(FACE_SIZE)] for _ in range(FACE_SIZE)]
        for x in range(len(Face))
    ]


def blank_cube(fill: str = "c") -> Cube:
    """Return a cube with every facelet set to ``fill``."""
    return [[[fill for _ in range(FACE_SIZE)] for _ in range(FACE_SIZE)] for _ in range(len(Face))]


def copy_cube(cube: Cube) -> Cube:
    return [
        [[cube[x][y][z] for z in range(FACE_SIZE)] for y in range(FACE_SIZE)]
        for x in range(len(Face))
    ]


def validate_cube(cube: Cube) -> None:
    """Validate the cube structure and its color distribution.

    This catches malformed patterns and impossible color counts.  It does not
    attempt full cubie-level solvability; the solvers report that separately.
    """
    if len(cube) != len(Face):
        raise InvalidCubeError(f"A cube must have {len(Face)} faces.")

    for face in cube:
        if len(face) != FACE_SIZE or any(len(row) != FACE_SIZE for row in face):
            raise InvalidCubeError(f"Every face must be {FACE_SIZE}x{FACE_SIZE}.")

    counts = Counter(color for face in cube for row in face for color in row)
    unknown_colors = set(counts) - set(FACE_COLORS)
    if unknown_colors:
        raise InvalidCubeError(f"Unknown facelet colors: {sorted(unknown_colors)}.")

    for color in FACE_COLORS:
        if counts[color] != FACE_SIZE * FACE_SIZE:
            raise InvalidCubeError(f"Color {color!r} must appear exactly 9 times.")

    centres = face_centres(cube)
    if len(set(centres)) != len(Face):
        raise InvalidCubeError("Every face must have a different centre color.")


def face_centres(cube: Cube) -> list[str]:
    return [face[CENTER][CENTER] for face in cube]


def face_centre(cube: Cube, face: Face) -> str:
    return cube[face][CENTER][CENTER]


def _rotate_face_clockwise(face: list[list[str]]) -> list[list[str]]:
    return [[face[2 - j][i] for j in range(FACE_SIZE)] for i in range(FACE_SIZE)]


def left(cube: Cube) -> Cube:
    cube2 = copy_cube(cube)
    for i in range(FACE_SIZE):
        cube2[Face.BACK][i][0] = [cube[Face.DOWN][x][2] for x in [2, 1, 0]][i]
        cube2[Face.DOWN][i][2] = [cube[Face.FRONT][x][0] for x in [2, 1, 0]][i]
        cube2[Face.UP][i][0] = [cube[Face.BACK][x][0] for x in [0, 1, 2]][i]
        cube2[Face.FRONT][i][0] = [cube[Face.UP][x][0] for x in [0, 1, 2]][i]
    cube2[Face.LEFT] = _rotate_face_clockwise(cube[Face.LEFT])
    return cube2


def right(cube: Cube) -> Cube:
    cube2 = copy_cube(cube)
    for i in range(FACE_SIZE):
        cube2[Face.UP][i][2] = [cube[Face.FRONT][x][2] for x in [0, 1, 2]][i]
        cube2[Face.FRONT][i][2] = [cube[Face.DOWN][x][0] for x in [2, 1, 0]][i]
        cube2[Face.BACK][i][2] = [cube[Face.UP][x][2] for x in [0, 1, 2]][i]
        cube2[Face.DOWN][i][0] = [cube[Face.BACK][x][2] for x in [2, 1, 0]][i]
    cube2[Face.RIGHT] = _rotate_face_clockwise(cube[Face.RIGHT])
    return cube2


def up(cube: Cube) -> Cube:
    cube2 = copy_cube(cube)
    for i in range(FACE_SIZE):
        cube2[Face.BACK][2][i] = [cube[Face.LEFT][x][2] for x in [2, 1, 0]][i]
        cube2[Face.LEFT][i][2] = [cube[Face.FRONT][0][x] for x in [0, 1, 2]][i]
        cube2[Face.RIGHT][i][0] = [cube[Face.BACK][2][x] for x in [0, 1, 2]][i]
        cube2[Face.FRONT][0][i] = [cube[Face.RIGHT][x][0] for x in [2, 1, 0]][i]
    cube2[Face.UP] = _rotate_face_clockwise(cube[Face.UP])
    return cube2


def down(cube: Cube) -> Cube:
    cube2 = copy_cube(cube)
    for i in range(FACE_SIZE):
        cube2[Face.BACK][0][i] = [cube[Face.RIGHT][x][2] for x in [0, 1, 2]][i]
        cube2[Face.LEFT][i][0] = [cube[Face.BACK][0][x] for x in [2, 1, 0]][i]
        cube2[Face.RIGHT][i][2] = [cube[Face.FRONT][2][x] for x in [2, 1, 0]][i]
        cube2[Face.FRONT][2][i] = [cube[Face.LEFT][x][0] for x in [0, 1, 2]][i]
    cube2[Face.DOWN] = _rotate_face_clockwise(cube[Face.DOWN])
    return cube2


def front(cube: Cube) -> Cube:
    cube2 = copy_cube(cube)
    for i in range(FACE_SIZE):
        cube2[Face.DOWN][2][i] = [cube[Face.RIGHT][2][x] for x in [0, 1, 2]][i]
        cube2[Face.LEFT][2][i] = [cube[Face.DOWN][2][x] for x in [0, 1, 2]][i]
        cube2[Face.UP][2][i] = [cube[Face.LEFT][2][x] for x in [0, 1, 2]][i]
        cube2[Face.RIGHT][2][i] = [cube[Face.UP][2][x] for x in [0, 1, 2]][i]
    cube2[Face.FRONT] = _rotate_face_clockwise(cube[Face.FRONT])
    return cube2


def back(cube: Cube) -> Cube:
    cube2 = copy_cube(cube)
    for i in range(FACE_SIZE):
        cube2[Face.DOWN][0][i] = [cube[Face.LEFT][0][x] for x in [0, 1, 2]][i]
        cube2[Face.LEFT][0][i] = [cube[Face.UP][0][x] for x in [0, 1, 2]][i]
        cube2[Face.UP][0][i] = [cube[Face.RIGHT][0][x] for x in [0, 1, 2]][i]
        cube2[Face.RIGHT][0][i] = [cube[Face.DOWN][0][x] for x in [0, 1, 2]][i]
    cube2[Face.BACK] = _rotate_face_clockwise(cube[Face.BACK])
    return cube2


def midM(cube: Cube) -> Cube:
    cube2 = copy_cube(cube)
    for i in range(FACE_SIZE):
        cube2[Face.BACK][i][1] = [cube[Face.DOWN][x][1] for x in [2, 1, 0]][i]
        cube2[Face.DOWN][i][1] = [cube[Face.FRONT][x][1] for x in [2, 1, 0]][i]
        cube2[Face.UP][i][1] = [cube[Face.BACK][x][1] for x in [0, 1, 2]][i]
        cube2[Face.FRONT][i][1] = [cube[Face.UP][x][1] for x in [0, 1, 2]][i]
    return cube2


def midE(cube: Cube) -> Cube:
    cube2 = copy_cube(cube)
    for i in range(FACE_SIZE):
        cube2[Face.BACK][1][i] = [cube[Face.RIGHT][x][1] for x in [0, 1, 2]][i]
        cube2[Face.LEFT][i][1] = [cube[Face.BACK][1][x] for x in [2, 1, 0]][i]
        cube2[Face.RIGHT][i][1] = [cube[Face.FRONT][1][x] for x in [2, 1, 0]][i]
        cube2[Face.FRONT][1][i] = [cube[Face.LEFT][x][1] for x in [0, 1, 2]][i]
    return cube2


def midS(cube: Cube) -> Cube:
    cube2 = copy_cube(cube)
    for i in range(FACE_SIZE):
        cube2[Face.DOWN][1][i] = [cube[Face.RIGHT][1][x] for x in [0, 1, 2]][i]
        cube2[Face.LEFT][1][i] = [cube[Face.DOWN][1][x] for x in [0, 1, 2]][i]
        cube2[Face.UP][1][i] = [cube[Face.LEFT][1][x] for x in [0, 1, 2]][i]
        cube2[Face.RIGHT][1][i] = [cube[Face.UP][1][x] for x in [0, 1, 2]][i]
    return cube2


def rotx(cube: Cube) -> Cube:
    cube2 = right(cube)
    for _ in range(FACE_SIZE):
        cube2 = left(cube2)
        cube2 = midM(cube2)
    return cube2


def roty(cube: Cube) -> Cube:
    cube2 = up(cube)
    for _ in range(FACE_SIZE):
        cube2 = down(cube2)
        cube2 = midE(cube2)
    return cube2


def rotz(cube: Cube) -> Cube:
    cube2 = front(cube)
    cube2 = midS(cube2)
    for _ in range(FACE_SIZE):
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
    cube_colors = ""
    for i in [Face.UP, Face.LEFT, Face.FRONT, Face.RIGHT, Face.BACK, Face.DOWN]:
        for j in range(FACE_SIZE):
            for k in range(FACE_SIZE):
                if i in [Face.UP, Face.FRONT]:
                    cube_colors += cube[i][j][k]
                if i in [Face.BACK, Face.DOWN]:
                    cube_colors += cube[i][2 - j][2 - k]
                if i == Face.LEFT:
                    cube_colors += cube[i][k][2 - j]
                if i == Face.RIGHT:
                    cube_colors += cube[i][2 - k][j]
    return cube_colors


def is_solved(cube: Cube) -> bool:
    try:
        centres = face_centres(cube)
        cube = apply_moves(cube, [["x"], [], ["z'"], ["x", "x"], ["z"], ["x'"]][centres.index("y")])
        centres = face_centres(cube)
        cube = apply_moves(cube, [["y", "y"], [], ["y'"], [], ["y"], []][centres.index("g")])
        for i in range(len(cube)):
            centre = cube[i][CENTER][CENTER]
            if centre != FACE_COLORS[i]:
                return False
            for j in range(FACE_SIZE):
                for k in range(FACE_SIZE):
                    if cube[i][j][k] != centre:
                        return False
        return True
    except (ValueError, IndexError):
        return False


def cube_signature(cube: Cube) -> tuple[str, ...]:
    """Return a hashable signature for caching solved-state checks."""
    return tuple(color for face in cube for row in face for color in row)


def print_cube(cube: Cube) -> None:
    for i in range(FACE_SIZE):
        print("\n" + 14 * " ", end="")
        for piece in cube[Face.BACK][i]:
            print(piece, end=" ")
    for i in range(FACE_SIZE):
        print("\n", end="")
        for j in range(4):
            for k in range(FACE_SIZE):
                print(cube[j + 1][i][k], end=" ")
            print(" ", end="")
    for i in range(FACE_SIZE):
        print("\n" + 14 * " ", end="")
        for piece in cube[-1][i]:
            print(piece, end=" ")
