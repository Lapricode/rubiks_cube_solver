from rubik.config import (
    CUBE_SIZES,
    MAX_CUBE_SIZE,
    MIN_CUBE_SIZE,
    auxiliary_piece_side_length,
    piece_side_length_for_size,
    piece_side_length_limits,
)


def test_cube_size_range_covers_small_and_large_cubes() -> None:
    assert CUBE_SIZES == list(range(MIN_CUBE_SIZE, MAX_CUBE_SIZE + 1))
    assert CUBE_SIZES[:4] == [2, 3, 4, 5]
    assert CUBE_SIZES[-1] == MAX_CUBE_SIZE


def test_piece_scaling_keeps_large_cubes_bounded() -> None:
    for size in (2, 3, 4, 5, 10, 50, 100):
        piece = piece_side_length_for_size(size)
        minimum, maximum = piece_side_length_limits(size)
        assert minimum <= piece <= maximum
        assert size * piece <= 300.0


def test_auxiliary_drawings_keep_a_constant_footprint() -> None:
    for size in (5, 10, 50, 100):
        piece = auxiliary_piece_side_length(size, footprint=60.0, maximum=15.0)
        assert size * piece == 60.0
