# Sanierungsbedarf der öffentlichen Infrastruktur je Kreis

Ziel: ein Maß je Kreis, das den Sanierungsbedarf der öffentlichen Infrastruktur anzeigt und sich über Jahre fortschreiben lässt; Gegenstück zur Baukapazität (`docs/aufnahme.md`).

## Baustein Brücken der Bundesfernstraßen (Stand 14.11.2026)

Quelle: BASt-Brückenstatistik als CSV, Stand 01.03.2026, 52.625 Teilbauwerke mit Baujahr, Fläche, Traglastindex und Zustandsnote, Open-Data-Nutzungsbedingungen der BASt. Abruf und Auswertung: `python -m monitor.sanierung_bruecken <ordner> --ziel data/static`, nur Standardbibliothek. Ergebnis je Kreis: `data/static/sanierung_bruecken.csv`.

Lage: Die Statistik nennt keine Koordinaten. Die ersten vier Ziffern der Bauwerksnummer sind das Blatt der TK25 (Zeile, Spalte; Raster 6 mal 10 Bogenminuten ab 55°54' Nord, 5°50' Ost, geprüft an Karlsruhe-Nord 6916 und Starnberg 8034). Der Blattmittelpunkt wird dem Kreis zugeordnet; 510 Teilbauwerke liegen außerhalb (Grenzblätter, Sondernummern), 373 Kreise haben Brücken. Brücken nahe der Kreisgrenze können im Nachbarkreis landen (Blatt rund 11 mal 11 km).

Befund: 11,0 % der Brückenfläche haben heute die Note 3,0 oder schlechter. Am höchsten ist der Anteil in Trier-Saarburg (53 %), Trier (50 %), Tuttlingen (49 %), Freudenstadt (47 %) und Mayen-Koblenz (47 %), jeweils Kreise mit mindestens 2 ha Brückenfläche. Der Anteil der Fläche, die mindestens 60 Jahre alt ist, steigt von 10 % heute auf 33 % im Jahr 2035; in Mülheim an der Ruhr, Cochem-Zell, Krefeld und Bremerhaven auf über 90 %.

Fortschreibung: Die Note je Brücke mit einer Alterungskurve aus dem Querschnitt fortzuschreiben, unterschätzt die Alterung stark (im Mittel steigt die Note nur um rund 0,01 je Jahr, weil schlechte alte Brücken schon ersetzt sind): 11,0 % heute, 11,7 % im Jahr 2035 ohne Erneuerung. Bis eine zweite Ausgabe der Statistik vorliegt, mit der sich die Veränderung je Brücke messen lässt, ist die Altersgröße die robustere Prognose. Ältere Ausgaben bietet die BASt nicht zum Abruf an (die Versionsnummern der Datei liefern denselben Stand).

## Baustein Kommunalinvestitionen

Abruf aus der Regionaldatenbank nur mit Konto, auf dem Rechner: `tools/Kommunalinvestitionen abrufen.bat` (`monitor/kommunal_invest.py`). Tabellen 71717-Z-05 (2018 bis 2025, Auszahlungen aus Investitionstätigkeit der Gemeinden und Gemeindeverbände) und 71517-02-03-4 sowie 71517-04-02-4 (1995 bis 2014, Kassenstatistik je Kreis). Die Schnittstelle nimmt keine Basic-Anmeldung an; ein in der Cloud-Umgebung gespeichertes Zugangsdatum hilft deshalb nicht.

## Offen

Eisenbahnbrücken (StreckeDB, BKG), Alter der Siedlungsnetze (Zensus 2022), Abgleich mit TED-Ausschreibungen für Brücken- und Straßenerneuerung, Zusammenführung und Verhältnis zur Baukapazität.
