"""Frozen-server entrypoint for the Hockey Intelligence desktop sidecar.

In a PyInstaller onefile bundle this provisions a fresh database on first
launch (schema + authoritative historical results) inside a per-user data
directory, then serves the FastAPI app with uvicorn.

Frozen layout (inside _MEIPASS):
    app/              FastAPI package (static included)
    migrations/       Alembic migration tree
    alembic.ini       Alembic config (script_location = migrations)
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("hockey-intelligence-sidecar")

PORT = int(os.environ.get("HI_PORT", "8000"))


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _data_dir() -> Path:
    """Return the persistent per-user data directory."""
    if override := os.environ.get("HI_DATA_DIR"):
        p = Path(override).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    p = base / "HockeyIntelligence"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _bundle_root() -> Path:
    """Return the PyInstaller extraction root, or the project root in dev."""
    if getattr(sys, "frozen", False):  # pragma: no cover
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# First-run provisioning
# ---------------------------------------------------------------------------

_SEASON_ROWS = [
    (start * 10000 + (start + 1), f"{start}-{str(start + 1)[2:]}", idx + 1)
    for idx, start in enumerate(range(1917, 2027))
]


def _provision_database(db_path: Path, bundle_root: Path) -> None:
    """Create the database from bundled Alembic migrations and seed seasons."""
    log.info("Provisioning fresh database at %s ...", db_path)

    # --- run Alembic upgrade head (schema + champions + playoff_series) ----
    from alembic import command
    from alembic.config import Config

    ini = bundle_root / "alembic.ini"
    if ini.exists():
        cfg = Config(str(ini))
        cfg.attributes["configure_args"] = {}  # prevent interactive prompts
        command.upgrade(cfg, "head")
    else:
        log.warning("alembic.ini not found at %s; skipping migration provisioning", ini)

    # --- seed 110 seasons --------------------------------------------------
    try:
        con = sqlite3.connect(str(db_path))
        con.executemany(
            "INSERT OR IGNORE INTO seasons (id, formatted_id, season_ordinal) VALUES (?, ?, ?)",
            _SEASON_ROWS,
        )
        con.commit()
        con.close()
        log.info("Seeded 110 seasons into %s", db_path)
    except Exception:
        log.exception("Failed to seed seasons")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    data_dir = _data_dir()
    bundle_root = _bundle_root()
    db_path = data_dir / "hockey_intelligence.db"

    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"

    if not db_path.exists():
        try:
            _provision_database(db_path, bundle_root)
        except Exception:
            log.exception("Database provisioning failed; starting with an empty schema")
            # Tables still exist from init_db; proceed anyway.

    log.info("Starting uvicorn on 127.0.0.1:%d (data dir: %s)", PORT, data_dir)

    import uvicorn

    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info", access_log=True)


if __name__ == "__main__":
    main()
