"""Animation scheduling and solve replay state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from ..cube import Cube, Move, apply_moves, copy_cube


class Scheduler(Protocol):
    def after(self, delay_ms: int, callback: Callable[[], None]) -> str: ...

    def after_cancel(self, after_id: str) -> None: ...


class AnimationController:
    """Schedule one pending Tk callback at a time and allow cancellation."""

    def __init__(self, widget: Scheduler) -> None:
        self.widget = widget
        self._after_id: str | None = None

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> None:
        self.cancel()
        self._after_id = self.widget.after(delay_ms, self._run(callback))

    def _run(self, callback: Callable[[], None]) -> Callable[[], None]:
        def run() -> None:
            self._after_id = None
            callback()

        return run

    def cancel(self) -> None:
        if self._after_id is None:
            return
        try:
            self.widget.after_cancel(self._after_id)
        except Exception:
            pass
        self._after_id = None


def invert_move(move: Move) -> Move:
    if move.endswith("'"):
        return move[:-1]
    if move.endswith("2"):
        return move
    return move + "'"


@dataclass
class ReplayController:
    """Track the moves of a completed solve and the replay cursor."""

    active: bool = False
    moves: list[Move] = field(default_factory=list)
    pointer: int = 0

    def reset(self) -> None:
        self.active = False
        self.moves = []
        self.pointer = 0

    def start(self, moves: list[Move]) -> None:
        self.moves = list(moves)
        self.pointer = len(self.moves)
        self.active = True

    def previous_move(self) -> Move:
        if self.pointer <= 0:
            return ""
        self.pointer -= 1
        return invert_move(self.moves[self.pointer])

    def next_move(self) -> Move:
        if self.pointer >= len(self.moves):
            return ""
        move = self.moves[self.pointer]
        self.pointer += 1
        return move

    def jump_to_start(self, initial_cube: Cube) -> Cube:
        self.pointer = 0
        return copy_cube(initial_cube)

    def seek(self, index: int, initial_cube: Cube) -> Cube:
        self.pointer = min(max(0, index), len(self.moves))
        return apply_moves(copy_cube(initial_cube), self.moves[: self.pointer])

    def jump_to_end(self, current_cube: Cube) -> Cube:
        remaining_moves = self.moves[self.pointer :]
        self.pointer = len(self.moves)
        return apply_moves(current_cube, remaining_moves)
