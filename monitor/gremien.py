"""Satz „Heute rät …“ für Sachverständigenrat und Gemeinschaftsdiagnose, aus der jüngsten Empfehlung je Dauerfrage.

Die Empfehlungen stehen in data/static/<gremium>_positionen.json: je Frage (L Löhne, G Geld, F Finanzen, A Arbeitsmarkt)
und Jahr die Stufe s (-1, 0, +1, NA). Der Satz nennt die Empfehlungen des jüngsten Gutachtens und die Fragen ohne Empfehlung.
"""
from __future__ import annotations

import json
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "data" / "static"
ORDER = ["A", "F", "G", "L"]
DE = {
    ("A", "+1"): "den Arbeitsmarkt flexibler machen und Anreize zur Arbeit stärken", ("A", "-1"): "Schutz und Leistungen ausbauen",
    ("A", "0"): "Arbeitsmarkt und Sozialstaat lassen, wie sie sind",
    ("F", "+1"): "die Konjunktur mit dem Haushalt anschieben", ("F", "-1"): "sparen und das Defizit abbauen", ("F", "0"): "die Finanzpolitik neutral halten",
    ("G", "+1"): "die Geldpolitik lockern", ("G", "-1"): "die Geldpolitik straffen", ("G", "0"): "die Geldpolitik beibehalten",
    ("L", "+1"): "die Löhne kräftiger erhöhen", ("L", "-1"): "bei den Löhnen zurückhaltend sein",
    ("L", "0"): "die Löhne im Rahmen von Produktivität und Preisanstieg erhöhen",
}
EN = {
    ("A", "+1"): "make the labour market more flexible and strengthen incentives to work", ("A", "-1"): "expand protection and benefits",
    ("A", "0"): "leave the labour market and welfare state as they are",
    ("F", "+1"): "support the economy through the budget", ("F", "-1"): "save and cut the deficit", ("F", "0"): "keep fiscal policy neutral",
    ("G", "+1"): "loosen monetary policy", ("G", "-1"): "tighten monetary policy", ("G", "0"): "keep monetary policy unchanged",
    ("L", "+1"): "raise wages more strongly", ("L", "-1"): "show wage restraint", ("L", "0"): "raise wages in line with productivity and prices",
}
NONE_DE = {"A": "zum Arbeitsmarkt", "F": "zur Finanzpolitik", "G": "zur Geldpolitik", "L": "zu den Löhnen"}
NONE_EN = {"A": "the labour market", "F": "fiscal policy", "G": "monetary policy", "L": "wages"}
WHO = {"svr": ("rät der Sachverständigenrat", "Jahresgutachten", "the Council of Economic Experts advises", "annual report", "gibt der Sachverständigenrat", "the Council gives"),
       "gd": ("raten die Institute", "Herbstgutachten", "the institutes advise", "autumn report", "geben die Institute", "the institutes give")}


def _join(xs: list[str], und: str) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + f" {und} " + xs[-1]


def heute(attach: str, who: str, lang: str = "de") -> str:
    """Ein bis zwei Sätze zur jüngsten Empfehlung; leer, wenn die Datei fehlt."""
    try:
        d = json.loads((STATIC / attach).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    qs = [q for q in ORDER if isinstance(d.get(q), dict) and d[q]]
    if not qs:
        return ""
    year = max(max(d[q]) for q in qs)
    rec, none = [], []
    for q in qs:
        s = str((d[q].get(year) or {}).get("s", "NA"))
        phrase = (DE if lang == "de" else EN).get((q, s))
        (rec if phrase else none).append(phrase or (NONE_DE if lang == "de" else NONE_EN)[q])
    v_de, doc_de, v_en, doc_en, g_de, g_en = WHO[who]
    if lang == "de":
        out = f"Im {doc_de} {year} {v_de}: {'; '.join(rec)}." if rec else f"Im {doc_de} {year} {g_de} zu den vier Dauerfragen keine Empfehlung."
        if rec and none:
            out += f" Keine Empfehlung gibt es {_join(none, 'und')}."
    else:
        pos = "its" if who == "svr" else "their"
        out = f"In {pos} {doc_en} {year}, {v_en}: {'; '.join(rec)}." if rec else f"In {pos} {doc_en} {year}, {g_en} no recommendation on the four standing questions."
        if rec and none:
            out += f" There is no recommendation on {_join(none, 'or')}."
    return out
