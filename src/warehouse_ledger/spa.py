"""Serve the Vite build from the API when FRONTEND_DIST points at a dist folder."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_DIST = "/app/frontend/dist"


def frontend_dist_dir() -> Path | None:
    raw = os.environ.get("FRONTEND_DIST", _DEFAULT_DIST).strip()
    if not raw:
        return None
    dist = Path(raw)
    if not dist.is_dir() or not (dist / "index.html").is_file():
        return None
    return dist


def spa_file(full_path: str, dist: Path) -> Path:
    """Pick a file under dist. Unknown paths fall back to index.html (React router)."""
    dist_root = dist.resolve()
    if not full_path or full_path.endswith("/"):
        return dist_root / "index.html"
    candidate = (dist_root / full_path).resolve()
    try:
        candidate.relative_to(dist_root)
    except ValueError:
        return dist_root / "index.html"
    if candidate.is_file():
        return candidate
    return dist_root / "index.html"
