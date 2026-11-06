"""Optimal 2x2 solver built on corner orientation and permutation databases."""

from __future__ import annotations

from array import array
from collections import deque
from collections.abc import Sequence
from math import factorial

from .config import FACE_COLORS, Face
from .cube import (
    Cube,
    Move,
    apply_move,
    apply_moves,
    blank_cube,
    cube_size,
    is_solved,
    validate_cube,
)
from .solvers import SolverFailedError

# Corner positions in the order DFL, DFR, DRB, DBL, UFL, UFR, URB, UBL.
# Each facelet triple starts with the U/D sticker so orientation 0 is solved.
CORNER_FACELETS: tuple[tuple[tuple[Face, int, int], ...], ...] = (
    ((Face.DOWN, 1, 1), (Face.LEFT, 1, 0), (Face.FRONT, 1, 0)),
    ((Face.DOWN, 1, 0), (Face.FRONT, 1, 1), (Face.RIGHT, 1, 1)),
    ((Face.DOWN, 0, 0), (Face.RIGHT, 0, 1), (Face.BACK, 0, 1)),
    ((Face.DOWN, 0, 1), (Face.BACK, 0, 0), (Face.LEFT, 0, 0)),
    ((Face.UP, 1, 0), (Face.LEFT, 1, 1), (Face.FRONT, 0, 0)),
    ((Face.UP, 1, 1), (Face.FRONT, 0, 1), (Face.RIGHT, 1, 0)),
    ((Face.UP, 0, 1), (Face.RIGHT, 0, 0), (Face.BACK, 1, 1)),
    ((Face.UP, 0, 0), (Face.BACK, 1, 0), (Face.LEFT, 0, 1)),
)

BASE_MOVES = list("URFDLB")
MOVE_NAMES = [f"{face}{suffix}" for face in BASE_MOVES for suffix in ("", "2", "'")]
FACE_ORDER = {face: index for index, face in enumerate(BASE_MOVES)}
OPPOSITE_FACES = {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}
PERMUTATION_STATES = factorial(8)
ORIENTATION_STATES = 3**8
FACTORIALS = [factorial(value) for value in range(9)]

OrientationMoves = list[array[int]]
PermutationMoves = list[array[int]]
DistanceTable = array[int]

_orientation_moves: OrientationMoves | None = None
_permutation_moves: PermutationMoves | None = None
_orientation_distances: DistanceTable | None = None
_permutation_distances: DistanceTable | None = None


CORNER_COLORS = [
    frozenset(FACE_COLORS[face] for face, _row, _column in corner) for corner in CORNER_FACELETS
]


def _encode_orientation(orientation: Sequence[int]) -> int:
    return sum(value * (3**index) for index, value in enumerate(orientation))


def _decode_orientation(index: int) -> list[int]:
    values = [0] * 8
    for position in range(8):
        index, values[position] = divmod(index, 3)
    return values


def _encode_permutation(permutation: Sequence[int]) -> int:
    rank = 0
    for position in range(8):
        smaller_after = sum(
            1 for value in permutation[position + 1 :] if value < permutation[position]
        )
        rank += smaller_after * FACTORIALS[7 - position]
    return rank


def _decode_permutation(rank: int) -> list[int]:
    available = list(range(8))
    permutation: list[int] = []
    for position in range(8):
        factor = FACTORIALS[7 - position]
        chosen, rank = divmod(rank, factor)
        permutation.append(available.pop(chosen))
    return permutation


def _extract_corners(cube: Cube) -> tuple[list[int], list[int]]:
    if cube_size(cube) != 2:
        raise SolverFailedError("The 2x2 solver only supports 2x2 cubes.")
    permutation: list[int] = []
    orientation: list[int] = []
    for corner in CORNER_FACELETS:
        colors = [cube[face][row][column] for face, row, column in corner]
        try:
            cubie = CORNER_COLORS.index(frozenset(colors))
        except ValueError as exc:
            raise SolverFailedError("The cube contains an invalid 2x2 corner.") from exc
        ud_colors = [index for index, color in enumerate(colors) if color in {"w", "y"}]
        if len(ud_colors) != 1:
            raise SolverFailedError("The cube contains an invalid 2x2 corner orientation.")
        permutation.append(cubie)
        orientation.append(ud_colors[0])
    return permutation, orientation


def _derive_move_geometry(move: Move) -> tuple[list[int], list[list[int]]]:
    labeled = blank_cube(size=2)
    for position, corner in enumerate(CORNER_FACELETS):
        for sticker, (face, row, column) in enumerate(corner):
            labeled[face][row][column] = position * 3 + sticker

    moved = apply_move(labeled, move)
    label_locations: dict[int, tuple[int, int]] = {}
    for position, corner in enumerate(CORNER_FACELETS):
        for sticker, (face, row, column) in enumerate(corner):
            label_locations[moved[face][row][column]] = (position, sticker)

    position_map = [0] * 8
    sticker_map = [[0, 1, 2] for _ in range(8)]
    for position in range(8):
        locations = [label_locations[position * 3 + sticker] for sticker in range(3)]
        destinations = {destination for destination, _sticker in locations}
        if len(destinations) != 1:
            raise SolverFailedError("Could not derive 2x2 move geometry.")
        position_map[position] = destinations.pop()
        sticker_map[position] = [sticker for _destination, sticker in locations]
    return position_map, sticker_map


def _double_table(table: array[int]) -> array[int]:
    double = array(table.typecode, [0]) * len(table)
    for coordinate in range(len(table)):
        double[coordinate] = table[table[coordinate]]
    return double


def _inverse_table(table: array[int]) -> array[int]:
    inverse = array(table.typecode, [0]) * len(table)
    for coordinate, destination in enumerate(table):
        inverse[destination] = coordinate
    return inverse


def _build_move_tables() -> None:
    global _orientation_moves, _permutation_moves
    if _orientation_moves is not None and _permutation_moves is not None:
        return

    orientation_tables: OrientationMoves = []
    permutation_tables: PermutationMoves = []
    for move in BASE_MOVES:
        position_map, sticker_map = _derive_move_geometry(move)
        orientation_table = array("H", [0]) * ORIENTATION_STATES
        permutation_table = array("I", [0]) * PERMUTATION_STATES

        for coordinate in range(ORIENTATION_STATES):
            old_orientation = _decode_orientation(coordinate)
            new_orientation = [0] * 8
            for position in range(8):
                new_orientation[position_map[position]] = sticker_map[position][
                    old_orientation[position]
                ]
            orientation_table[coordinate] = _encode_orientation(new_orientation)

        for coordinate in range(PERMUTATION_STATES):
            old_permutation = _decode_permutation(coordinate)
            new_permutation = [0] * 8
            for position in range(8):
                new_permutation[position_map[position]] = old_permutation[position]
            permutation_table[coordinate] = _encode_permutation(new_permutation)

        base_orientation = orientation_table
        base_permutation = permutation_table
        orientation_tables.extend(
            [
                base_orientation,
                _double_table(base_orientation),
                _inverse_table(base_orientation),
            ]
        )
        permutation_tables.extend(
            [
                base_permutation,
                _double_table(base_permutation),
                _inverse_table(base_permutation),
            ]
        )

    _orientation_moves = orientation_tables
    _permutation_moves = permutation_tables


def _build_distance_table(move_tables: Sequence[array[int]], states: int) -> DistanceTable:
    distances: DistanceTable = array("b", [-1]) * states
    distances[0] = 0
    queue: deque[int] = deque([0])
    while queue:
        coordinate = queue.popleft()
        next_distance = distances[coordinate] + 1
        for table in move_tables:
            next_coordinate = table[coordinate]
            if distances[next_coordinate] == -1:
                distances[next_coordinate] = next_distance
                queue.append(next_coordinate)
    return distances


def _build_distance_tables() -> None:
    global _orientation_distances, _permutation_distances
    if _orientation_distances is not None and _permutation_distances is not None:
        return
    _build_move_tables()
    assert _orientation_moves is not None and _permutation_moves is not None
    _orientation_distances = _build_distance_table(_orientation_moves, ORIENTATION_STATES)
    _permutation_distances = _build_distance_table(_permutation_moves, PERMUTATION_STATES)


def _search(
    permutation: int,
    orientation: int,
    depth: int,
    limit: int,
    last_face: str | None,
    path: list[Move],
) -> bool:
    assert _orientation_moves is not None
    assert _permutation_moves is not None
    assert _orientation_distances is not None
    assert _permutation_distances is not None

    heuristic = max(
        _orientation_distances[orientation],
        _permutation_distances[permutation],
    )
    if heuristic < 0:
        return False
    if depth + heuristic > limit:
        return False
    if heuristic == 0:
        return True

    for move_index, move in enumerate(MOVE_NAMES):
        face = move[0]
        if face == last_face:
            continue
        if (
            last_face is not None
            and OPPOSITE_FACES.get(face) == last_face
            and FACE_ORDER[last_face] > FACE_ORDER[face]
        ):
            continue
        next_orientation = _orientation_moves[move_index][orientation]
        next_permutation = _permutation_moves[move_index][permutation]
        if _orientation_distances[next_orientation] < 0:
            continue
        path.append(move)
        if _search(
            next_permutation,
            next_orientation,
            depth + 1,
            limit,
            face,
            path,
        ):
            return True
        path.pop()
    return False


def solve_2x2(cube: Cube) -> tuple[list[Move], list[list[Move]], Cube]:
    """Return ``(moves, stages, solved_cube)`` for a 2x2 cube."""
    validate_cube(cube)
    if cube_size(cube) != 2:
        raise SolverFailedError("The 2x2 solver only supports 2x2 cubes.")
    _build_distance_tables()
    assert _orientation_distances is not None
    assert _permutation_distances is not None

    permutation_list, orientation_list = _extract_corners(cube)
    permutation = _encode_permutation(permutation_list)
    orientation = _encode_orientation(orientation_list)

    if _orientation_distances[orientation] < 0 or _permutation_distances[permutation] < 0:
        raise SolverFailedError("This 2x2 pattern is not solvable.")

    if permutation == 0 and orientation == 0:
        return [], [], cube

    start_limit = max(
        _orientation_distances[orientation],
        _permutation_distances[permutation],
    )
    path: list[Move] = []
    for limit in range(start_limit, 15):
        if _search(permutation, orientation, 0, limit, None, path):
            solved = apply_moves(cube, path)
            if not is_solved(solved):
                raise SolverFailedError("The 2x2 solver returned an invalid solution.")
            return path, [path], solved

    raise SolverFailedError("The 2x2 solver could not find a solution.")
