# zastávky autobusů a vlaků pro scénu: nástupiště z jízdních řádů (GTFS z mesto.json mhd.gtfs, staží mhd.py do build/gtfs.zip)
# a železniční stanice, zastávky a nástupiště z OpenStreetMap (Overpass, ODbL).
# Overture má autobusové zastávky jen zčásti a nástupiště vlaků skoro vůbec; GTFS má každé nástupiště zvlášť (obě strany silnice).
# -> assets/zastavky.json: {"bus": [[lat, lon, název], ...],
#                           "vlak": [{"nazev", "lat", "lon", "body": [[lat, lon], ...], "nastupiste": [[[lat, lon], ...], ...]}]}
#    body = nástupiště stanice z GTFS (strana koleje), nastupiste = obrysy/osy railway=platform z OSM (když chybí, prep.py je dokreslí)
# spouštět z kořene repa: python nastroje/zastavky.py   (po mhd.py, potřebuje build/gtfs.zip)
import csv, io, json, math, os, sys, zipfile; sys.path.insert(0, '.'); sys.path.insert(0, 'nastroje')
import geo
from hriste import dotaz

x0, y0, x1, y1 = geo.extent(geo.MARGIN + 50)
(lo0, lo1), (la0, la1) = geo.to_lonlat([x0, x1], [y0, y1])
inside = lambda lat, lon: lo0 <= lon <= lo1 and la0 <= lat <= la1
bb = f'{la0:.5f},{lo0:.5f},{la1:.5f},{lo1:.5f}'
E = dotaz(f'[out:json][timeout:120];(node["railway"~"^(station|halt)$"]({bb});way["railway"="platform"]({bb});'
          f'way["public_transport"="platform"]["train"="yes"]({bb}););out tags geom;')
dist = lambda a, b: math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))
stanice = [{'nazev': e['tags'].get('name', ''), 'lat': e['lat'], 'lon': e['lon'], 'body': [], 'nastupiste': []}
           for e in E if e['type'] == 'node' and e['tags'].get('railway') in ('station', 'halt')]
for e in E:
    if e['type'] != 'way' or not e.get('geometry'): continue
    g = [[round(q['lat'], 7), round(q['lon'], 7)] for q in e['geometry']]
    c = (sum(q[0] for q in g) / len(g), sum(q[1] for q in g) / len(g))
    s = min(stanice, key=lambda s: dist(c, (s['lat'], s['lon'])), default=None)
    if s and dist(c, (s['lat'], s['lon'])) < 250: s['nastupiste'].append(g)

bus = []
if os.path.exists('build/gtfs.zip'):
    for r in csv.DictReader(io.TextIOWrapper(zipfile.ZipFile('build/gtfs.zip').open('stops.txt'), 'utf-8-sig')):
        if r.get('location_type', '0') not in ('0', '') or not r.get('stop_lat'): continue
        lat, lon, n = float(r['stop_lat']), float(r['stop_lon']), r['stop_name']
        if not inside(lat, lon) or n.startswith('vl. v km'): continue          # technické body tratě
        # nástupiště vlaku: stejný název jako stanice v OSM a do 400 m od ní
        s = next((s for s in stanice if s['nazev'] == n and dist((lat, lon), (s['lat'], s['lon'])) < 400), None)
        if s: s['body'].append([round(lat, 7), round(lon, 7)])
        else: bus.append([round(lat, 7), round(lon, 7), n])
else:
    print('chybí build/gtfs.zip (python mhd.py --stahnout), autobusové zastávky zůstanou z Overture')
json.dump({'bus': bus, 'vlak': stanice}, open('assets/zastavky.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('autobusových nástupišť', len(bus), 'stanic', len(stanice), 'z toho bez nástupiště v OSM', sum(not s['nastupiste'] for s in stanice))
