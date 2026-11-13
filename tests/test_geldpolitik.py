from datetime import date

from monitor.geldpolitik import _country_net, _edp_countries, _monthly_table


def test_monthly_table_carries_year():
    text = "Titel,,\n,,A,B\n2014,November,1,2\n,December,3,\"-9,418\"\n2015,January,5,6\n"
    rows = _monthly_table(text)
    assert [d for d, _ in rows] == [date(2014, 11, 1), date(2014, 12, 1), date(2015, 1, 1)]
    assert rows[1][1] == ["3", "-9,418"]


def test_country_net_reads_first_block_only():
    text = ("Breakdown,,\nNet purchases,,\n,Mar-20,Apr-20,Cumulative\nGermany,100,\"1,200\",1300\nItaly,50,60,110\nTotal,150,1260,1410\n"
            "In EUR millions,,\n,,\nWAM,,\n,Mar-20,Apr-20\nGermany,8.1,7.2\n")
    out = _country_net(text)
    assert out["Germany"] == {date(2020, 3, 1): 100.0, date(2020, 4, 1): 1200.0}
    assert set(out) == {"Germany", "Italy"}


def test_edp_countries_between_headings():
    page = ("<h2>Overview of ongoing excessive deficit procedures</h2><a>France</a><a>Italy</a><a>Romania</a>"
            "<h2>Overview of closed excessive deficit procedures</h2><a>Germany</a><a>The Netherlands</a>")
    assert _edp_countries(page) == ["FR", "IT"]
