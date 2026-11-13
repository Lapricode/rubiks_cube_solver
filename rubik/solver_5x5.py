"""In-house 5x5 reduction solver.

The solver reduces the cube with pure three-cycle macros for x-centres,
t-centres, wings and midges, corrects edge parity, then finishes with the
existing beginner solver on the reduced 3x3.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence

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
from .solvers import SolverFailedError, solve_beginner

SIZE = 5
FACE_NAMES = ["R", "L", "U", "D", "F", "B"]
ALL_MOVES = [
    move
    for faces in (
        FACE_NAMES,
        [face.lower() for face in FACE_NAMES],
        [f"{face}w" for face in FACE_NAMES],
    )
    for face in faces
    for suffix in ("", "'", "2")
    for move in (face + suffix,)
] + [face + suffix for face in "MES" for suffix in ("", "'", "2")]

WING_MACRO = "R U R' u R U' R' u'".split()
MIDGE_MACRO = "L U' M U L' U' M' U".split()
X_MACRO = "r u r' u' R u r u' r' R'".split()
T_MACRO = "L E' l E L' E' l' E".split()
FLIP_MACRO = "L U M' U2 M2 U L' U' M2 U2 M U'".split()

POSITIONS = [
    (int(face), row, column) for face in range(6) for row in range(SIZE) for column in range(SIZE)
]
POSITION_INDEX = {position: index for index, position in enumerate(POSITIONS)}
X_CENTER_POSITIONS = tuple(
    position for position in POSITIONS if position[1] in (1, 3) and position[2] in (1, 3)
)
T_CENTER_POSITIONS = tuple(
    position
    for position in POSITIONS
    if (position[1] in (1, 3) and position[2] == 2) or (position[1] == 2 and position[2] in (1, 3))
)
EDGE_POSITIONS = {
    position for position in POSITIONS if (position[1] in (0, 4)) ^ (position[2] in (0, 4))
}
WING_SEED = ((int(Face.BACK), 3, 4), (int(Face.RIGHT), 0, 1))
MIDGE_SEED = ((int(Face.DOWN), 0, 2), (int(Face.BACK), 0, 2))


def _build_sticker_moves() -> dict[str, list[int]]:
    labeled = [
        [
            [face * SIZE * SIZE + row * SIZE + column for column in range(SIZE)]
            for row in range(SIZE)
        ]
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
            POSITION_INDEX[locations[face * SIZE * SIZE + row * SIZE + column]]
            for face, row, column in POSITIONS
        ]
    return maps


_STICKER_MOVES: dict[str, list[int]] | None = None


def _sticker_moves() -> dict[str, list[int]]:
    global _STICKER_MOVES
    if _STICKER_MOVES is None:
        _STICKER_MOVES = _build_sticker_moves()
    return _STICKER_MOVES


def _orbit(seed: tuple[tuple[int, int, int], ...]) -> list[tuple[tuple[int, int, int], ...]]:
    sticker_moves = _sticker_moves()
    pairs: list[tuple[tuple[int, int, int], ...]] = []
    seen = {seed}
    queue: deque[tuple[tuple[int, int, int], ...]] = deque([seed])
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
    return pairs


def _build_wing_pairs() -> tuple[tuple[tuple[int, int, int], ...], ...]:
    pairs = _orbit(WING_SEED)
    if (
        len(pairs) != 24
        or len({position for pair in pairs for position in pair}) != 48
        or not {position for pair in pairs for position in pair} <= EDGE_POSITIONS
    ):
        raise SolverFailedError("Could not derive the 5x5 wing geometry.")
    return tuple(pairs)


def _build_midge_pairs() -> tuple[tuple[tuple[int, int, int], ...], ...]:
    pairs: list[tuple[tuple[int, int, int], ...]] = []
    seen: set[frozenset[tuple[int, int, int]]] = set()
    for pair in _orbit(MIDGE_SEED):
        key = frozenset(pair)
        if key not in seen:
            seen.add(key)
            pairs.append(pair)
    if len(pairs) != 12:
        raise SolverFailedError("Could not derive the 5x5 midge geometry.")
    return tuple(pairs)


def _build_piece_moves(
    pieces: Sequence[tuple[tuple[int, int, int], ...]],
    canonical: Callable[
        [tuple[tuple[int, int, int], ...]],
        tuple[tuple[int, int, int], ...] | frozenset[tuple[int, int, int]],
    ],
) -> dict[str, list[int]]:
    sticker_moves = _sticker_moves()
    piece_index = {canonical(piece): index for index, piece in enumerate(pieces)}
    moves: dict[str, list[int]] = {}
    for move in ALL_MOVES:
        table: list[int] = []
        for piece in pieces:
            next_piece = canonical(
                tuple(
                    POSITIONS[sticker_moves[move][POSITION_INDEX[position]]] for position in piece
                )
            )
            table.append(piece_index[next_piece])
        moves[move] = table
    return moves


def _build_center_moves(
    positions: Sequence[tuple[int, int, int]],
) -> dict[str, list[int]]:
    sticker_moves = _sticker_moves()
    center_index = {position: index for index, position in enumerate(positions)}
    moves: dict[str, list[int]] = {}
    for move in ALL_MOVES:
        moves[move] = [
            center_index[POSITIONS[sticker_moves[move][POSITION_INDEX[position]]]]
            for position in positions
        ]
    return moves


def _macro_support(
    move_tables: dict[str, list[int]], macro: Sequence[Move]
) -> tuple[int, int, int]:
    permutation = list(range(len(next(iter(move_tables.values())))))
    for move in macro:
        permutation = [move_tables[move][value] for value in permutation]
    moved = [index for index, value in enumerate(permutation) if value != index]
    if len(moved) != 3:
        raise SolverFailedError("The 5x5 macro is not a pure three-cycle.")
    first, second, third = moved
    if permutation[first] != second or permutation[second] != third or permutation[third] != first:
        raise SolverFailedError("The 5x5 macro is not a three-cycle.")
    return first, second, third


def _build_setup_tables(move_tables: dict[str, list[int]], support: tuple[int, int, int]) -> tuple[
    dict[tuple[int, int, int], tuple[int, int, int] | None],
    dict[tuple[int, int, int], Move],
]:
    parent: dict[tuple[int, int, int], tuple[int, int, int] | None] = {support: None}
    move_for_state: dict[tuple[int, int, int], Move] = {}
    queue: deque[tuple[int, int, int]] = deque([support])
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


class _Geometry:
    __slots__ = (
        "wing_pairs",
        "wing_targets",
        "wing_target_index",
        "wing_moves",
        "wing_support",
        "wing_setup_parent",
        "wing_setup_move",
        "midge_pairs",
        "midge_targets",
        "midge_target_index",
        "midge_moves",
        "midge_support",
        "midge_setup_parent",
        "midge_setup_move",
        "flip_support",
        "flip_setup_parent",
        "flip_setup_move",
        "x_positions",
        "x_targets",
        "x_moves",
        "x_support",
        "x_setup_parent",
        "x_setup_move",
        "t_positions",
        "t_targets",
        "t_moves",
        "t_support",
        "t_setup_parent",
        "t_setup_move",
    )

    def __init__(self) -> None:
        solved = solved_cube(SIZE)

        def identity(
            piece: tuple[tuple[int, int, int], ...],
        ) -> tuple[tuple[int, int, int], ...]:
            return piece

        self.wing_pairs = _build_wing_pairs()
        self.wing_targets = [
            tuple(solved[face][row][column] for face, row, column in pair)
            for pair in self.wing_pairs
        ]
        self.wing_target_index = {target: index for index, target in enumerate(self.wing_targets)}
        self.wing_moves = _build_piece_moves(self.wing_pairs, identity)
        self.wing_support = _macro_support(self.wing_moves, WING_MACRO)
        self.wing_setup_parent, self.wing_setup_move = _build_setup_tables(
            self.wing_moves, self.wing_support
        )

        self.midge_pairs = _build_midge_pairs()
        self.midge_targets = [
            tuple(solved[face][row][column] for face, row, column in pair)
            for pair in self.midge_pairs
        ]
        self.midge_target_index = {
            frozenset(target): index for index, target in enumerate(self.midge_targets)
        }
        self.midge_moves = _build_piece_moves(self.midge_pairs, frozenset)
        self.midge_support = _macro_support(self.midge_moves, MIDGE_MACRO)
        self.midge_setup_parent, self.midge_setup_move = _build_setup_tables(
            self.midge_moves, self.midge_support
        )

        self.flip_support = _build_flip_support(self.midge_pairs)
        self.flip_setup_parent, self.flip_setup_move = _build_flip_setup_tables(
            self.midge_moves, self.flip_support
        )

        self.x_positions = X_CENTER_POSITIONS
        self.x_targets = [solved[face][row][column] for face, row, column in self.x_positions]
        self.x_moves = _build_center_moves(self.x_positions)
        self.x_support = _macro_support(self.x_moves, X_MACRO)
        self.x_setup_parent, self.x_setup_move = _build_setup_tables(self.x_moves, self.x_support)

        self.t_positions = T_CENTER_POSITIONS
        self.t_targets = [solved[face][row][column] for face, row, column in self.t_positions]
        self.t_moves = _build_center_moves(self.t_positions)
        self.t_support = _macro_support(self.t_moves, T_MACRO)
        self.t_setup_parent, self.t_setup_move = _build_setup_tables(self.t_moves, self.t_support)


def _build_flip_support(
    midge_pairs: Sequence[tuple[tuple[int, int, int], ...]],
) -> tuple[int, int]:
    moved_cube = apply_moves(solved_cube(SIZE), FLIP_MACRO)
    moved = {
        (face, row, column)
        for face, row, column in POSITIONS
        if moved_cube[face][row][column] != solved_cube(SIZE)[face][row][column]
    }
    support: list[int] = []
    for index, pair in enumerate(midge_pairs):
        if set(pair) & moved:
            support.append(index)
    if len(support) != 2:
        raise SolverFailedError("Could not derive the 5x5 midge flip geometry.")
    return support[0], support[1]


def _build_flip_setup_tables(move_tables: dict[str, list[int]], support: tuple[int, int]) -> tuple[
    dict[frozenset[int], frozenset[int] | None],
    dict[frozenset[int], Move],
]:
    start = frozenset(support)
    parent: dict[frozenset[int], frozenset[int] | None] = {start: None}
    move_for_state: dict[frozenset[int], Move] = {}
    queue: deque[frozenset[int]] = deque([start])
    while queue:
        state = queue.popleft()
        for move in ALL_MOVES:
            table = move_tables[move]
            next_state = frozenset(table[index] for index in state)
            if len(next_state) != 2:
                raise SolverFailedError("The 5x5 midge flip support degenerated.")
            if next_state not in parent:
                parent[next_state] = state
                move_for_state[next_state] = move
                queue.append(next_state)
    return parent, move_for_state


_geometry: _Geometry | None = None


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
    parent: (
        dict[tuple[int, int, int], tuple[int, int, int] | None]
        | dict[frozenset[int], frozenset[int] | None]
    ),
    move_for_state: dict[tuple[int, int, int], Move] | dict[frozenset[int], Move],
    target: tuple[int, int, int] | frozenset[int],
) -> list[Move]:
    if target not in parent:
        raise SolverFailedError("Could not conjugate a 5x5 three-cycle.")
    path: list[Move] = []
    state = target
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


def _apply_flip(
    cube: Cube,
    parent: dict[frozenset[int], frozenset[int] | None],
    move_for_state: dict[frozenset[int], Move],
    target: frozenset[int],
) -> tuple[Cube, list[Move]]:
    setup = _setup_path(parent, move_for_state, target)
    inverse = _inverse_moves(setup)
    cube = apply_moves(cube, inverse)
    cube = apply_moves(cube, FLIP_MACRO)
    cube = apply_moves(cube, setup)
    return cube, inverse + list(FLIP_MACRO) + setup


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
                raise SolverFailedError("Could not resolve a 5x5 two-cycle.")
        else:
            third = current[second]
        if third in (first, second):
            raise SolverFailedError("Could not build a 5x5 three-cycle.")
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
    try:
        return [
            geometry.wing_target_index[tuple(cube[face][row][column] for face, row, column in pair)]
            for pair in geometry.wing_pairs
        ]
    except KeyError as exc:
        raise SolverFailedError("The cube contains an invalid 5x5 wing.") from exc


def _solve_wings(cube: Cube, geometry: _Geometry) -> tuple[Cube, list[Move]]:
    permutation = _wing_permutation(cube, geometry)
    if _parity(permutation):
        raise SolverFailedError("5x5 wing parity must be corrected before sorting.")
    cube, moves = _sort_permutation(
        cube,
        permutation,
        geometry.wing_setup_parent,
        geometry.wing_setup_move,
        WING_MACRO,
    )
    if _wing_permutation(cube, geometry) != list(range(24)):
        raise SolverFailedError("The 5x5 wing solver returned an invalid solution.")
    return cube, moves


def _center_permutation(
    cube: Cube,
    positions: Sequence[tuple[int, int, int]],
    targets: Sequence[str],
) -> list[int]:
    current = [cube[face][row][column] for face, row, column in positions]
    destinations: list[int | None] = [None] * len(current)
    for color in FACE_COLORS:
        current_positions = [index for index, value in enumerate(current) if value == color]
        target_positions = [index for index, value in enumerate(targets) if value == color]
        if len(current_positions) != len(target_positions) or len(current_positions) != 4:
            raise SolverFailedError("The cube contains invalid 5x5 centres.")
        for source, destination in zip(current_positions, target_positions, strict=True):
            destinations[source] = destination
    permutation = [int(value) for value in destinations]
    if _parity(permutation):
        for color in FACE_COLORS:
            positions_for_color = [index for index, value in enumerate(current) if value == color]
            if len(positions_for_color) >= 2:
                first, second = positions_for_color[:2]
                permutation[first], permutation[second] = permutation[second], permutation[first]
                break
    return permutation


def _solve_center_orbit(
    cube: Cube,
    positions: Sequence[tuple[int, int, int]],
    targets: Sequence[str],
    parent: dict[tuple[int, int, int], tuple[int, int, int] | None],
    move_for_state: dict[tuple[int, int, int], Move],
    macro: Sequence[Move],
) -> tuple[Cube, list[Move]]:
    permutation = _center_permutation(cube, positions, targets)
    cube, moves = _sort_permutation(cube, permutation, parent, move_for_state, macro)
    current = [cube[face][row][column] for face, row, column in positions]
    if current != list(targets):
        raise SolverFailedError("The 5x5 centre solver returned an invalid solution.")
    return cube, moves


def _solve_centers(cube: Cube, geometry: _Geometry) -> tuple[Cube, list[Move]]:
    moves: list[Move] = []
    cube, x_moves = _solve_center_orbit(
        cube,
        geometry.x_positions,
        geometry.x_targets,
        geometry.x_setup_parent,
        geometry.x_setup_move,
        X_MACRO,
    )
    moves.extend(x_moves)
    cube, t_moves = _solve_center_orbit(
        cube,
        geometry.t_positions,
        geometry.t_targets,
        geometry.t_setup_parent,
        geometry.t_setup_move,
        T_MACRO,
    )
    moves.extend(t_moves)
    return cube, moves


def _midge_permutation(cube: Cube, geometry: _Geometry) -> list[int]:
    try:
        return [
            geometry.midge_target_index[
                frozenset(cube[face][row][column] for face, row, column in pair)
            ]
            for pair in geometry.midge_pairs
        ]
    except KeyError as exc:
        raise SolverFailedError("The cube contains an invalid 5x5 midge.") from exc


def _solve_midges(cube: Cube, geometry: _Geometry) -> tuple[Cube, list[Move]]:
    permutation = _midge_permutation(cube, geometry)
    if _parity(permutation):
        raise SolverFailedError("5x5 midge parity must be corrected before sorting.")
    cube, moves = _sort_permutation(
        cube,
        permutation,
        geometry.midge_setup_parent,
        geometry.midge_setup_move,
        MIDGE_MACRO,
    )
    if _midge_permutation(cube, geometry) != list(range(12)):
        raise SolverFailedError("The 5x5 midge solver returned an invalid solution.")
    return cube, moves


def _flipped_midges(cube: Cube, geometry: _Geometry) -> list[int]:
    flipped: list[int] = []
    for index, pair in enumerate(geometry.midge_pairs):
        current = tuple(cube[face][row][column] for face, row, column in pair)
        target = geometry.midge_targets[index]
        if current == target:
            continue
        if current == target[::-1]:
            flipped.append(index)
        else:
            raise SolverFailedError("The cube contains invalid 5x5 midge colours.")
    return flipped


def _fix_midge_orientation(cube: Cube, geometry: _Geometry) -> tuple[Cube, list[Move]]:
    flipped = _flipped_midges(cube, geometry)
    if len(flipped) % 2:
        raise SolverFailedError("Could not correct 5x5 midge orientation.")
    moves: list[Move] = []
    for first, second in zip(flipped[0::2], flipped[1::2], strict=True):
        cube, flip_moves = _apply_flip(
            cube,
            geometry.flip_setup_parent,
            geometry.flip_setup_move,
            frozenset((first, second)),
        )
        moves.extend(flip_moves)
    if _flipped_midges(cube, geometry):
        raise SolverFailedError("Could not correct 5x5 midge orientation.")
    return cube, moves


def _align_fixed_centers(cube: Cube) -> tuple[Cube, list[Move]]:
    target = tuple(solved_cube(SIZE)[index][2][2] for index in range(6))
    if tuple(cube[index][2][2] for index in range(6)) == target:
        return cube, []
    rotations = ["x", "x'", "y", "y'", "z", "z'"]
    start = tuple(cube[index][2][2] for index in range(6))
    queue: deque[tuple[Cube, list[Move]]] = deque([(cube, [])])
    seen = {start}
    while queue:
        state, moves = queue.popleft()
        if len(moves) >= 5:
            continue
        for rotation in rotations:
            next_cube = apply_move(state, rotation)
            next_moves = moves + [rotation]
            key = tuple(next_cube[index][2][2] for index in range(6))
            if key == target:
                return next_cube, next_moves
            if key not in seen:
                seen.add(key)
                queue.append((next_cube, next_moves))
    raise SolverFailedError("Could not align the 5x5 fixed centres.")


def _sample_reduced(cube: Cube) -> Cube:
    reduced: Cube = [
        [[None for _ in range(3)] for _ in range(3)] for _ in range(6)
    ]  # type: ignore[list-item]
    coordinates = (0, 2, 4)
    for face in range(6):
        for row in range(3):
            for column in range(3):
                reduced[face][row][column] = cube[face][coordinates[row]][coordinates[column]]
    return reduced


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


def _repair_after_finish(
    cube: Cube,
    geometry: _Geometry,
    add_stage: Callable[[Sequence[Move], str], None],
) -> Cube:
    cube, moves = _align_fixed_centers(cube)
    add_stage(moves, "Re-aligning fixed centres")
    cube, moves = _solve_centers(cube, geometry)
    add_stage(moves, "Repairing centres")

    if _parity(_wing_permutation(cube, geometry)):
        cube = apply_move(cube, "r")
        add_stage(["r"], "Fixing wing parity")
        cube, moves = _solve_centers(cube, geometry)
        add_stage(moves, "Repairing centres")
        if _parity(_wing_permutation(cube, geometry)):
            raise SolverFailedError("Could not correct 5x5 wing parity.")

    cube, moves = _solve_wings(cube, geometry)
    add_stage(moves, "Repairing wings")

    if _parity(_midge_permutation(cube, geometry)):
        cube = apply_move(cube, "R")
        add_stage(["R"], "Fixing midge parity")
        cube, moves = _solve_wings(cube, geometry)
        add_stage(moves, "Repairing wings")
        if _parity(_midge_permutation(cube, geometry)):
            raise SolverFailedError("Could not correct 5x5 midge parity.")
        if _parity(_wing_permutation(cube, geometry)):
            raise SolverFailedError("5x5 wing parity was not preserved.")

    cube, moves = _solve_midges(cube, geometry)
    add_stage(moves, "Repairing midges")
    cube, moves = _fix_midge_orientation(cube, geometry)
    add_stage(moves, "Repairing midge orientation")
    return cube


def solve_5x5_detailed(
    cube: Cube,
) -> tuple[list[Move], list[list[Move]], list[str], Cube]:
    """Return ``(moves, stages, stage_notes, solved_cube)`` for a 5x5 cube."""
    validate_cube(cube)
    if cube_size(cube) != SIZE:
        raise SolverFailedError("The 5x5 solver only supports 5x5 cubes.")
    if is_solved(cube):
        return [], [], [], cube

    start_cube = cube
    geometry = _geometry_for_cube()
    stages: list[list[Move]] = []
    stage_notes: list[str] = []

    def add_stage(moves: Sequence[Move], note: str) -> None:
        simplified = _simplify_stage(moves)
        if simplified:
            stages.append(simplified)
            stage_notes.append(note)

    cube, moves = _align_fixed_centers(cube)
    add_stage(moves, "Aligning fixed centres")
    cube, moves = _solve_centers(cube, geometry)
    add_stage(moves, "Solving centres")

    if _parity(_wing_permutation(cube, geometry)):
        cube = apply_move(cube, "r")
        add_stage(["r"], "Fixing wing parity")
        cube, moves = _solve_centers(cube, geometry)
        add_stage(moves, "Repairing centres")
        if _parity(_wing_permutation(cube, geometry)):
            raise SolverFailedError("Could not correct 5x5 wing parity.")

    cube, moves = _solve_wings(cube, geometry)
    add_stage(moves, "Solving wings")

    if _parity(_midge_permutation(cube, geometry)):
        cube = apply_move(cube, "R")
        add_stage(["R"], "Fixing midge parity")
        cube, moves = _solve_wings(cube, geometry)
        add_stage(moves, "Repairing wings")
        if _parity(_midge_permutation(cube, geometry)):
            raise SolverFailedError("Could not correct 5x5 midge parity.")
        if _parity(_wing_permutation(cube, geometry)):
            raise SolverFailedError("5x5 wing parity was not preserved.")

    cube, moves = _solve_midges(cube, geometry)
    add_stage(moves, "Solving midges")
    cube, moves = _fix_midge_orientation(cube, geometry)
    add_stage(moves, "Fixing midge orientation")

    reduced = _sample_reduced(cube)
    finish_stages, _ = solve_beginner(reduced, "w")
    finish_moves = [move for stage in finish_stages for move in stage]
    cube = apply_moves(cube, finish_moves)
    add_stage(finish_moves, "Finishing as a 3x3")

    cube = _repair_after_finish(cube, geometry, add_stage)

    solved = cube
    if not is_solved(solved):
        raise SolverFailedError("The 5x5 solver returned an invalid solution.")
    all_moves = [move for stage in stages for move in stage]
    if not is_solved(apply_moves(start_cube, all_moves)):
        raise SolverFailedError("The 5x5 solver returned an invalid solution.")
    return all_moves, stages, stage_notes, solved


def solve_5x5(cube: Cube) -> tuple[list[Move], list[list[Move]], Cube]:
    """Return ``(moves, stages, solved_cube)`` for a 5x5 cube."""
    moves, stages, _stage_notes, solved = solve_5x5_detailed(cube)
    return moves, stages, solved
