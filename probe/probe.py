"""Einmalige Erkundung: PEGELONLINE-Stationen und DWD-Verzeichnisse (wird wieder entfernt)."""
import io, re, zipfile
import requests

S = requests.Session()
P = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"
D = "https://opendata.dwd.de/climate_environment/CDC/"

def hdr(t): print("\n" + "=" * 20, t, flush=True)

hdr("PEGELONLINE Stationen")
st = S.get(f"{P}/stations.json", params={"includeTimeseries": "true"}, timeout=60).json()
for s in st:
    n = s.get("shortname", "")
    if re.search(r"KAUB|K.LN|RUHRORT|MAGDEBURG|DRESDEN", n, re.I):
        ts = [t["shortname"] for t in s.get("timeseries", [])]
        print(n, "|", s.get("longname"), "|", s.get("uuid"), "|", s.get("water", {}).get("shortname"), "|", ts)
for name in ["KAUB", "KÖLN", "DUISBURG-RUHRORT", "MAGDEBURG-STROMBRÜCKE", "DRESDEN"]:
    r = S.get(f"{P}/stations/{name}/W/measurements.json", params={"start": "P31D"}, timeout=60)
    j = r.json() if r.ok else r.text[:200]
    print(name, r.status_code, (len(j), j[:2], j[-1:]) if isinstance(j, list) else j)
r = S.get(f"{P}/stations/KAUB/W.json", timeout=60); print("W.json", r.text[:400])

def ls(path):
    r = S.get(D + path, timeout=60)
    names = re.findall(r'href="([^"?/][^"]*)"', r.text)
    print(path, r.status_code, names[:60])
    return names

hdr("DWD regional_averages_DE/monthly")
ls("regional_averages_DE/")
sub = ls("regional_averages_DE/monthly/")
for d in sub:
    if d.endswith("/") and re.search(r"temp|precip|air", d):
        files = ls("regional_averages_DE/monthly/" + d)
        for f in files[:1] + files[-2:]:
            if f.endswith(".txt"):
                t = S.get(D + "regional_averages_DE/monthly/" + d + f, timeout=60).text
                print("---", d + f, "\n" + "\n".join(t.splitlines()[:4]), "\n...\n" + "\n".join(t.splitlines()[-2:]))

hdr("DWD derived_germany/techn/monthly/heating_degreedays")
ls("derived_germany/techn/monthly/")
h = ls("derived_germany/techn/monthly/heating_degreedays/")
for d in h:
    if d.endswith("/"):
        files = ls("derived_germany/techn/monthly/heating_degreedays/" + d)
        for f in files[:3]:
            url = D + "derived_germany/techn/monthly/heating_degreedays/" + d + f
            if f.endswith((".txt", ".csv")):
                t = S.get(url, timeout=60).text
                print("---", d + f, "\n" + "\n".join(t.splitlines()[:6]))
            elif f.endswith(".zip"):
                z = zipfile.ZipFile(io.BytesIO(S.get(url, timeout=120).content))
                print("--- ZIP", d + f, z.namelist()[:10])
                for n in z.namelist()[:2]:
                    print("\n".join(z.read(n).decode("latin-1").splitlines()[:6]))
