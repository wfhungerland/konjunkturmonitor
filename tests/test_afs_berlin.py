import pandas as pd

from monitor.afs_berlin import index_block


def _sheet():
    rows = [["8 Sondergliederungen"] + [None] * 13, [None] * 14,
            ["Jahr", "Jan.", "Febr.", "März", "April", "Mai", "Juni", "Juli", "August", "Sept.", "Okt.", "Nov.", "Dez.", "Durch- schnitt"],
            [None] * 14,
            [None, "Gesamtindex ohne Energie"] + [None] * 12, [None, "Indexstand"] + [None] * 12,
            [2025] + [110.0] * 12 + [110.0],
            [None, "Veränderung gegenüber Vorjahresmonat in %"] + [None] * 12,
            [2025] + [1.0] * 12 + [1.0],
            [None, "Energie"] + [None] * 12, [None, "Indexstand"] + [None] * 12,
            [None] * 14,
            [2024] + [150.0 + m for m in range(12)] + [155.0],
            [2026] + [160.0, 161.0, "…"] + ["…"] * 9 + ["…"],
            [2926] + [1.0] * 12 + [1.0],
            [None, "Veränderung gegenüber Vorjahresmonat in %"] + [None] * 12,
            [2025] + [3.0] * 12 + [3.0]]
    return pd.DataFrame(rows)


def test_index_block_takes_only_index_rows_of_named_block():
    s = index_block(_sheet(), "Energie")
    assert s[pd.Timestamp("2024-01-01")] == 150.0
    assert s[pd.Timestamp("2024-12-01")] == 161.0
    assert s[pd.Timestamp("2026-02-01")] == 161.0
    assert len(s) == 14  # 12 Monate 2024 + 2 Monate 2026; Tippfehlerjahr 2926 und Veränderungen nicht
    assert 110.0 not in s.values


def test_parse_h1_reads_berlin_and_germany(tmp_path):
    import io
    from monitor.afs_berlin import parse_h1
    rows = [["Arbeitskreis VGR der Länder", None, None], ["Bruttoinlandsprodukt, 1. Halbjahr 2026", None, None],
            ["Land/", "Veränderungsrate", None], ["Gebiet", "in jeweiligen Preisen", "preisbereinigt"],
            ["Bayern", 3.8, 1.0], ["Berlin", 3.6, 0.8999999999999999], ["Deutschland", 3.7, 0.9], ["mit Berlin", 3.8, 1.0]]
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, sheet_name="1.Hj2026", header=False, index=False)
    year, vals = parse_h1(buf.getvalue())
    assert year == 2026 and vals == {"de30": 0.9, "de": 0.9}
