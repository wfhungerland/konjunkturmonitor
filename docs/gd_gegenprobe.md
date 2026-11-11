# Gegenprobe des Prognosedatensatzes der Gemeinschaftsdiagnose

Stand: 11.11.2026. Offen, Durchführung von Hand (etwa durch eine Praktikantin oder einen Praktikanten).

## Warum

Alle Werte im Datensatz `data/static/gd_prognosen.csv` wurden maschinell gelesen und maschinell nachgeprüft. Eine Gegenprobe durch einen Menschen fehlt noch. Sie zeigt, ob die Trefferquote der maschinellen Prüfung auch einem unabhängigen Blick standhält.

## Was zu tun ist

1. Die Prüfliste `gegenprobe.csv` liegt auf dem Server unter `/srv/daten/GD/datensatz/`. Jede Zeile nennt Gutachten, Größe, Prognosejahr, erfassten Wert, Datei, PDF-Seite, gedruckte Seite und Tabelle.
2. Die PDFs liegen mit denselben Dateinamen in der Dropbox im Ordner GD (Unterordner Scans, Gutachten, Anhangstabellen).
3. Für jede Zeile: PDF öffnen, zur PDF-Seite springen, die genannte Tabelle suchen und den Wert für Größe und Prognosejahr ablesen. Dabei den erfassten Wert erst nach dem eigenen Ablesen ansehen.
4. In die Spalten `gelesen`, `stimmt` (ja/nein) und `bemerkung` eintragen, was im PDF steht. Bei Unklarheit (unleserlich, mehrere passende Zahlen) „nein“ und eine kurze Bemerkung.
5. Die ausgefüllte Datei zurück auf den Server oder in die Dropbox legen und Bescheid geben.

## Hinweise

- Spannen stehen im Datensatz als Mitte, Brüche wie 2½ als 2.5, Millionen bei Arbeitslosen in Tausend. Der gedruckte Wortlaut steht in `wert_text`.
- Je Zeile etwa eine Minute.
- Das Ergebnis kommt als Eintrag in `data/static/korrekturen.yaml` und in den Methodentext der Abbildungen 96-101.
