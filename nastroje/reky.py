# řeky pro vodáky v prohlížeči: osy waterway=river z OpenStreetMap (Overpass, ODbL), ve směru toku (OSM kreslí řeky po proudu)
# Kusy jedné řeky se spojí (linemerge se směrem) a vezme se nejdelší souvislý tah; krátké řeky (< MIN_DELKA) se vynechají.
# -> assets/reky.json: [{"nazev": "Sázava", "body": [[lat, lon], ...]}]   overlay.py je ořízne na mapu a dá do overlay.json (rivers)
# spouštět z kořene repa: python nastroje/reky.py
import json, sys; sys.path.insert(0, '.'); sys.path.insert(0, 'nastroje')
import shapely
from shapely.geometry import LineString
import geo
from hriste import dotaz

MIN_DELKA = 1500          # m v mapě
x0, y0, x1, y1 = geo.extent(geo.MARGIN + 500)
(lo0, lo1), (la0, la1) = geo.to_lonlat([x0, x1], [y0, y1])
E = dotaz(f'[out:json][timeout:120];way["waterway"="river"]({la0:.5f},{lo0:.5f},{la1:.5f},{lo1:.5f});out tags geom;')
po_nazvu = {}
for e in E:
    if len(e.get('geometry') or []) < 2: continue
    xs, ys = geo.to_local([q['lon'] for q in e['geometry']], [q['lat'] for q in e['geometry']])
    po_nazvu.setdefault(e['tags'].get('name') or f'w{e["id"]}', []).append(LineString(zip(xs, ys)))
out = []
for n, ls in po_nazvu.items():
    g = shapely.line_merge(shapely.MultiLineString(ls), directed=True)
    best = max(list(g.geoms) if hasattr(g, 'geoms') else [g], key=lambda q: q.length)
    if shapely.clip_by_rect(best, *geo.extent(0)).length < MIN_DELKA: continue
    lo, la = geo.to_lonlat(*map(list, best.xy))
    out.append({'nazev': n, 'body': [[round(float(a), 7), round(float(b), 7)] for a, b in zip(la, lo)]})
    print(n, round(best.length), 'm')
json.dump(out, open('assets/reky.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('řek', len(out))
