"""Manifest der veröffentlichten Seite: Prüfsumme (SHA-256) jeder Datei, damit sich Veränderungen nachweisen lassen.

Nach dem Bau schreibt der Lauf site/manifest.json (Zeitpunkt, Code-Stand, Prüfsumme je Datei) und die Prüfsumme des Manifests
nach data/archive/manifest.sha256; der Workflow committet diese Datei. Damit steht im Git-Verlauf, welche Fassung der Seite
zu welchem Lauf gehört. Der Wächter (monitor/waechter.py) vergleicht täglich die Seite im Netz damit.

Selbst nachprüfen: manifest.json von der Seite laden, `sha256sum manifest.json` mit data/archive/manifest.sha256 im
Repository vergleichen, dann einzelne Dateien gegen die Einträge im Manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

NAME = "manifest.json"
ANCHOR = Path("data") / "archive" / "manifest.sha256"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(site: Path, root: Path = Path(".")) -> dict:
    files = {p.relative_to(site).as_posix(): sha256(p.read_bytes()) for p in sorted(site.rglob("*")) if p.is_file() and p.name != NAME}
    manifest = {"generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "commit": os.environ.get("GITHUB_SHA", ""), "n": len(files), "files": files}
    raw = (json.dumps(manifest, ensure_ascii=False, indent=0) + "\n").encode("utf-8")
    (site / NAME).write_bytes(raw)
    anchor = root / ANCHOR
    anchor.parent.mkdir(parents=True, exist_ok=True)
    anchor.write_text(f"{sha256(raw)}  {NAME}\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    m = write(Path(sys.argv[1] if len(sys.argv) > 1 else "site"))
    print(f"Manifest: {m['n']} Dateien, Stand {m['generated_at']}")
