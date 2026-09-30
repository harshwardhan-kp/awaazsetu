#!/usr/bin/env python3
import sys, sqlite3, os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import settings, ROOT

if not settings.database_url.startswith("sqlite:///"):
    raise SystemExit("Use PostgreSQL pg_dump for this configured database.")
source = Path(settings.database_url.removeprefix("sqlite:///")).resolve()
if not source.exists():
    raise SystemExit("Database does not exist yet.")
folder = ROOT / "work/backups"
folder.mkdir(parents=True, exist_ok=True)
folder.chmod(0o700)
target = folder / (
    "awaazsetu-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".db"
)
with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
target.chmod(0o600)
print(
    "Private backup created in work/backups/. Keep encryption/hash keys with secure backups."
)
