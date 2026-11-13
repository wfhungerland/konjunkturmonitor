# Null-Werte und nötige Raten für `proj_gap`

Herleitung der Rechnung für die Abbildung „BIP und Projektion der Bundesregierung“ (`proj_gap`, Kapitel Prognosen und Revisionen).

## Begriffe

Ein Null-Wert ist die gleichbleibende Rate je fehlender Periode, mit der ein Vergleich gerade Null ergibt. Mit Zielrate statt Null ergibt sich die „nötige Rate“ der Abbildung.

- NWX: nötige Rate des nächsten Monats gegenüber dem Vormonat, damit der Durchschnitt der letzten x Monate dem der x Monate davor gleicht.
- NWQ: gleiche Monatsrate für die fehlenden Monate eines Quartals, damit das Quartalsmittel dem Vorquartal gleicht.
- NWJ: gleiche Quartalsrate gegenüber dem Vorquartal für die fehlenden Quartale eines Jahres, damit das Jahresmittel dem Vorjahr gleicht.

Für `proj_gap` zählt NWJ, verallgemeinert auf eine Zielrate.

## NWJ mit Zielrate

Bekannt sind die Quartalswerte q_1 … q_k des laufenden Jahres (k = 0 bis 3), q_0 ist das letzte Quartal des Vorjahres. J ist der Jahresdurchschnitt des Vorjahres, T die Zielrate. Gesucht ist g, die gleiche Rate ggü. Vorquartal für die n = 4 − k fehlenden Quartale:

    q_1 + … + q_k + q_k·[(1+g) + (1+g)² + … + (1+g)^n] = 4·J·(1+T)

Die linke Seite steigt in g streng, es gibt also genau eine Lösung mit g > −1. Geschlossene Formeln:

- k = 3: g = (4J(1+T) − q_1 − q_2 − q_3) / q_3 − 1
- k = 2: g = ½·√(4(4J(1+T) − q_1)/q_2 − 3) − 3/2, gültig nur bei positivem Wurzelterm
- k = 1 und k = 0: Gleichung dritten bzw. vierten Grades; der Monitor löst sie numerisch (Bisektion).

## Umsetzung in `monitor/build.py` (`_projection`)

1. Jahreswert = Summe der vier Quartale (Verkettung mit annual overlap). Probe: Die Summe der unbereinigten Quartale ergibt für 2025 die amtliche Jahresrate von 0,2 %.
2. Unbereinigt: Die fehlenden Quartale müssen zusammen S = (1 + Z) × Summe des Vorjahres − Summe der bekannten Quartale erreichen (unbereinigter Volumenindex `de_gdp_index_nsa`, Z = Jahresrate der Projektion). Verteilt wird S mit gleicher Rate ggü. Vorjahresquartal.
3. Bereinigt (Schalter „ggü. Vorquartal“): NWJ mit Zielrate auf dem saison- und kalenderbereinigten Index, Ziel ist die kalenderbereinigte Jahresrate der Projektion (`values_ka` in `data/static/prognosen.yaml`). Fehlt sie, entfällt der Schalter; bereinigte Werte und unbereinigtes Ziel werden nicht gemischt.
4. Beispiel, Datenstand 12.11.2026 (Herbstprojektion 2026: 1,3 %, kalenderbereinigt 1,0 %): nötig im 4. Quartal 2,1 % ggü. Vorjahresquartal und 0,1 % ggü. Vorquartal.
5. Probe: Die Jahresverlaufsrate der Herbstprojektion 2026 (1,2 %, 4. Quartal ggü. Vorjahresquartal, bereinigt) setzt für das 4. Quartal 2026 ein Wachstum von gut 0,2 % ggü. Vorquartal voraus. NWJ mit der gerundeten Zielrate von 1,0 % ergibt 0,1 %; der Unterschied liegt im Rundungsspielraum von Punkt 6.
6. Die Zielraten haben eine Nachkommastelle. Fehlt ein Quartal, bewegt das die nötige Rate um rund ±0,2 Prozentpunkte.
