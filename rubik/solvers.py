"""Cube solving algorithms.

The beginner method is implemented directly.  CFOP and Kociemba are delegated
to the external ``rubik_solver`` package, imported lazily so the application
still starts when that optional dependency is missing.
"""

from __future__ import annotations

import importlib
import sys
import types

from .config import Face
from .cube import (
    Cube,
    apply_move,
    apply_moves,
    copy_cube,
    cube_size,
    face_centres,
    get_colors_rubik_solver_library,
    improve_moves_sequence,
    is_solved,
    validate_cube,
)

# Edge/corner positions in the beginner solver, ordered as:
# down edges, middle edges, up edges / down corners, up corners.
EDGES = [
    ["101", "001"],
    ["112", "210"],
    ["121", "521"],
    ["110", "412"],
    ["012", "401"],
    ["201", "010"],
    ["510", "221"],
    ["421", "512"],
    ["301", "021"],
    ["310", "212"],
    ["321", "501"],
    ["312", "410"],
]
CORNERS = [
    ["122", "220", "520"],
    ["120", "522", "422"],
    ["100", "402", "002"],
    ["102", "000", "200"],
    ["320", "222", "500"],
    ["322", "502", "420"],
    ["302", "400", "022"],
    ["300", "020", "202"],
]


class SolverError(Exception):
    """Base class for errors raised while solving a cube."""


class SolverLibraryNotInstalledError(SolverError):
    """Raised when an optional external solver package is not installed."""


class SolverFailedError(SolverError):
    """Raised when a solver cannot produce a valid solution."""


def _flatten_move_groups(move_groups: list[list[str]]) -> list[str]:
    return [move for group in move_groups for move in group]


def _put_centre_down(cube: Cube, initial_solved_color: str) -> tuple[Cube, list[str]]:
    rotation_moves = [["x"], [], ["z'"], ["x", "x"], ["z"], ["x'"]]
    moves = rotation_moves[face_centres(cube).index(initial_solved_color)]
    return apply_moves(cube, moves), list(moves)


def _solve_down_cross(
    cube: Cube, initial_solved_color: str, middle_centres: list[str]
) -> tuple[Cube, list[str]]:
    rubiks_cube2 = cube
    solve_moves: list[list[str]] = []
    cross_pieces_solved: list[str] = []
    edges_examined = [EDGES[k] for k in range(len(EDGES) - 1, -1, -1)]
    for _ in range(4):
        for edge in edges_examined:
            edge_colors = [
                rubiks_cube2[int(edge[0][0])][int(edge[0][1])][int(edge[0][2])],
                rubiks_cube2[int(edge[1][0])][int(edge[1][1])][int(edge[1][2])],
            ]
            if initial_solved_color in edge_colors:
                not_cross_color = edge_colors[1 - edge_colors.index(initial_solved_color)]
                if not_cross_color not in cross_pieces_solved:
                    edge_layer = EDGES.index(edge) // 4
                    if (
                        edge_layer == 0
                        and edge_colors[0] == initial_solved_color
                        and edge_colors[1] == rubiks_cube2[int(edge[1][0])][1][1]
                    ):
                        cross_pieces_solved.append(not_cross_color)
                    else:
                        # Put edge in front up middle position.
                        rubiks_cube2 = apply_moves(
                            rubiks_cube2,
                            [
                                [],
                                ["y" + (abs([0, 2, 2][edge_layer] - int(edge[0][2])) // 2) * "'"],
                                ["y", "y"],
                            ][2 - int(edge[0][1])]
                            + [
                                ["F", "F"],
                                ["F'", "U'", "F", "U"],
                                [],
                            ][edge_layer],
                        )
                        solve_moves.append(
                            [
                                [],
                                ["y" + (abs([0, 2, 2][edge_layer] - int(edge[0][2])) // 2) * "'"],
                                ["y", "y"],
                            ][2 - int(edge[0][1])]
                            + [
                                ["F", "F"],
                                ["F'", "U'", "F", "U"],
                                [],
                            ][edge_layer]
                        )
                        # Put edge in the correct position.
                        offset = middle_centres.index(
                            rubiks_cube2[Face.FRONT][1][1]
                        ) - middle_centres.index(not_cross_color)
                        edge_orientation = edge_colors.index(initial_solved_color)
                        rubiks_cube2 = apply_moves(
                            rubiks_cube2,
                            [
                                [
                                    ["F'", "F'"],
                                    ["U", "L", "L"],
                                    ["U", "U", "B", "B"],
                                    ["U'", "R", "R"],
                                ],
                                [
                                    ["U'", "M'", "U", "M"],
                                    ["F'", "L", "F"],
                                    ["U", "M", "U", "M'"],
                                    ["F", "R'", "F'"],
                                ],
                            ][edge_orientation][offset],
                        )
                        solve_moves.append(
                            [
                                [
                                    ["F'", "F'"],
                                    ["U", "L", "L"],
                                    ["U", "U", "B", "B"],
                                    ["U'", "R", "R"],
                                ],
                                [
                                    ["U'", "M'", "U", "M"],
                                    ["F'", "L", "F"],
                                    ["U", "M", "U", "M'"],
                                    ["F", "R'", "F'"],
                                ],
                            ][edge_orientation][offset]
                        )
                        cross_pieces_solved.append(not_cross_color)
                        break
    return rubiks_cube2, _flatten_move_groups(solve_moves)


def _solve_down_corners(
    cube: Cube, initial_solved_color: str, middle_centres: list[str]
) -> tuple[Cube, list[str]]:
    rubiks_cube2 = cube
    solve_moves: list[list[str]] = []
    down_corners_solved: list[list[str]] = []
    corners_examined = [CORNERS[k] for k in range(len(CORNERS) - 1, -1, -1)]
    for _ in range(4):
        for corner in corners_examined:
            corner_colors = [
                rubiks_cube2[int(corner[0][0])][int(corner[0][1])][int(corner[0][2])],
                rubiks_cube2[int(corner[1][0])][int(corner[1][1])][int(corner[1][2])],
                rubiks_cube2[int(corner[2][0])][int(corner[2][1])][int(corner[2][2])],
            ]
            if initial_solved_color in corner_colors:
                other_corner_colors = [
                    corner_colors[corner_colors.index(initial_solved_color) - 1],
                    corner_colors[corner_colors.index(initial_solved_color) - 2],
                ]
                if (
                    other_corner_colors not in down_corners_solved
                    and [other_corner_colors[1], other_corner_colors[0]] not in down_corners_solved
                ):
                    corner_layer = CORNERS.index(corner) // 4
                    if (
                        corner_layer == 0
                        and corner_colors[0] == initial_solved_color
                        and corner_colors[1] == rubiks_cube2[int(corner[1][0])][1][1]
                        and corner_colors[2] == rubiks_cube2[int(corner[2][0])][1][1]
                    ):
                        down_corners_solved.append(other_corner_colors)
                    else:
                        # Put corner in front up right position.
                        rubiks_cube2 = apply_moves(
                            rubiks_cube2,
                            [
                                [["y"], ["y", "y"]][corner_layer],
                                [
                                    ["y", "y"],
                                    [],
                                    ["y"],
                                    ["y'"],
                                ][int(int(corner[0][1]) / 2 + 2 * corner_layer)],
                                [["y'"], []][corner_layer],
                            ][int((int(corner[0][1]) + int(corner[0][2])) / 2)]
                            + [
                                ["R", "U", "R'", "U'"],
                                [],
                            ][corner_layer],
                        )
                        solve_moves.append(
                            [
                                [["y"], ["y", "y"]][corner_layer],
                                [
                                    ["y", "y"],
                                    [],
                                    ["y"],
                                    ["y'"],
                                ][int(int(corner[0][1]) / 2 + 2 * corner_layer)],
                                [["y'"], []][corner_layer],
                            ][int((int(corner[0][1]) + int(corner[0][2])) / 2)]
                            + [
                                ["R", "U", "R'", "U'"],
                                [],
                            ][corner_layer]
                        )
                        # Put corner in the correct position.
                        offset = [
                            2,
                            [
                                1,
                                3,
                            ][
                                [True, False].index(
                                    rubiks_cube2[Face.FRONT][1][1] in other_corner_colors
                                )
                            ],
                            0,
                        ][
                            [
                                rubiks_cube2[Face.FRONT][1][1] in other_corner_colors,
                                rubiks_cube2[Face.RIGHT][1][1] in other_corner_colors,
                            ].count(True)
                        ]
                        corner_orientation = [
                            rubiks_cube2[Face.UP][2][2] == initial_solved_color,
                            rubiks_cube2[Face.FRONT][0][2] == initial_solved_color,
                            rubiks_cube2[Face.RIGHT][2][0] == initial_solved_color,
                        ].index(True)
                        rubiks_cube2 = apply_moves(
                            rubiks_cube2,
                            [
                                [
                                    [
                                        "R",
                                        "U'",
                                        "U'",
                                        "R'",
                                        "U'",
                                        "R",
                                        "U",
                                        "R'",
                                    ],
                                    [
                                        "U",
                                        "L'",
                                        "U",
                                        "L",
                                        "U",
                                        "U",
                                        "L'",
                                        "U'",
                                        "L",
                                    ],
                                    [
                                        "L",
                                        "U",
                                        "L'",
                                        "U",
                                        "L",
                                        "U'",
                                        "L'",
                                    ],
                                    [
                                        "U'",
                                        "R'",
                                        "U",
                                        "U",
                                        "R",
                                        "U",
                                        "R'",
                                        "U'",
                                        "R",
                                    ],
                                ],
                                [
                                    ["U", "R", "U'", "R'"],
                                    ["U", "L'", "U'", "L"],
                                    ["L", "U", "U", "L'"],
                                    ["B", "U'", "B'"],
                                ],
                                [
                                    ["R", "U", "R'"],
                                    ["L'", "U", "L"],
                                    ["U", "U", "L", "U", "L'"],
                                    ["U'", "U'", "R'", "U", "R"],
                                ],
                            ][corner_orientation][offset],
                        )
                        solve_moves.append(
                            [
                                [
                                    [
                                        "R",
                                        "U'",
                                        "U'",
                                        "R'",
                                        "U'",
                                        "R",
                                        "U",
                                        "R'",
                                    ],
                                    [
                                        "U",
                                        "L'",
                                        "U",
                                        "L",
                                        "U",
                                        "U",
                                        "L'",
                                        "U'",
                                        "L",
                                    ],
                                    [
                                        "L",
                                        "U",
                                        "L'",
                                        "U",
                                        "L",
                                        "U'",
                                        "L'",
                                    ],
                                    [
                                        "U'",
                                        "R'",
                                        "U",
                                        "U",
                                        "R",
                                        "U",
                                        "R'",
                                        "U'",
                                        "R",
                                    ],
                                ],
                                [
                                    ["U", "R", "U'", "R'"],
                                    ["U", "L'", "U'", "L"],
                                    ["L", "U", "U", "L'"],
                                    ["B", "U'", "B'"],
                                ],
                                [
                                    ["R", "U", "R'"],
                                    ["L'", "U", "L"],
                                    ["U", "U", "L", "U", "L'"],
                                    ["U'", "U'", "R'", "U", "R"],
                                ],
                            ][corner_orientation][offset]
                        )
                        down_corners_solved.append(other_corner_colors)
                        break
    return rubiks_cube2, _flatten_move_groups(solve_moves)


def _solve_middle_edges(
    cube: Cube, final_solved_color: str, middle_centres: list[str]
) -> tuple[Cube, list[str]]:
    rubiks_cube2 = cube
    solve_moves: list[list[str]] = []
    middle_edges_solved: list[list[str]] = []
    edges_examined = [EDGES[k] for k in range(len(EDGES) - 1, 3, -1)]
    for _ in range(4):
        for edge in edges_examined:
            edge_colors = [
                rubiks_cube2[int(edge[0][0])][int(edge[0][1])][int(edge[0][2])],
                rubiks_cube2[int(edge[1][0])][int(edge[1][1])][int(edge[1][2])],
            ]
            if (
                final_solved_color not in edge_colors
                and edge_colors not in middle_edges_solved
                and [edge_colors[1], edge_colors[0]] not in middle_edges_solved
            ):
                edge_layer = EDGES[4:].index(edge) // 4
                if (
                    edge_layer == 0
                    and edge_colors[0] == rubiks_cube2[int(edge[0][0])][1][1]
                    and edge_colors[1] == rubiks_cube2[int(edge[1][0])][1][1]
                ):
                    middle_edges_solved.append(edge_colors)
                else:
                    # Put edge in front up middle position.
                    rubiks_cube2 = apply_moves(
                        rubiks_cube2,
                        [
                            [],
                            ["y" + ((2 - int(edge[0][2])) // 2) * "'"],
                            ["y", "y"],
                        ][2 - int(edge[0][1])]
                        + [
                            [
                                "F'",
                                "U",
                                "F",
                                "U",
                                "R",
                                "U'",
                                "R'",
                                "U'",
                            ],
                            [],
                        ][edge_layer],
                    )
                    solve_moves.append(
                        [
                            [],
                            ["y" + ((2 - int(edge[0][2])) // 2) * "'"],
                            ["y", "y"],
                        ][2 - int(edge[0][1])]
                        + [
                            [
                                "F'",
                                "U",
                                "F",
                                "U",
                                "R",
                                "U'",
                                "R'",
                                "U'",
                            ],
                            [],
                        ][edge_layer]
                    )
                    # Put edge in the correct position.
                    offset = middle_centres.index(
                        rubiks_cube2[Face.FRONT][1][1]
                    ) - middle_centres.index(edge_colors[1])
                    rubiks_cube2 = apply_moves(
                        rubiks_cube2,
                        [[], ["y'", "U"], ["y", "y", "U", "U"], ["y", "U'"]][offset],
                    )
                    solve_moves.append([[], ["y'", "U"], ["y", "y", "U", "U"], ["y", "U'"]][offset])
                    edge_orientation = [True, False].index(
                        edge_colors[0] == rubiks_cube2[Face.RIGHT][1][1]
                    )
                    rubiks_cube2 = apply_moves(
                        rubiks_cube2,
                        [
                            [
                                "U",
                                "R",
                                "U'",
                                "R'",
                                "U'",
                                "F'",
                                "U",
                                "F",
                            ],
                            [
                                "U'",
                                "L'",
                                "U",
                                "L",
                                "U",
                                "F",
                                "U'",
                                "F'",
                            ],
                        ][edge_orientation],
                    )
                    solve_moves.append(
                        [
                            [
                                "U",
                                "R",
                                "U'",
                                "R'",
                                "U'",
                                "F'",
                                "U",
                                "F",
                            ],
                            [
                                "U'",
                                "L'",
                                "U",
                                "L",
                                "U",
                                "F",
                                "U'",
                                "F'",
                            ],
                        ][edge_orientation]
                    )
                    middle_edges_solved.append(edge_colors)
                    break
    return rubiks_cube2, _flatten_move_groups(solve_moves)


def _solve_up_cross(
    cube: Cube, final_solved_color: str, middle_centres: list[str]
) -> tuple[Cube, list[str]]:
    rubiks_cube2 = cube
    solve_moves: list[list[str]] = []
    edges_examined = [edge for edge in EDGES[8:]]
    up_edges_colors = [
        rubiks_cube2[int(edge[0][0])][int(edge[0][1])][int(edge[0][2])] for edge in edges_examined
    ]
    up_case = int(up_edges_colors.count(final_solved_color) // 2)
    angle_line_case = [0, 1][
        [True, False].index(
            (up_edges_colors[0] == final_solved_color) ^ (up_edges_colors[2] == final_solved_color)
        )
    ]
    check_up_left_back_edge_color = [
        rubiks_cube2[Face.UP][0][1],
        rubiks_cube2[Face.UP][1][0],
    ]
    cross_moves = [
        ["F", "R", "U", "R'", "U'", "S", "R", "U", "R'", "U'", "S'", "F'"],
        [
            [
                ["U", "U"],
                [["U'"], ["U"]][
                    [True, False].index(check_up_left_back_edge_color[0] == final_solved_color)
                ],
                [],
            ][check_up_left_back_edge_color.count(final_solved_color)]
            + ["F", "U", "R", "U'", "R'", "F'"],
            [["U"], []][[True, False].index(check_up_left_back_edge_color[0] == final_solved_color)]
            + ["F", "R", "U", "R'", "U'", "F'"],
        ][angle_line_case],
        [],
    ][up_case]
    rubiks_cube2 = apply_moves(rubiks_cube2, cross_moves)
    solve_moves.append(cross_moves)

    not_cross_colors = [
        rubiks_cube2[int(edge[1][0])][int(edge[1][1])][int(edge[1][2])] for edge in edges_examined
    ]
    cross_orientation_moves = [["U", "U"], ["U'"], [], ["U"]][
        not_cross_colors.index(rubiks_cube2[Face.FRONT][1][1])
    ]
    rubiks_cube2 = apply_moves(rubiks_cube2, cross_orientation_moves)
    solve_moves.append(cross_orientation_moves)

    right_edge_offset = abs(
        middle_centres.index(rubiks_cube2[Face.RIGHT][1][1])
        - middle_centres.index(rubiks_cube2[Face.RIGHT][1][0])
    )
    left_edge_offset = abs(
        middle_centres.index(rubiks_cube2[Face.LEFT][1][1])
        - middle_centres.index(rubiks_cube2[Face.LEFT][1][2])
    )
    up_edge_moves = [
        [
            [],
            [
                "y'",
                "R",
                "U",
                "R'",
                "U",
                "R",
                "U'",
                "U'",
                "R'",
                "U",
            ],
        ][left_edge_offset % 2],
        [
            [
                "y",
                "y",
                "R",
                "U",
                "R'",
                "U",
                "R",
                "U'",
                "U'",
                "R'",
                "U",
            ],
            [
                "R",
                "R",
                "U'",
                "R'",
                "U'",
                "R",
                "U",
                "R",
                "U",
                "R",
                "U'",
                "R",
            ],
        ][left_edge_offset // 2],
        [
            [
                "R'",
                "U",
                "R'",
                "U'",
                "R'",
                "U'",
                "R'",
                "U",
                "R",
                "U",
                "R",
                "R",
            ],
            [
                "R",
                "U",
                "R'",
                "U'",
                "R'",
                "F",
                "R",
                "R",
                "U'",
                "R'",
                "U'",
                "R",
                "U",
                "R'",
                "F'",
            ],
        ][[0, 0, 1, 0][left_edge_offset]],
    ][[0, 1, 2, 1][right_edge_offset]]
    rubiks_cube2 = apply_moves(rubiks_cube2, up_edge_moves)
    solve_moves.append(up_edge_moves)
    return rubiks_cube2, _flatten_move_groups(solve_moves)


def _solve_up_corners(
    cube: Cube, final_solved_color: str, middle_centres: list[str]
) -> tuple[Cube, list[str]]:
    rubiks_cube2 = cube
    solve_moves: list[list[str]] = []
    up_corners_in_right_position: list[list[str]] = []
    corners_examined = CORNERS[4:]
    for corner in corners_examined:
        corner_colors = [
            rubiks_cube2[int(corner[0][0])][int(corner[0][1])][int(corner[0][2])],
            rubiks_cube2[int(corner[1][0])][int(corner[1][1])][int(corner[1][2])],
            rubiks_cube2[int(corner[2][0])][int(corner[2][1])][int(corner[2][2])],
        ]
        corner_centres_colors = [
            rubiks_cube2[int(corner[0][0])][1][1],
            rubiks_cube2[int(corner[1][0])][1][1],
            rubiks_cube2[int(corner[2][0])][1][1],
        ]
        if (
            (corner_colors[0] in corner_centres_colors)
            and (corner_colors[1] in corner_centres_colors)
            and (corner_colors[2] in corner_centres_colors)
        ):
            up_corners_in_right_position.append(corner)
    if len(up_corners_in_right_position) == 0:
        permutation_moves = [
            "U",
            "R",
            "U'",
            "L'",
            "U",
            "R'",
            "U'",
            "L",
        ]
        rubiks_cube2 = apply_moves(rubiks_cube2, permutation_moves)
        solve_moves.append(permutation_moves)
        for corner in corners_examined:
            corner_colors = [
                rubiks_cube2[int(corner[0][0])][int(corner[0][1])][int(corner[0][2])],
                rubiks_cube2[int(corner[1][0])][int(corner[1][1])][int(corner[1][2])],
                rubiks_cube2[int(corner[2][0])][int(corner[2][1])][int(corner[2][2])],
            ]
            corner_centres_colors = [
                rubiks_cube2[int(corner[0][0])][1][1],
                rubiks_cube2[int(corner[1][0])][1][1],
                rubiks_cube2[int(corner[2][0])][1][1],
            ]
            if (
                (corner_colors[0] in corner_centres_colors)
                and (corner_colors[1] in corner_centres_colors)
                and (corner_colors[2] in corner_centres_colors)
            ):
                corner_in_right_position = corner
                break
        corner_alignment_moves = [[], ["y"], ["y", "y"], ["y'"]][
            ["322", "302", "300", "320"].index(corner_in_right_position[0])
        ]
        rubiks_cube2 = apply_moves(rubiks_cube2, corner_alignment_moves)
        solve_moves.append(corner_alignment_moves)
    elif len(up_corners_in_right_position) == 1:
        corner_in_right_position = up_corners_in_right_position[0]
        corner_alignment_moves = [[], ["y"], ["y", "y"], ["y'"]][
            ["322", "302", "300", "320"].index(corner_in_right_position[0])
        ]
        rubiks_cube2 = apply_moves(rubiks_cube2, corner_alignment_moves)
        solve_moves.append(corner_alignment_moves)

    right_back_corner_centres_colors = [
        rubiks_cube2[Face.UP][1][1],
        rubiks_cube2[Face.RIGHT][1][1],
        rubiks_cube2[Face.BACK][1][1],
    ]
    if len(up_corners_in_right_position) != 4:
        position_index = [True, False].index(
            (rubiks_cube2[Face.UP][2][0] in right_back_corner_centres_colors)
            and (rubiks_cube2[Face.FRONT][0][0] in right_back_corner_centres_colors)
            and (rubiks_cube2[Face.LEFT][2][2] in right_back_corner_centres_colors)
        )
        corner_permutation_moves = [
            ["U", "R", "U'", "L'", "U", "R'", "U'", "L"],
            ["L'", "U", "R", "U'", "L", "U", "R'", "U'"],
        ][position_index]
        rubiks_cube2 = apply_moves(rubiks_cube2, corner_permutation_moves)
        solve_moves.append(corner_permutation_moves)

    for _ in range(4):
        orientation_index = [
            rubiks_cube2[Face.UP][2][2],
            rubiks_cube2[Face.FRONT][0][2],
            rubiks_cube2[Face.RIGHT][2][0],
        ].index(final_solved_color)
        corner_orientation_options = [
            [],
            4 * ["R'", "D'", "R", "D"],
            2 * ["R'", "D'", "R", "D"],
        ]
        corner_orientation_moves = corner_orientation_options[orientation_index] + ["U'"]
        rubiks_cube2 = apply_moves(rubiks_cube2, corner_orientation_moves)
        solve_moves.append(corner_orientation_moves)

    up_side_offset = middle_centres.index(rubiks_cube2[Face.FRONT][1][1]) - middle_centres.index(
        rubiks_cube2[Face.FRONT][0][1]
    )
    final_alignment_moves = [[], ["U"], ["U", "U"], ["U'"]][up_side_offset]
    rubiks_cube2 = apply_moves(rubiks_cube2, final_alignment_moves)
    solve_moves.append(final_alignment_moves)
    return rubiks_cube2, _flatten_move_groups(solve_moves)


def solve_beginner(cube: Cube, initial_solved_color: str) -> tuple[list[list[str]], Cube]:
    """Return ``(stages, solved_cube)`` for the beginner method.

    ``stages`` is a list of six move lists, one per solving stage.
    """
    validate_cube(cube)
    if cube_size(cube) != 3:
        raise SolverFailedError("The beginner solver only supports 3x3 cubes.")
    rubiks_cube2 = copy_cube(cube)
    final_solved_color = ["b", "r", "y", "g", "o", "w"][
        (["b", "r", "y", "g", "o", "w"].index(initial_solved_color) + 3) % 6
    ]
    middle_centres = [["r", "w", "o", "y"], ["g", "w", "b", "y"], ["b", "o", "g", "r"]][
        ["b", "r", "y", "g", "o", "w"].index(initial_solved_color) % 3
    ]
    if initial_solved_color in ["g", "o", "w"]:
        middle_centres.reverse()

    solve_moves2: list[list[str]] = []

    rubiks_cube2, moves = _put_centre_down(rubiks_cube2, initial_solved_color)
    solve_moves2.append(moves)

    rubiks_cube2, moves = _solve_down_cross(rubiks_cube2, initial_solved_color, middle_centres)
    solve_moves2.append(moves)

    rubiks_cube2, moves = _solve_down_corners(rubiks_cube2, initial_solved_color, middle_centres)
    solve_moves2.append(moves)

    rubiks_cube2, moves = _solve_middle_edges(rubiks_cube2, final_solved_color, middle_centres)
    solve_moves2.append(moves)

    rubiks_cube2, moves = _solve_up_cross(rubiks_cube2, final_solved_color, middle_centres)
    solve_moves2.append(moves)

    rubiks_cube2, moves = _solve_up_corners(rubiks_cube2, final_solved_color, middle_centres)
    solve_moves2.append(moves)

    if not is_solved(rubiks_cube2):
        raise SolverFailedError("The beginner solver could not solve the cube.")
    solve_moves2 = [improve_moves_sequence(stage) for stage in solve_moves2]
    return solve_moves2, rubiks_cube2


def _ensure_past_compatibility() -> None:
    """Provide ``past.builtins`` for rubik_solver on modern Python versions."""
    try:
        importlib.import_module("past.builtins")
    except ImportError:
        for module_name in [name for name in sys.modules if name.startswith("past")]:
            del sys.modules[module_name]
        past_module = types.ModuleType("past")
        past_module.__path__ = []
        past_builtins = types.ModuleType("past.builtins")
        past_builtins.basestring = str
        past_module.builtins = past_builtins
        sys.modules["past"] = past_module
        sys.modules["past.builtins"] = past_builtins


def solve_external(cube: Cube, method: str) -> tuple[list[str], list[str] | None, Cube]:
    """Solve with the external ``rubik_solver`` package.

    Returns ``(flat_moves, stage_moves, solved_cube)``.  ``stage_moves`` is a
    list of four stages for CFOP and ``None`` for Kociemba.
    """
    validate_cube(cube)
    if cube_size(cube) != 3:
        raise SolverFailedError("CFOP and Kociemba only support 3x3 cubes.")
    _ensure_past_compatibility()

    try:
        from rubik_solver import utils
    except ImportError as exc:
        raise SolverLibraryNotInstalledError(
            "The 'rubik_solver' package is required for CFOP and Kociemba."
        ) from exc

    solve_moves: list[str] = []
    centres = face_centres(cube)
    rotated_cube = apply_moves(
        cube,
        [["x"], [], ["z'"], ["x", "x"], ["z"], ["x'"]][centres.index("w")],
    )
    solve_moves.append(["x", "", "z'", "x2", "z", "x'"][centres.index("w")])
    centres = face_centres(rotated_cube)
    rotated_cube = apply_moves(
        rotated_cube,
        [["y'"], [], [], [], ["y", "y"], ["y"]][centres.index("b")],
    )
    solve_moves.append(["y'", "", "", "", "y2", "y"][centres.index("b")])

    cube_colors = get_colors_rubik_solver_library(rotated_cube)
    try:
        library_moves = utils.solve(cube_colors, method)
    except Exception as exc:
        raise SolverFailedError(f"The {method} solver failed: {exc}") from exc

    solve_moves = solve_moves + library_moves
    solve_moves = [
        [str(move), str(move).lower()][[True, False][str(move)[0] not in ["X", "Y", "Z"]]]
        for move in solve_moves
        if move != ""
    ]
    solve_moves = improve_moves_sequence(solve_moves)

    if method == "CFOP":
        rubiks_cube2 = copy_cube(cube)
        stage_moves: list[list[str]] = [[], [], [], []]
        stage = 0
        for move in solve_moves:
            white_cross_pieces_solved = [
                rubiks_cube2[Face.DOWN][1][1] == "w",
                rubiks_cube2[Face.DOWN][2][1] == "w",
                rubiks_cube2[Face.DOWN][1][0] == "w",
                rubiks_cube2[Face.DOWN][0][1] == "w",
                rubiks_cube2[Face.DOWN][1][2] == "w",
                rubiks_cube2[Face.FRONT][1][1] == rubiks_cube2[Face.FRONT][2][1],
                rubiks_cube2[Face.LEFT][1][1] == rubiks_cube2[Face.LEFT][1][0],
                rubiks_cube2[Face.BACK][1][1] == rubiks_cube2[Face.BACK][0][1],
                rubiks_cube2[Face.RIGHT][1][1] == rubiks_cube2[Face.RIGHT][1][2],
            ]
            solved_cross = white_cross_pieces_solved.count(True) == len(white_cross_pieces_solved)
            f2l_pieces_solved = [
                [
                    rubiks_cube2[Face.FRONT][1][0],
                    rubiks_cube2[Face.FRONT][2][0],
                    rubiks_cube2[Face.FRONT][1][2],
                    rubiks_cube2[Face.FRONT][2][2],
                ].count(rubiks_cube2[Face.FRONT][1][1])
                == 4,
                [
                    rubiks_cube2[Face.RIGHT][2][1],
                    rubiks_cube2[Face.RIGHT][2][2],
                    rubiks_cube2[Face.RIGHT][0][1],
                    rubiks_cube2[Face.RIGHT][0][2],
                ].count(rubiks_cube2[Face.RIGHT][1][1])
                == 4,
                [
                    rubiks_cube2[Face.BACK][1][2],
                    rubiks_cube2[Face.BACK][0][2],
                    rubiks_cube2[Face.BACK][1][0],
                    rubiks_cube2[Face.BACK][0][0],
                ].count(rubiks_cube2[Face.BACK][1][1])
                == 4,
                [
                    rubiks_cube2[Face.LEFT][0][1],
                    rubiks_cube2[Face.LEFT][0][0],
                    rubiks_cube2[Face.LEFT][2][1],
                    rubiks_cube2[Face.LEFT][2][0],
                ].count(rubiks_cube2[Face.LEFT][1][1])
                == 4,
            ]
            solved_f2l = solved_cross and f2l_pieces_solved.count(True) == len(f2l_pieces_solved)
            oll_pieces_solved = [rubiks_cube2[Face.UP][i][j] for j in range(3) for i in range(3)]
            solved_oll = solved_f2l and oll_pieces_solved.count("y") == len(oll_pieces_solved)
            stages_check = [solved_cross, solved_f2l, solved_oll]
            if stages_check.count(True) > stage:
                stage = stages_check.count(True)
            stage_moves[stage].append(move)
            rubiks_cube2 = apply_move(rubiks_cube2, move)
        if not is_solved(rubiks_cube2):
            raise SolverFailedError("The CFOP solver returned an invalid solution.")
        stage_moves = [improve_moves_sequence(stage) for stage in stage_moves]
        return solve_moves, stage_moves, rubiks_cube2

    rubiks_cube2 = apply_moves(cube, solve_moves)
    if not is_solved(rubiks_cube2):
        raise SolverFailedError("The Kociemba solver returned an invalid solution.")
    return solve_moves, None, rubiks_cube2
