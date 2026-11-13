"""Persistent per-cube-size statistics for self solves."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import CUBE_SIZES

STATS_PATH = Path.home() / ".rubiks_cube_solver_stats.json"
SUPPORTED_SIZES = tuple(CUBE_SIZES)
MAX_HISTORY = 50


def default_stats() -> dict[str, dict[str, list[float]]]:
    return {str(size): {"times": [], "moves": []} for size in SUPPORTED_SIZES}


def _normalise(data: Any) -> dict[str, dict[str, list[float]]]:
    stats = default_stats()
    if not isinstance(data, dict):
        return stats
    for size in SUPPORTED_SIZES:
        entry = data.get(str(size))
        if not isinstance(entry, dict):
            continue
        for key in ("times", "moves"):
            values = entry.get(key)
            if isinstance(values, list):
                stats[str(size)][key] = [
                    float(value) for value in values if isinstance(value, (int, float))
                ]
    return stats


def load_stats(path: Path | None = None) -> dict[str, dict[str, list[float]]]:
    stats_path = path or STATS_PATH
    try:
        return _normalise(json.loads(stats_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return default_stats()


def save_stats(stats: dict[str, dict[str, list[float]]], path: Path | None = None) -> None:
    stats_path = path or STATS_PATH
    try:
        stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    except OSError:
        pass


def record_solve(
    stats: dict[str, dict[str, list[float]]],
    size: int,
    seconds: float,
    moves: int,
    path: Path | None = None,
) -> dict[str, dict[str, list[float]]]:
    entry = stats.setdefault(str(size), {"times": [], "moves": []})
    entry.setdefault("times", []).append(float(seconds))
    entry.setdefault("moves", []).append(float(moves))
    entry["times"] = entry["times"][-MAX_HISTORY:]
    entry["moves"] = entry["moves"][-MAX_HISTORY:]
    save_stats(stats, path)
    return stats


def summarize(stats: dict[str, dict[str, list[float]]], size: int) -> dict[str, Any]:
    entry = stats.get(str(size), {"times": [], "moves": []})
    times = entry.get("times", [])
    moves = entry.get("moves", [])
    return {
        "count": len(times),
        "best": min(times) if times else None,
        "average": sum(times) / len(times) if times else None,
        "last_times": times[-3:],
        "last_moves": moves[-3:],
    }


def format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "--"
    total = max(0, int(seconds))
    return f"{total // 60}:{total % 60:02d}"
