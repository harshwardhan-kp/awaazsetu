#!/usr/bin/env python3
"""Deploy this isolated app without putting credentials in CLI arguments or archives."""

import subprocess, json, zipfile, os
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
GROUP = "rg-awaazsetu"
APP = "awaazsetu-hkp-2026"


def run(args):
    return subprocess.run(args, cwd=ROOT, check=True)


values = {k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}
values.update(
    DATABASE_URL="sqlite:////home/awaazsetu/awaazsetu.db",
    PUBLIC_BASE_URL=f"https://{APP}.azurewebsites.net",
    SCM_DO_BUILD_DURING_DEPLOYMENT="true",
    WEBSITES_PORT="8000",
    ALLOWED_ORIGINS=f"https://{APP}.azurewebsites.net,https://awaazsetu.vercel.app",
)
path = ROOT / "work/azure-settings.json"
path.parent.mkdir(exist_ok=True)
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(values, f)
try:
    run(
        [
            "az",
            "webapp",
            "config",
            "appsettings",
            "set",
            "-g",
            GROUP,
            "-n",
            APP,
            "--settings",
            "@" + str(path),
            "--output",
            "none",
        ]
    )
finally:
    path.unlink(missing_ok=True)
run(
    [
        "az",
        "webapp",
        "config",
        "set",
        "-g",
        GROUP,
        "-n",
        APP,
        "--startup-file",
        "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --no-access-log",
        "--output",
        "none",
    ]
)
run(
    [
        "az",
        "webapp",
        "update",
        "-g",
        GROUP,
        "-n",
        APP,
        "--https-only",
        "true",
        "--output",
        "none",
    ]
)
archive = ROOT / "work/deploy.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for directory in ["backend", "data", "frontend/dist"]:
        for p in (ROOT / directory).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, p.relative_to(ROOT))
    z.write(ROOT / "requirements.lock.txt", "requirements.txt")
run(
    [
        "az",
        "webapp",
        "deploy",
        "-g",
        GROUP,
        "-n",
        APP,
        "--src-path",
        str(archive),
        "--type",
        "zip",
        "--async",
        "true",
        "--output",
        "none",
    ]
)
print("Deployment submitted. Verify /api/health and full browser workflow separately.")
