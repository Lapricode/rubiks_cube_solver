"""In-house 4x4 reduction solver.

The solver reduces the cube with pure three-cycle macros for wings and centres,
handles wing and 3x3 parity, then finishes with the existing beginner solver.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from .config import FACE_COLORS, Face
from .cube import (
    Cube,
    Move,
    apply_move,
    apply_moves,
    cube_size,
    is_solved,
    solved_cube,
    validate_cube,
)
from .solvers import CORNERS, EDGES, SolverFailedError, solve_beginner

SIZE = 4
FACE_NAMES = ["B", "D", "L", "U", "R", "F"]
ALL_MOVES = [
    move
    for face in FACE_NAMES
    for suffix in ("", "'", "2")
    for move in (face + suffix, face.lower() + suffix, face + "w" + suffix)
]

WING_MACRO = "R U R' u R U' R' u'".split()
CENTER_MACRO = "r u r' u' R u r u' r' R'".split()
OLL_PARITY = "r U2 r U2 r U2 r' U2 l U2 r' U2 r U2 r' U2 r'".split()
PLL_PARITY = "r2 U2 r2 Uw2 r2 Uw2".split()

POSITIONS = [
    (int(face), row, column) for face in range(6) for row in range(SIZE) for column in range(SIZE)
]
POSITION_INDEX = {position: index for index, position in enumerate(POSITIONS)}
CENTER_POSITIONS = tuple(
    position for position in POSITIONS if position[1] in (1, 2) and position[2] in (1, 2)
)
EDGE_POSITIONS = tuple(
    position for position in POSITIONS if (position[1] in (1, 2)) ^ (position[2] in (1, 2))
)
WING_SEED = ((int(Face.BACK), 2, 3), (int(Face.RIGHT), 0, 1))

CORNER_TARGET_SETS = [
    frozenset(solved_cube(3)[int(face)][int(row)][int(column)] for face, row, column in group)
    for group in CORNERS
]
EDGE_TARGET_SETS = [
    frozenset(solved_cube(3)[int(face)][int(row)][int(column)] for face, row, column in group)
    for group in EDGES
]


class _Geometry:
    __slots__ = (
        "pairs",
        "wing_targets",
        "center_positions",
        "center_targets",
        "wing_moves",
        "center_moves",
        "wing_support",
        "center_support",
        "wing_setup_parent",
        "wing_setup_move",
        "center_setup_parent",
        "center_setup_move",
    )

    def __init__(self) -> None:
        self.pairs = _build_wing_pairs()
        self.wing_targets = [
            tuple(solved_cube(SIZE)[face][row][column] for face, row, column in pair)
            for pair in self.pairs
        ]
        self.center_positions = CENTER_POSITIONS
        self.center_targets = [
            solved_cube(SIZE)[face][row][column] for face, row, column in CENTER_POSITIONS
        ]
        self.wing_moves = _build_piece_moves(self.pairs)
        center_index = {position: index for index, position in enumerate(self.center_positions)}
        sticker_moves = _sticker_moves()
        self.center_moves = {
            move: [
                center_index[POSITIONS[sticker_moves[move][POSITION_INDEX[position]]]]
                for position in self.center_positions
            ]
            for move in ALL_MOVES
        }
        self.wing_support = _macro_support(self.wing_moves, WING_MACRO)
        self.center_support = _macro_support(self.center_moves, CENTER_MACRO)
        self.wing_setup_parent, self.wing_setup_move = _build_setup_tables(
            self.wing_moves, self.wing_support
        )
        self.center_setup_parent, self.center_setup_move = _build_setup_tables(
            self.center_moves, self.center_support
        )


_geometry: _Geometry | None = None


def _build_sticker_moves() -> dict[str, list[int]]:
    labeled = [
        [[face * 16 + row * 4 + column for column in range(SIZE)] for row in range(SIZE)]
        for face in range(6)
    ]
    maps: dict[str, list[int]] = {}
    for move in ALL_MOVES:
        moved = apply_move(labeled, move)
        locations = {
            moved[face][row][column]: (face, row, column)
            for face in range(6)
            for row in range(SIZE)
            for column in range(SIZE)
        }
        maps[move] = [
            POSITION_INDEX[locations[face * 16 + row * 4 + column]]
            for face, row, column in POSITIONS
        ]
    return maps


_STICKER_MOVES: dict[str, list[int]] | None = None


def _sticker_moves() -> dict[str, list[int]]:
    global _STICKER_MOVES
    if _STICKER_MOVES is None:
        _STICKER_MOVES = _build_sticker_moves()
    return _STICKER_MOVES


def _build_wing_pairs() -> tuple[tuple[tuple[int, int, int], tuple[int, int, int]], ...]:
    sticker_moves = _sticker_moves()
    pairs: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = []
    seen = {WING_SEED}
    queue: deque[tuple[tuple[int, int, int], tuple[int, int, int]]] = deque([WING_SEED])
    while queue:
        pair = queue.popleft()
        pairs.append(pair)
        for move in ALL_MOVES:
            next_pair = tuple(
                POSITIONS[sticker_moves[move][POSITION_INDEX[position]]] for position in pair
            )
            if next_pair not in seen:
                seen.add(next_pair)
                queue.append(next_pair)
    if len(pairs) != 24 or set(position for pair in pairs for position in pair) != set(
        EDGE_POSITIONS
    ):
        raise SolverFailedError("Could not derive the 4x4 wing geometry.")
    return tuple(pairs)


def _build_piece_moves(
    pieces: Sequence[tuple[tuple[int, int, int], ...]],
) -> dict[str, list[int]]:
    sticker_moves = _sticker_moves()
    piece_index = {piece: index for index, piece in enumerate(pieces)}
    moves: dict[str, list[int]] = {}
    for move in ALL_MOVES:
        table: list[int] = []
        for piece in pieces:
            next_piece = tuple(
                POSITIONS[sticker_moves[move][POSITION_INDEX[position]]] for position in piece
            )
            table.append(piece_index[next_piece])
        moves[move] = table
    return moves


def _macro_support(
    move_tables: dict[str, list[int]], macro: Sequence[Move]
) -> tuple[int, int, int]:
    permutation = list(range(len(next(iter(move_tables.values())))))
    for move in macro:
        permutation = [move_tables[move][value] for value in permutation]
    moved = [index for index, value in enumerate(permutation) if value != index]
    if len(moved) != 3:
        raise SolverFailedError("The 4x4 macro is not a pure three-cycle.")
    first = moved[0]
    second = permutation[first]
    third = permutation[second]
    if permutation[third] != first:
        raise SolverFailedError("The 4x4 macro is not a three-cycle.")
    return first, second, third


def _build_setup_tables(
    move_tables: dict[str, list[int]], support: tuple[int, int, int]
) -> tuple[
    dict[tuple[int, int, int], tuple[int, int, int] | None], dict[tuple[int, int, int], Move]
]:
    start = support
    parent: dict[tuple[int, int, int], tuple[int, int, int] | None] = {start: None}
    move_for_state: dict[tuple[int, int, int], Move] = {}
    queue: deque[tuple[int, int, int]] = deque([start])
    while queue:
        state = queue.popleft()
        for move in ALL_MOVES:
            table = move_tables[move]
            next_state = (table[state[0]], table[state[1]], table[state[2]])
            if next_state not in parent:
                parent[next_state] = state
                move_for_state[next_state] = move
                queue.append(next_state)
    return parent, move_for_state


def _geometry_for_cube() -> _Geometry:
    global _geometry
    if _geometry is None:
        _geometry = _Geometry()
    return _geometry


def _inverse_move(move: Move) -> Move:
    if move.endswith("'"):
        return move[:-1]
    if move.endswith("2"):
        return move
    return move + "'"


def _inverse_moves(moves: Sequence[Move]) -> list[Move]:
    return [_inverse_move(move) for move in reversed(moves)]


def _setup_path(
    parent: dict[tuple[int, int, int], tuple[int, int, int] | None],
    move_for_state: dict[tuple[int, int, int], Move],
    target: tuple[int, int, int],
) -> list[Move]:
    if target not in parent:
        raise SolverFailedError("Could not conjugate a 4x4 three-cycle.")
    path: list[Move] = []
    state: tuple[int, int, int] | None = target
    while state is not None and parent[state] is not None:
        path.append(move_for_state[state])
        state = parent[state]
    path.reverse()
    return path


def _apply_cycle(
    cube: Cube,
    parent: dict[tuple[int, int, int], tuple[int, int, int] | None],
    move_for_state: dict[tuple[int, int, int], Move],
    macro: Sequence[Move],
    cycle: tuple[int, int, int],
) -> tuple[Cube, list[Move]]:
    setup = _setup_path(parent, move_for_state, cycle)
    inverse = _inverse_moves(setup)
    cube = apply_moves(cube, inverse)
    cube = apply_moves(cube, macro)
    cube = apply_moves(cube, setup)
    return cube, inverse + list(macro) + setup


_THREE_BY_THREE_SLICE_MOVES = {
    "M": ["L'", "R", "x'"],
    "M2": ["L2", "R2", "x2"],
    "M'": ["L", "R'", "x"],
    "E": ["D'", "U", "y'"],
    "E2": ["D2", "U2", "y2"],
    "E'": ["D", "U'", "y"],
    "S": ["F'", "B", "z"],
    "S2": ["F2", "B2", "z2"],
    "S'": ["F", "B'", "z'"],
}


def _expand_three_by_three_slices(moves: Sequence[Move]) -> list[Move]:
    expanded: list[Move] = []
    for move in moves:
        expanded.extend(_THREE_BY_THREE_SLICE_MOVES.get(move, [move]))
    return expanded


def _base_move(move: Move) -> str:
    if move.endswith("'") or move.endswith("2"):
        return move[:-1]
    return move


def _simplify_stage(moves: Sequence[Move]) -> list[Move]:
    result: list[Move] = []
    for move in moves:
        if result and _base_move(result[-1]) == _base_move(move):
            previous = result.pop()
            previous_turns = 3 if previous.endswith("'") else 2 if previous.endswith("2") else 1
            move_turns = 3 if move.endswith("'") else 2 if move.endswith("2") else 1
            turns = (previous_turns + move_turns) % 4
            if turns == 1:
                result.append(_base_move(move))
            elif turns == 2:
                result.append(_base_move(move) + "2")
            elif turns == 3:
                result.append(_base_move(move) + "'")
        else:
            result.append(move)
    return result


def _parity(permutation: Sequence[int]) -> int:
    inversions = sum(
        1
        for left in range(len(permutation))
        for right in range(left + 1, len(permutation))
        if permutation[left] > permutation[right]
    )
    return inversions % 2


def _sort_permutation(
    cube: Cube,
    permutation: Sequence[int],
    parent: dict[tuple[int, int, int], tuple[int, int, int] | None],
    move_for_state: dict[tuple[int, int, int], Move],
    macro: Sequence[Move],
) -> tuple[Cube, list[Move]]:
    current = list(permutation)
    moves: list[Move] = []
    while True:
        first = next((index for index, value in enumerate(current) if value != index), None)
        if first is None:
            return cube, moves
        second = current[first]
        if current[second] == first:
            third = next(
                (
                    index
                    for index, value in enumerate(current)
                    if value != index and index not in (first, second)
                ),
                None,
            )
            if third is None:
                raise SolverFailedError("Could not resolve a 4x4 two-cycle.")
        else:
            third = current[second]
        if third in (first, second):
            raise SolverFailedError("Could not build a 4x4 three-cycle.")
        cube, cycle_moves = _apply_cycle(
            cube, parent, move_for_state, macro, (first, second, third)
        )
        moves.extend(cycle_moves)
        current[second], current[third], current[first] = (
            current[first],
            current[second],
            current[third],
        )


def _wing_permutation(cube: Cube, geometry: _Geometry) -> list[int]:
    target_index = {target: index for index, target in enumerate(geometry.wing_targets)}
    try:
        return [
            target_index[tuple(cube[face][row][column] for face, row, column in pair)]
            for pair in geometry.pairs
        ]
    except KeyError as exc:
        raise SolverFailedError("The cube contains an invalid 4x4 wing.") from exc


def _solve_wings(cube: Cube, geometry: _Geometry) -> tuple[Cube, list[Move], bool]:
    permutation = _wing_permutation(cube, geometry)
    used_parity = False
    if _parity(permutation):
        cube = apply_moves(cube, OLL_PARITY)
        permutation = _wing_permutation(cube, geometry)
        used_parity = True
        if _parity(permutation):
            raise SolverFailedError("Could not correct 4x4 wing parity.")
    cube, moves = _sort_permutation(
        cube,
        permutation,
        geometry.wing_setup_parent,
        geometry.wing_setup_move,
        WING_MACRO,
    )
    if _wing_permutation(cube, geometry) != list(range(24)):
        raise SolverFailedError("The 4x4 wing solver returned an invalid solution.")
    return cube, moves, used_parity


def _center_permutation(cube: Cube, geometry: _Geometry) -> list[int]:
    current = [cube[face][row][column] for face, row, column in geometry.center_positions]
    target = geometry.center_targets
    destinations: list[int | None] = [None] * len(current)
    for color in FACE_COLORS:
        current_positions = [index for index, value in enumerate(current) if value == color]
        target_positions = [index for index, value in enumerate(target) if value == color]
        if len(current_positions) != 4 or len(target_positions) != 4:
            raise SolverFailedError("The cube contains invalid 4x4 centres.")
        for source, destination in zip(current_positions, target_positions, strict=True):
            destinations[source] = destination
    permutation = [int(value) for value in destinations]
    if _parity(permutation):
        for color in FACE_COLORS:
            positions = [index for index, value in enumerate(current) if value == color]
            if len(positions) >= 2:
                first, second = positions[:2]
                permutation[first], permutation[second] = permutation[second], permutation[first]
                break
    return permutation


def _solve_centers(cube: Cube, geometry: _Geometry) -> tuple[Cube, list[Move]]:
    permutation = _center_permutation(cube, geometry)
    cube, moves = _sort_permutation(
        cube,
        permutation,
        geometry.center_setup_parent,
        geometry.center_setup_move,
        CENTER_MACRO,
    )
    current = [cube[face][row][column] for face, row, column in geometry.center_positions]
    if current != geometry.center_targets:
        raise SolverFailedError("The 4x4 centre solver returned an invalid solution.")
    return cube, moves


def _sample_reduced(cube: Cube) -> Cube:
    reduced: Cube = [
        [[None for _ in range(3)] for _ in range(3)] for _ in range(6)
    ]  # type: ignore[list-item]
    coordinates = (0, 1, 3)
    for face in range(6):
        for row in range(3):
            for column in range(3):
                reduced[face][row][column] = cube[face][coordinates[row]][coordinates[column]]
    return reduced


def _group_parity(
    cube: Cube, groups: Sequence[Sequence[str]], target_sets: Sequence[frozenset[str]]
) -> int:
    permutation: list[int] = []
    for group in groups:
        colors = frozenset(cube[int(face)][int(row)][int(column)] for face, row, column in group)
        try:
            permutation.append(target_sets.index(colors))
        except ValueError as exc:
            raise SolverFailedError("The reduced 4x4 cube contains an invalid piece.") from exc
    return _parity(permutation)


def _reduced_parities(cube: Cube) -> tuple[int, int, Cube]:
    reduced = _sample_reduced(cube)
    return (
        _group_parity(reduced, CORNERS, CORNER_TARGET_SETS),
        _group_parity(reduced, EDGES, EDGE_TARGET_SETS),
        reduced,
    )


def solve_4x4_detailed(
    cube: Cube,
) -> tuple[list[Move], list[list[Move]], list[str], Cube]:
    """Return ``(moves, stages, stage_notes, solved_cube)`` for a 4x4 cube."""
    validate_cube(cube)
    if cube_size(cube) != SIZE:
        raise SolverFailedError("The 4x4 solver only supports 4x4 cubes.")
    if is_solved(cube):
        return [], [], [], cube

    start_cube = cube
    geometry = _geometry_for_cube()
    stages: list[list[Move]] = []
    stage_notes: list[str] = []

    cube, wing_moves, wing_parity = _solve_wings(cube, geometry)
    if wing_parity:
        stages.append(list(OLL_PARITY))
        stage_notes.append("Fixing wing parity")
    if wing_moves:
        stages.append(wing_moves)
        stage_notes.append("Pairing and solving wings")

    cube, center_moves = _solve_centers(cube, geometry)
    if center_moves:
        stages.append(center_moves)
        stage_notes.append("Solving centres")

    corner_parity, edge_parity, reduced = _reduced_parities(cube)
    if corner_parity != edge_parity:
        cube = apply_moves(cube, PLL_PARITY)
        stages.append(list(PLL_PARITY))
        stage_notes.append("Fixing 3x3 parity")

        cube, center_moves = _solve_centers(cube, geometry)
        if center_moves:
            stages.append(center_moves)
            stage_notes.append("Repairing centres")

        corner_parity, edge_parity, reduced = _reduced_parities(cube)
        if corner_parity != edge_parity:
            raise SolverFailedError("Could not correct 4x4 3x3 parity.")

    finish_stages, _ = solve_beginner(reduced, "w")
    finish_moves = _expand_three_by_three_slices(
        [move for stage in finish_stages for move in stage]
    )
    if finish_moves:
        stages.append(finish_moves)
        stage_notes.append("Finishing as a 3x3")

    simplified_stages: list[list[Move]] = []
    simplified_notes: list[str] = []
    for stage, note in zip(stages, stage_notes, strict=True):
        simplified = _simplify_stage(stage)
        if simplified:
            simplified_stages.append(simplified)
            simplified_notes.append(note)

    stages = simplified_stages
    all_moves = [move for stage in stages for move in stage]
    solved = apply_moves(start_cube, all_moves)
    if not is_solved(solved):
        raise SolverFailedError("The 4x4 solver returned an invalid solution.")
    return all_moves, stages, simplified_notes, solved


def solve_4x4(cube: Cube) -> tuple[list[Move], list[list[Move]], Cube]:
    """Return ``(moves, stages, solved_cube)`` for a 4x4 cube."""
    moves, stages, _stage_notes, solved = solve_4x4_detailed(cube)
    return moves, stages, solved
