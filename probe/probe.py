"""Einmalige Erkundung: DWD-Heizgradtage (wird wieder entfernt)."""
import io, re, zipfile
import requests

S = requests.Session()
D = "https://opendata.dwd.de/climate_environment/CDC/derived_germany/techn/monthly/heating_degreedays/hdd_3807/"

def ls(path):
    r = S.get(D + path, timeout=60)
    names = re.findall(r'href="([^"?/][^"]*)"', r.text)
    print(path, r.status_code, len(names), names[:8], "...", names[-8:], flush=True)
    return names

def show(url, n=20):
    b = S.get(url, timeout=120).content
    if url.endswith(".zip"):
        z = zipfile.ZipFile(io.BytesIO(b)); print("ZIP", url, z.namelist()[:10])
        for m in z.namelist()[:2]:
            t = z.read(m).decode("latin-1"); L = t.splitlines()
            print("---", m, len(L)); print("\n".join(L[:n])); print("...", [l for l in L if re.search("deutschland|germany", l, re.I)][:5])
    else:
        t = b.decode("latin-1"); L = t.splitlines()
        print("---", url, len(L)); print("\n".join(L[:n])); print("...", [l for l in L if re.search("deutschland|germany", l, re.I)][:5])

for sub in ["", "recent/", "historical/"]:
    names = ls(sub)
    files = [n for n in names if not n.endswith("/") and not n.startswith("..")]
    for f in files[:1] + files[-1:]:
        show(D + sub + f)
