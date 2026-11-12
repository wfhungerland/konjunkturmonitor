# Null-Werte und nötige Raten für `proj_gap`

Stand: 12.11.2026. Auszug aus internen Arbeitsunterlagen zu Null-Werten (NWX, NWQ, NWJ), beschränkt auf das, was die Abbildung „BIP und Projektion der Bundesregierung“ (`proj_gap`, Kapitel Prognosen und Revisionen) braucht. Die Unterlagen selbst liegen nicht im Repository.

## Begriffe

Ein Null-Wert ist die gleichbleibende Rate je fehlender Periode, mit der ein Vergleich gerade Null ergibt. Mit Zielrate statt Null ergibt sich die „nötige Rate“ der Abbildung.

- NWX: nötige Rate des nächsten Monats gegenüber dem Vormonat, damit der Durchschnitt der letzten x Monate dem der x Monate davor gleicht.
- NWQ: gleiche Monatsrate für die fehlenden Monate eines Quartals, damit das Quartalsmittel dem Vorquartal gleicht.
- NWJ: gleiche Quartalsrate gegenüber dem Vorquartal für die fehlenden Quartale eines Jahres, damit das Jahresmittel dem Vorjahr gleicht.

Für `proj_gap` zählt NWJ, verallgemeinert auf eine Zielrate.

## NWJ mit Zielrate (richtige Form)

Bekannt sind die Quartalswerte q_1 … q_k des laufenden Jahres (k = 0 bis 3), q_0 ist das letzte Quartal des Vorjahres. J ist der Jahresdurchschnitt des Vorjahres, T die Zielrate. Gesucht ist g, die gleiche Rate ggü. Vorquartal für die n = 4 − k fehlenden Quartale:

    q_1 + … + q_k + q_k·[(1+g) + (1+g)² + … + (1+g)^n] = 4·J·(1+T)

Die linke Seite steigt in g streng, es gibt also genau eine Lösung mit g > −1. Geschlossene Formeln:

- k = 3: g = (4J(1+T) − q_1 − q_2 − q_3) / q_3 − 1
- k = 2: g = ½·√(4(4J(1+T) − q_1)/q_2 − 3) − 3/2, gültig nur bei positivem Wurzelterm
- k = 1 und k = 0: Gleichung dritten bzw. vierten Grades; numerisch lösen (Bisektion genügt), die Cardano-Formel aus den Unterlagen lohnt nicht.

## Fehler in den Unterlagen

1. NWJ Fall 0, 1 und 3 setzen das Niveau des letzten Quartals gleich J (etwa q_3(1+g) = J). Das trifft das Jahresende, nicht das Jahresmittel, und widerspricht der eigenen Definition. Auch die Beispielrechnung (152,55 auf 155,26 mit 0,883 %) zielt auf das Niveau im 4. Quartal.
2. NWJ Fall 2 schreibt J statt 4J auf die rechte Seite; die Ergebnisformel im Hauptteil (±√(J/q_2) − 1) passt nicht zur Herleitung im Anhang.
3. NWJ Fall 0 und 1 übernehmen wörtlich die Beispieltexte von NWQ.
4. NWX: Für x = 2 nennt der Text als Vorperiode m_(t−3) bis m_(t−4); richtig ist m_(t−2) und m_(t−1). Die Formeln NW2, NW3 und NW6 stimmen.

NWQ Fall 0 bis 2 und die Excel-Umsetzung (Fall nach Monat mod 3, Fall 0 über die reelle Lösung von x³ + 4x² + 6x + 3(1 − 3q/m_3) = 0) rechnen richtig.

## Abgleich mit der Rechnung in `monitor/build.py` (`_projection`)

Der Code rechnet anders als NWJ: Er sucht eine gleiche Rate ggü. Vorjahresquartal (unbereinigt) und gewichtet mit Vorjahresanteilen aus dem bereinigten Index. Das ist für das unbereinigte Jahresziel der Projektion der passende Ansatz. Drei Punkte bestimmen die Genauigkeit:

1. Rundung: Die Vorjahresraten von Eurostat kommen auf eine Nachkommastelle. Fehlt nur ein Quartal, summieren sich die Rundungsfehler der drei bekannten Quartale in der nötigen Rate auf bis zu 0,15 Pp. Exakt wird es mit dem unbereinigten Volumenindex (Eurostat namq_10_gdp, s_adj = NSA): nötige Rate = (4·(1+T)·Mittel des Vorjahres − Summe der bekannten Quartale) / Summe der fehlenden Vorjahresquartale − 1. Dann entfällt auch die Gewichtung aus dem bereinigten Index.
2. Schalter „ggü. Vorquartal“: Der Code setzt die unbereinigte nötige Rate auf das bereinigte Niveau des Vorjahresquartals. Das mischt bereinigt und unbereinigt; daher ändert sich die Quartalsrate von Quartal zu Quartal. Sauber ist NWJ auf dem bereinigten Index mit der kalenderbereinigten Jahresrate der Projektion als Ziel; ob die Projektion sie ausweist, ist je Runde zu prüfen. Dann gibt es eine einzige Rate für alle fehlenden Quartale.
3. Datenstand 12.11.2026 (2026: drei Quartale, Ziel Herbstprojektion 1,3 %): Der Code ergibt für das 4. Quartal 2,1 % ggü. Vorjahresquartal und 1,1 % ggü. Vorquartal. NWJ auf dem bereinigten Index mit Ziel 1,3 % ergibt 1,33 % ggü. Vorquartal; ohne Wachstum im 4. Quartal käme das bereinigte Jahr auf 0,96 %. Der Abstand zwischen 1,1 und 1,33 ist im Kern der Kalendereffekt.
