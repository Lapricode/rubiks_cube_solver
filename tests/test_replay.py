from rubik.cube import apply_moves, is_solved, solved_cube
from rubik.ui.animation import AnimationController, ReplayController, invert_move


def test_invert_move() -> None:
    assert invert_move("R") == "R'"
    assert invert_move("R'") == "R"
    assert invert_move("R2") == "R2"


def test_replay_cursor_walks_forward_and_backward() -> None:
    replay = ReplayController()
    replay.start(["R", "U", "F'"])

    assert replay.active
    assert replay.pointer == 3
    assert replay.previous_move() == "F"
    assert replay.pointer == 2
    assert replay.next_move() == "F'"
    assert replay.pointer == 3
    assert replay.next_move() == ""
    assert replay.previous_move() == "F"
    assert replay.previous_move() == "U'"
    assert replay.previous_move() == "R'"
    assert replay.previous_move() == ""


def test_replay_jump_start_and_end() -> None:
    initial = apply_moves(solved_cube(), ["R", "U"])
    replay = ReplayController()
    replay.start(["U'", "R'"])

    at_start = replay.jump_to_start(initial)
    assert at_start == initial
    assert replay.pointer == 0
    assert not is_solved(at_start)

    solved = replay.jump_to_end(at_start)
    assert replay.pointer == 2
    assert is_solved(solved)
    assert is_solved(replay.jump_to_end(solved))


class FakeWidget:
    def __init__(self) -> None:
        self.pending: dict[str, object] = {}
        self.cancelled: list[str] = []
        self._next_id = 0

    def after(self, delay_ms: int, callback) -> str:
        self._next_id += 1
        after_id = f"after-{self._next_id}"
        self.pending[after_id] = callback
        return after_id

    def after_cancel(self, after_id: str) -> None:
        self.cancelled.append(after_id)
        self.pending.pop(after_id, None)


def test_animation_controller_cancels_pending_callback() -> None:
    widget = FakeWidget()
    animation = AnimationController(widget)
    called: list[str] = []

    animation.schedule(0, lambda: called.append("first"))
    first_id = animation._after_id
    animation.schedule(0, lambda: called.append("second"))

    assert first_id in widget.cancelled
    assert called == []

    callback = widget.pending[animation._after_id]
    callback()
    assert called == ["second"]
    assert animation._after_id is None


def test_replay_reset() -> None:
    replay = ReplayController()
    replay.start(["R"])
    replay.reset()

    assert not replay.active
    assert replay.moves == []
    assert replay.pointer == 0
