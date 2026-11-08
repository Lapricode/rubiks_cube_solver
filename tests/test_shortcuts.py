from rubik.config import DEFAULT_SHORTCUTS
from rubik.shortcuts import load_shortcuts, save_shortcuts


def test_shortcuts_default_when_file_missing(tmp_path) -> None:
    assert load_shortcuts(tmp_path / "missing.json") == DEFAULT_SHORTCUTS


def test_shortcuts_round_trip_and_ignore_unknown(tmp_path) -> None:
    path = tmp_path / "shortcuts.json"
    save_shortcuts({"undo": "<Control-u>", "unknown": "<F9>"}, path)

    assert load_shortcuts(path) == {**DEFAULT_SHORTCUTS, "undo": "<Control-u>"}
