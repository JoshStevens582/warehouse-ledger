from __future__ import annotations

from pathlib import Path

import pytest

from warehouse_ledger.spa import frontend_dist_dir, spa_file


def test_frontend_dist_dir_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "nope"
    monkeypatch.setenv("FRONTEND_DIST", str(missing))
    assert frontend_dist_dir() is None


def test_spa_file_serves_index_and_blocks_escape(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    (dist / "asset.js").write_text("1", encoding="utf-8")

    assert spa_file("", dist).name == "index.html"
    assert spa_file("asset.js", dist).name == "asset.js"
    assert spa_file("unknown/route", dist).name == "index.html"
    assert spa_file("../secret", dist).name == "index.html"
