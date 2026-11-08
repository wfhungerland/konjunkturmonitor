"""Satzprüfung: Platzhalter, Zeitraum, Vorzeichen und Wert."""
from monitor.satzpruefung import apply, check

C = {"chart": "x", "type": "line", "last_x": "2026-09-01", "series": [{"y": [1.0, 2.34]}]}


def test_ok():
    assert check(C, "Im September 2026 lag der Wert bei 2,3 %, 0,4 Pp höher als ein Jahr zuvor.") is None


def test_placeholder():
    assert check(C, "Im September 2026 lag der Wert bei nan %.") == "Platzhalter oder Rechenrest"


def test_future_period():
    assert "nach dem jüngsten Wert" in check(C, "Im Oktober 2026 lag der Wert bei 2,3 %.")
    assert check(dict(C, chart="forecast"), "Für das Jahr 2027 erwartet die Bundesregierung 1,1 %.") is None


def test_sign():
    assert check(C, "Im September 2026 stiegen die Preise um -0,3 % ggü. Vorjahresmonat.") == "Richtungswort passt nicht zum Vorzeichen"
    assert check(C, "Im September 2026 lag der Wert bei 2,3 %, -0,4 Pp höher als ein Jahr zuvor.") == "Richtungswort passt nicht zum Vorzeichen"
    assert check(C, "Im September 2026 stiegen die Preise um 0,3 % ggü. Vorjahresmonat, nach -0,1 % im Vormonat.") is None


def test_value():
    assert "entspricht keinem" in check(C, "Im September 2026 lag der Wert bei 5,0 %.")


def test_apply_drops_sentence():
    topics = [{"charts": [dict(C, no=1, texts=["Im September 2026 lag der Wert bei 2,3 %.", "Im September 2026 lag der Wert bei None."])]}]
    found = apply(topics)
    assert len(found) == 1 and topics[0]["charts"][0]["texts"] == ["Im September 2026 lag der Wert bei 2,3 %."]
