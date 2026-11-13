"""Wächter: prüft täglich, ob die veröffentlichte Seite erreichbar und aktuell ist, und meldet Probleme als GitHub-Issue.

Fängt Fälle ab, die der Datenlauf selbst nicht melden kann: Der Lauf startet nicht, die Veröffentlichung schlägt fehl
oder GitHub Pages liefert eine alte Fassung. Aktuell heißt: Stand höchstens drei Werktage alt.
Läuft im Workflow .github/workflows/waechter.yml mit dem GitHub-CLI (gh) und dem Token des Laufs.
"""
from __future__ import annotations

import json
import random
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from .alert import sync
from .manifest import ANCHOR, NAME, sha256

TITLE = "Wächter: Seite veraltet oder nicht erreichbar"
TITLE_MANIFEST = "Wächter: Seite weicht vom Manifest ab"
CORE = ["index.html", "en/index.html", "data.json", "plotly.min.js", "feed.xml", "impressum.html", "datenschutz.html", "korrekturen.html"]


def workdays_between(a: date, b: date) -> int:
    n, d = 0, a
    while d < b:
        d = date.fromordinal(d.toordinal() + 1)
        n += d.weekday() < 5
    return n


def check(url: str, today: date, max_workdays: int = 3) -> str | None:
    """Fehlertext oder None, wenn die Seite erreichbar und aktuell ist."""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/data.json", timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as exc:  # Netz, HTTP oder JSON
        return f"Die Seite {url} ist nicht erreichbar oder liefert keine gültigen Daten: {exc.__class__.__name__}: {exc}"
    gen = str(data.get("generated_at", ""))[:10]
    try:
        built = date.fromisoformat(gen)
    except ValueError:
        return f"Die Seite {url} nennt keinen gültigen Bauzeitpunkt ({gen!r})."
    lag = workdays_between(built, today)
    if lag > max_workdays:
        return (f"Die Seite {url} wurde zuletzt am {built:%d.%m.%Y} gebaut, vor {lag} Werktagen. "
                "Bitte den Workflow „Daten holen und Seite veröffentlichen“ prüfen (Actions).")
    return None


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def check_manifest(url: str, root: Path = Path("."), sample: int = 60, get=_get) -> str | None:
    """Vergleicht die Seite im Netz mit dem Manifest und das Manifest mit dem Stand im Repository (data/archive/manifest.sha256).
    Geprüft werden die Kernseiten und eine Zufallsstichprobe der übrigen Dateien. Fehlertext oder None."""
    base = url.rstrip("/") + "/"
    anchor = root / ANCHOR
    if not anchor.exists():
        return None  # vor dem ersten Lauf mit Manifest
    try:
        raw = get(base + NAME)
        files = json.loads(raw.decode("utf-8"))["files"]
    except Exception as exc:
        return f"Das Manifest {base}{NAME} fehlt oder ist nicht lesbar: {exc.__class__.__name__}: {exc}"
    if sha256(raw) != anchor.read_text(encoding="utf-8").split()[0]:
        return (f"Das Manifest der Seite {url} passt nicht zu `{ANCHOR.as_posix()}` im Repository. Die Seite im Netz stammt damit nicht "
                "aus dem letzten Lauf, der auf main festgehalten ist. Bitte unter Actions und Settings › Pages prüfen, wer zuletzt veröffentlicht hat.")
    rest = sorted(set(files) - set(CORE))
    todo = [f for f in CORE if f in files] + random.sample(rest, min(sample, len(rest)))
    bad = []
    for f in todo:
        try:
            ok = sha256(get(base + f)) == files[f]
        except Exception:
            ok = False
        if not ok:
            bad.append(f)
    if bad:
        return (f"{len(bad)} von {len(todo)} geprüften Dateien der Seite {url} weichen vom Manifest ab oder fehlen: "
                + ", ".join(f"`{f}`" for f in bad[:10]) + (" …" if len(bad) > 10 else "") + ". Bitte prüfen, wer zuletzt veröffentlicht hat.")
    return None


def main() -> None:
    cfg = yaml.safe_load(Path("monitor.yaml").read_text(encoding="utf-8"))
    url = cfg["site"]["url"]
    text = check(url, datetime.now(timezone.utc).date())
    sync(TITLE, text, "Die Seite ist wieder erreichbar und aktuell.")
    print(text or "Seite erreichbar und aktuell.")
    if text is None:
        diff = check_manifest(url)
        if diff:  # ein Lauf kann gerade zwischen Commit und Veröffentlichung stehen: einmal warten und erneut prüfen
            time.sleep(600)
            diff = check_manifest(url)
        sync(TITLE_MANIFEST, diff, "Die Seite stimmt wieder mit dem Manifest überein.")
        print(diff or "Seite stimmt mit dem Manifest überein.")


if __name__ == "__main__":
    main()
