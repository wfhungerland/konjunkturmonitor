"""Ticket (GitHub-Issue) bei Ausfällen des Datenabrufs.

Liest data/processed/run_status.json. Gibt es fehlgeschlagene oder veraltete Reihen, wird ein offenes Ticket
„Datenabruf: Ausfälle“ angelegt oder dessen Text aktualisiert; ist alles in Ordnung, wird ein offenes Ticket geschlossen.
Läuft im Workflow mit dem GitHub-CLI (gh) und dem Token des Laufs.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

TITLE = "Datenabruf: Ausfälle"
TITLE_JUMP = "Datenabruf: auffällige Werte"


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout.strip()


def body(run: dict) -> str | None:
    ser = run.get("series", [])
    bad = [s for s in ser if s.get("status") in ("failed", "skipped")]
    old = [s for s in ser if s.get("outdated")]
    if not bad and not old:
        return None
    lines = [f"Stand des Laufs: {run.get('finished_at', '')}", ""]
    if bad:
        lines += [f"**Fehlgeschlagen ({len(bad)}):**", ""] + [f"- `{s['series_id']}`: {s.get('message', '')[:200]}" for s in bad] + [""]
    if old:
        lines += [f"**Länger ohne neue Werte ({len(old)}):**", ""] + [f"- `{s['series_id']}`: letzte Periode {s.get('last', '')}" for s in old] + [""]
    lines += ["Die Seite zeigt bei betroffenen Abbildungen einen Hinweis und den zuletzt erfolgreich abgerufenen Stand.",
              "Dieses Ticket wird bei jedem Lauf aktualisiert und schließt sich, sobald alle Reihen wieder ankommen."]
    return "\n".join(lines)


def jumps(path: Path = Path("data/processed/observations.csv"), k: float = 8.0) -> list[str]:
    """Reihen, deren jüngste Veränderung mehr als k robuste Standardabweichungen von den bisherigen Veränderungen abweicht.
    Robust: Median der absoluten Abweichungen (MAD) × 1,4826. Fängt Einheitenwechsel, Basisumstellungen und Abruffehler."""
    import pandas as pd
    if not path.exists():
        return []
    obs = pd.read_csv(path, usecols=["series_id", "date", "value"], parse_dates=["date"])
    out = []
    for sid, g in obs.groupby("series_id"):
        g = g.sort_values("date")
        s = g["value"].dropna()
        if len(s) < 36 or g["date"].diff().dt.days.median() > 300:  # Jahreswerte schwanken zu wenig regelmäßig für diese Prüfung
            continue
        d = s.diff().dropna()
        hist, last = d.iloc[:-1], d.iloc[-1]
        mad = (hist - hist.median()).abs().median() * 1.4826
        if mad > 0 and abs(last - hist.median()) > k * mad and abs(last) > hist.abs().max():
            out.append(f"- `{sid}`: jüngste Veränderung {last:+.3g}, bisher höchstens ±{hist.abs().max():.3g}")
    return out


def sync(title: str, text: str | None, ok_comment: str) -> None:
    found = gh("issue", "list", "--state", "open", "--search", f'"{title}" in:title', "--json", "number", "--jq", ".[0].number")
    if text is None:
        if found:
            gh("issue", "close", found, "--comment", ok_comment)
        return
    if found:
        gh("issue", "edit", found, "--body", text)
    else:
        gh("issue", "create", "--title", title, "--body", text)


def main() -> None:
    run = json.loads(Path("data/processed/run_status.json").read_text(encoding="utf-8"))
    j = jumps()
    sync(TITLE_JUMP, ("Diese Reihen haben sich im letzten Lauf stärker verändert als je zuvor. Das kann echt sein (etwa ein Preisschock), "
                      "aber auch auf eine geänderte Einheit, eine neue Basis oder einen Abruffehler hindeuten. Bitte prüfen.\n\n" + "\n".join(j)) if j else None,
         "Keine auffälligen Werte mehr im letzten Lauf.")
    text = body(run)
    found = gh("issue", "list", "--state", "open", "--search", f'"{TITLE}" in:title', "--json", "number", "--jq", ".[0].number")
    if text is None:
        if found:
            gh("issue", "close", found, "--comment", "Alle Reihen wurden im letzten Lauf wieder erfolgreich abgerufen.")
        print("Keine Ausfälle.")
        return
    if found:
        gh("issue", "edit", found, "--body", text)
    else:
        gh("issue", "create", "--title", TITLE, "--body", text)
    print(text)


if __name__ == "__main__":
    main()
