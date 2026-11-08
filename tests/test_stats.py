from rubik.stats import (
    default_stats,
    format_seconds,
    load_stats,
    record_solve,
    save_stats,
    summarize,
)


def test_stats_defaults_and_summary() -> None:
    stats = default_stats()
    summary = summarize(stats, 3)

    assert summary["count"] == 0
    assert summary["best"] is None
    assert summary["average"] is None
    assert format_seconds(None) == "--"
    assert format_seconds(65) == "1:05"


def test_record_and_persist_stats(tmp_path) -> None:
    path = tmp_path / "stats.json"
    stats = default_stats()
    record_solve(stats, 3, 12.0, 20, path=path)
    record_solve(stats, 3, 8.0, 16, path=path)
    record_solve(stats, 2, 4.0, 8, path=path)

    loaded = load_stats(path)
    summary = summarize(loaded, 3)
    assert summary["count"] == 2
    assert summary["best"] == 8.0
    assert summary["average"] == 10.0
    assert summary["last_moves"] == [20.0, 16.0]
    assert summarize(loaded, 4)["count"] == 0


def test_stats_limits_history(tmp_path) -> None:
    stats = default_stats()
    for index in range(60):
        record_solve(stats, 3, index, index, path=tmp_path / "stats.json")

    assert len(stats["3"]["times"]) == 50
    assert stats["3"]["times"][0] == 10.0


def test_save_stats_ignores_unwritable_path(tmp_path) -> None:
    stats = default_stats()
    save_stats(stats, tmp_path / "missing" / "stats.json")
    assert stats == default_stats()
