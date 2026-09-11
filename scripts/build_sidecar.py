#!/usr/bin/env python3
"""Build the Hockey Intelligence server into a standalone sidecar binary.

Produces a single-file executable that is bundled into a Tauri desktop
installer as a resource (`sidecar/hockey-server`). In dev mode the Tauri
shell falls back to a system Python; with the bundled sidecar present the
Rust launcher prefers it.

Usage:
    python scripts/build_sidecar.py [--outdir src-tauri/sidecar]
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "scripts" / "sidecar_entry.py"
APP_STATIC = ROOT / "app" / "static"
MIGRATIONS = ROOT / "migrations"
ALEMBIC_INI = ROOT / "alembic.ini"


def _build() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outdir",
        type=Path,
        default=ROOT / "src-tauri" / "sidecar",
        help="Output directory (default: src-tauri/sidecar)",
    )
    args = parser.parse_args()

    outdir: Path = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    sep = os.pathsep  # : on POSIX, ; on Windows

    build_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "hockey-server",
        # Collect full packages so all transitive deps are bundled
        "--collect-all",
        "uvicorn",
        "--collect-all",
        "fastapi",
        "--collect-all",
        "starlette",
        "--collect-all",
        "sqlalchemy",
        "--collect-all",
        "pydantic",
        "--collect-all",
        "pydantic_settings",
        "--collect-submodules",
        "aiosqlite",
        # Data bundles: static assets, Alembic migrations + config
        f"--add-data={APP_STATIC}{sep}app/static",
        f"--add-data={MIGRATIONS}{sep}migrations",
        f"--add-data={ALEMBIC_INI}{sep}.",
        # Hidden imports that PyInstaller sometimes misses
        "--hidden-import=app.main",
        "--hidden-import=app.api",
        "--hidden-import=app.core.config",
        "--hidden-import=app.database.connection",
        "--hidden-import=app.data.seeder",
        "--hidden-import=app.models",
        "--hidden-import=app.services",
        "--distpath",
        str(outdir),
        "--workpath",
        str(ROOT / "src-tauri" / "build"),
        "--specpath",
        str(ROOT / "src-tauri" / "build"),
        str(ENTRY),
    ]

    print("Running:", " ".join(build_cmd))
    subprocess.run(build_cmd, check=True, cwd=str(ROOT))

    # PyInstaller names the output by --name. Tauri bundles the sidecar as a
    # resource named `hockey-server` (no extension) on every platform, so on
    # Windows we also copy the .exe to the extensionless name.
    if platform.system() == "Windows":
        src = outdir / "hockey-server.exe"
        target = outdir / "hockey-server"
        if src.exists() and not target.exists():
            shutil.copy2(src, target)
        produced = target
    else:
        produced = outdir / "hockey-server"

    if not produced.exists():
        print(f"ERROR: expected output not found at {produced}")
        sys.exit(1)

    size_mb = produced.stat().st_size / (1024 * 1024)
    print(f"Sidecar built: {produced}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    _build()
