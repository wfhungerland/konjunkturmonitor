"""Wächter: prüft täglich, ob die veröffentlichte Seite erreichbar und aktuell ist, und meldet Probleme als GitHub-Issue.

Fängt Fälle ab, die der Datenlauf selbst nicht melden kann: Der Lauf startet nicht, die Veröffentlichung schlägt fehl
oder GitHub Pages liefert eine alte Fassung. Aktuell heißt: Stand höchstens drei Werktage alt.
Läuft im Workflow .github/workflows/waechter.yml mit dem GitHub-CLI (gh) und dem Token des Laufs.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from .alert import sync

TITLE = "Wächter: Seite veraltet oder nicht erreichbar"


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


def main() -> None:
    cfg = yaml.safe_load(Path("monitor.yaml").read_text(encoding="utf-8"))
    url = cfg["site"]["url"]
    text = check(url, datetime.now(timezone.utc).date())
    sync(TITLE, text, "Die Seite ist wieder erreichbar und aktuell.")
    print(text or "Seite erreichbar und aktuell.")


if __name__ == "__main__":
    main()
