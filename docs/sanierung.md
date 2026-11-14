# Sanierungsbedarf der öffentlichen Infrastruktur je Kreis

Ziel: ein Maß je Kreis, das den Sanierungsbedarf der öffentlichen Infrastruktur anzeigt und sich über Jahre fortschreiben lässt; Gegenstück zur Baukapazität (`docs/aufnahme.md`).

## Baustein Brücken der Bundesfernstraßen (Stand 14.11.2026)

Quelle: BASt-Brückenstatistik als CSV, Stand 01.03.2026, 52.625 Teilbauwerke mit Baujahr, Fläche, Traglastindex und Zustandsnote, Open-Data-Nutzungsbedingungen der BASt. Abruf und Auswertung: `python -m monitor.sanierung_bruecken <ordner> --ziel data/static`, nur Standardbibliothek. Ergebnis je Kreis: `data/static/sanierung_bruecken.csv`.

Lage: Die Statistik nennt keine Koordinaten. Die ersten vier Ziffern der Bauwerksnummer sind das Blatt der TK25 (Zeile, Spalte; Raster 6 mal 10 Bogenminuten ab 55°54' Nord, 5°50' Ost, geprüft an Karlsruhe-Nord 6916 und Starnberg 8034). Der Blattmittelpunkt wird dem Kreis zugeordnet; 510 Teilbauwerke liegen außerhalb (Grenzblätter, Sondernummern), 373 Kreise haben Brücken. Brücken nahe der Kreisgrenze können im Nachbarkreis landen (Blatt rund 11 mal 11 km).

Befund: 11,0 % der Brückenfläche haben heute die Note 3,0 oder schlechter. Am höchsten ist der Anteil in Trier-Saarburg (53 %), Trier (50 %), Tuttlingen (49 %), Freudenstadt (47 %) und Mayen-Koblenz (47 %), jeweils Kreise mit mindestens 2 ha Brückenfläche. Der Anteil der Fläche, die mindestens 60 Jahre alt ist, steigt von 10 % heute auf 33 % im Jahr 2035; in Mülheim an der Ruhr, Cochem-Zell, Krefeld und Bremerhaven auf über 90 %.

Fortschreibung (Markov-Kette): Eine frühere Ausgabe der Statistik liegt aus dem Internet Archive vor (abgerufen August 2025, Stand 01.03.2025; `tools/Brueckenarchiv abrufen.bat`, `monitor/bruecken_archiv.py`, lokal, weil die Cloud-Umgebung das Archiv nicht erreicht). Von 52.196 Teilbauwerken in beiden Ständen hat sich binnen eines Jahres bei 10,1 % die Note verschlechtert (im Mittel um 0,31), bei 5,6 % verbessert; 390 sind abgegangen (zu 42 % mit Note ab 3,0), 429 neu (zu 6 %). Daraus entstehen jährliche Übergangsmatrizen zwischen sechs Notenklassen je Altersgruppe (unter 30, 30 bis 49, ab 50 Jahre), flächengewichtet, in zwei Szenarien: „Trend“ mit allen Übergängen und Ersatzneubauten im heutigen Tempo, „ohne Erneuerung“ ohne Verbesserungen und Ersatz. Rücktest auf den Schätzdaten: 2025 11,1 %, vorhergesagt 2026 11,0 %, beobachtet 11,0 %.

| Fläche mit Note ab 3,0 | 2026 | 2030 | 2035 |
|---|---:|---:|---:|
| Trend (heutiges Erneuerungstempo) | 11,0 % | 10,8 % | 11,0 % |
| ohne Erneuerung | 11,0 % | 16,2 % | 23,4 % |

Lesart: Das heutige Tempo hält den Anteil schlechter Brückenfläche gerade stabil. Ohne Erneuerung verdoppelt er sich bis 2035. Die Differenz ist der Erneuerungsbedarf: bis 2035 rund 7,4 Mio. m² Brückenfläche, die ohne Eingriff auf Note 3,0 oder schlechter fiele. Je 1.000 Einwohner am höchsten in Passau, Koblenz, Trier-Saarburg und Ahrweiler (750 bis 790 m²), danach Lahn-Dill-Kreis und Siegen-Wittgenstein. Spalten je Kreis: `anteil_ab_3_0_2030_trend` bis `anteil_ab_3_0_2035_ohne_erneuerung`.

Test außerhalb der Schätzdaten: Die Archivfassung vom Januar 2026 (Stand 1. September 2025, nur Notenklassen) teilt das Jahr. Mit den Übergängen von März bis September 2025 sagt das Modell für März 2026 einen Anteil von 10,93 % voraus, beobachtet sind 10,98 % (März 2025: 11,08 %, September 2025: 11,01 %). Je Halbjahr wechseln 3,6 bzw. 4,6 % der Bauwerke die Notenklasse, 2,3 bzw. 2,9 % zum Schlechteren; beide Halbjahre verhalten sich ähnlich.

Grenzen: Die Übergänge stammen aus einem Jahr; Prüfungen finden alle drei bis sechs Jahre statt. Die Stände der Archivfassungen sind aus dem Veröffentlichungsrhythmus der BASt geschlossen (Daten zum 1. März und 1. September). Die Querschnittskurve (Spalten `flaeche_note_ab_3_0_2030_m2` und `_2035_m2`) unterschätzt die Alterung und ist überholt.

## Baustein Kommunalinvestitionen

Abruf aus der Regionaldatenbank nur mit Konto, auf dem Rechner: `tools/Kommunalinvestitionen abrufen.bat` (`monitor/kommunal_invest.py`). Tabellen 71717-Z-05 (2018 bis 2025, Auszahlungen aus Investitionstätigkeit der Gemeinden und Gemeindeverbände) und 71517-02-03-4 sowie 71517-04-02-4 (1995 bis 2014, Kassenstatistik je Kreis). Die Schnittstelle nimmt keine Basic-Anmeldung an; ein in der Cloud-Umgebung gespeichertes Zugangsdatum hilft deshalb nicht.

## Offen

Eisenbahnbrücken (StreckeDB, BKG), Alter der Siedlungsnetze (Zensus 2022), Abgleich mit TED-Ausschreibungen für Brücken- und Straßenerneuerung, Zusammenführung und Verhältnis zur Baukapazität.
