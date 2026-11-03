"""Einmalig: Ländergrenzen VG2500 (BKG, Datenlizenz Deutschland 2.0) holen, vereinfachen und ins Log schreiben."""
import json, requests, sys
from shapely.geometry import shape, mapping

URLS = [
    "https://sgx.geodatenzentrum.de/wfs_vg2500?service=WFS&version=2.0.0&request=GetFeature&typeNames=vg2500:vg2500_lan&outputFormat=application/json&srsName=EPSG:4326",
    "https://sgx.geodatenzentrum.de/wfs_vg2500?service=WFS&version=1.1.0&request=GetFeature&typeName=vg2500:vg2500_lan&outputFormat=application/json&srsName=EPSG:4326",
]
gj = None
for u in URLS:
    r = requests.get(u, timeout=120)
    print(u, r.status_code, r.headers.get("content-type"), r.text[:200].replace("\n", " "))
    if r.ok and r.text.lstrip().startswith("{"):
        gj = r.json(); break
if gj is None:
    r = requests.get("https://sgx.geodatenzentrum.de/wfs_vg2500?service=WFS&request=GetCapabilities", timeout=60)
    print(r.text[:3000]); sys.exit(0)
print("Attribute:", gj["features"][0]["properties"])
out = []
for f in gj["features"]:
    p = f["properties"]
    if str(p.get("gf", 4)) != "4" and len(gj["features"]) > 16:
        continue
    g = shape(f["geometry"]).simplify(0.008, preserve_topology=True)
    def rnd(c):
        if isinstance(c[0], (float, int)):
            return [round(c[0], 3), round(c[1], 3)]
        return [rnd(x) for x in c]
    m = mapping(g)
    out.append({"code": str(p.get("ars") or p.get("ags") or p.get("rs"))[:2], "name": p.get("gen"), "type": m["type"], "coordinates": rnd(m["coordinates"])})
s = json.dumps(out, separators=(",", ":"))
print("LEN", len(s), "N", len(out))
for i in range(0, len(s), 4000):
    print("GJ:" + s[i:i + 4000])
