"""MHD podle jízdních řádů (GTFS, adresa v mesto.json mhd.gtfs) -> site/mhd.json

python mhd.py [--stahnout]   stáhne build/gtfs.zip (při --stahnout nebo když je starší než den) a převede ho:
  routes   [číslo linky, typ (0 tramvaj, 2 vlak, 3 autobus), celý název linky]
  shapes   trasy ve světových souřadnicích mapy [[x, y], ...] (zjednodušené na 1 m)
  services kalendář {id: [po..ne (7× 0/1), od, do, [přidané dny], [zrušené dny]]}
  trips    [linka, trasa, služba, začátek (s od půlnoci), [Δt, vzdálenost po trase (m)] × zastávky, cíl, [zastávka, Δt příjezdu] × zastávky,
            [Δt odjezdu podle jízdního řádu] × zastávky, číslo spoje (vlak: „Os 9032“), příznaky (1 bezbariérový, 2 kola)]
  heads, stops  názvy cílů a zastávek (indexy v trips)
Krajské GTFS (např. IDS JMK) se ořízne: jen autobusy a tramvaje, jejichž trasa vede územím mapy.
Prohlížeč z toho podle skutečného času dopočítá, kde je každé vozidlo. Bez mhd.gtfs skript nic neudělá.
"""
import csv, io, json, os, subprocess, sys, time, zipfile
import shapely
from nastroje.gtfs_casy import dopln_mezicasy
from geo import CHUNKS, HALF, MESTO, chunk_center, to_local

URL = (MESTO.get('mhd') or {}).get('gtfs')
if not URL: sys.exit('mesto.json nemá mhd.gtfs – MHD se vynechá')
Z = 'build/gtfs.zip'
if '--stahnout' in sys.argv or not os.path.exists(Z) or time.time() - os.path.getmtime(Z) > 86400:
    subprocess.run(['curl', '-sL', '-m', '120', '-o', Z + '.tmp', URL], check=True)
    zipfile.ZipFile(Z + '.tmp').testzip(); os.replace(Z + '.tmp', Z)
zf = zipfile.ZipFile(Z)
T = lambda n: (csv.DictReader(io.TextIOWrapper(zf.open(n + '.txt'), encoding='utf-8-sig')))
sec = lambda t: (lambda h, m, s: h * 3600 + m * 60 + s)(*map(int, t.split(':')))

AREA = shapely.union_all([shapely.box(x - HALF, y - HALF, x + HALF, y + HALF) for x, y in map(chunk_center, CHUNKS)])
# tramvaj 0 / 900–906, autobus 3 / 700–716, trolejbus 11 / 800 (kreslí se jako autobus); vlak 2, jen s volbou "vlak" a s tvary tras (po silnicích jezdit nemůže); lanovky prohlížeč nekreslí
KIND = lambda t: 0 if t == 0 or 900 <= t <= 906 else 3 if t in (3, 11, 800) or 700 <= t <= 716 else 2 if t == 2 and MESTO.get('vlak') and 'shapes.txt' in zf.namelist() else None
RT = {r['route_id']: r for r in T('routes') if KIND(int(r['route_type'] or 3)) is not None}
trips = [t for t in T('trips') if t['route_id'] in RT]
SN, SXY = {}, {}
for r in T('stops'):
    SN[r['stop_id']] = r['stop_name']
    if r.get('stop_lat'): SXY[r['stop_id']] = tuple(float(v) for v in to_local(float(r['stop_lon']), float(r['stop_lat'])))
shapes, SI, SLEN = [], {}, {}
if 'shapes.txt' in zf.namelist():
    used = {t['shape_id'] for t in trips}
    pts = {}
    for r in T('shapes'):
        if r['shape_id'] in used: pts.setdefault(r['shape_id'], []).append((int(r['shape_pt_sequence']), float(r['shape_pt_lon']), float(r['shape_pt_lat']), float(r['shape_dist_traveled'] or 0)))
    for k, v in pts.items():
        if len(v) < 2: continue
        v.sort(); x, y = to_local([p[1] for p in v], [p[2] for p in v])
        l = shapely.LineString(list(zip(x, y)))
        if not l.intersects(AREA): continue                      # trasa mimo mapu
        SI[k] = len(shapes); SLEN[k] = (l.length, v[-1][3] or 1.0)
        shapes.append([[round(a, 1), round(b, 1)] for a, b in shapely.simplify(l, 1.0).coords])
    trips = [t for t in trips if t['shape_id'] in SI]
TI = {t['trip_id'] for t in trips}
st = {}
for r in T('stop_times'):
    if r['trip_id'] not in TI: continue
    ta = r.get('arrival_time') or r.get('departure_time')
    td = r.get('departure_time') or ta
    st.setdefault(r['trip_id'], []).append((int(r['stop_sequence']), sec(ta) if ta else None, sec(td) if td else None, float(r.get('shape_dist_traveled') or 0), r['stop_id']))
st = {trip_id: dopln_mezicasy(rows) for trip_id, rows in st.items()}
if 'shapes.txt' not in zf.namelist():                      # GTFS bez tvarů tras (např. IDS JMK): trasa mezi zastávkami po silnicích z mapy
    import road_route
    near = AREA.buffer(300)
    trips = [t for t in trips if any(near.contains(shapely.Point(SXY[z[4]])) for z in st.get(t['trip_id'], []) if z[4] in SXY)]
    R = road_route.Graph('data_all/segment.parquet')
    syn = {}
    for t in trips:
        s = [z for z in st[t['trip_id']] if z[4] in SXY]
        key = tuple(z[4] for z in s)
        if key not in syn:
            line, dists = R.path([SXY[z] for z in key])
            syn[key] = (f'syn{len(shapes)}', dists)
            SI[syn[key][0]] = len(shapes); SLEN[syn[key][0]] = (dists[-1] or 1.0, dists[-1] or 1.0)
            shapes.append([[round(a, 1), round(b, 1)] for a, b in shapely.simplify(shapely.LineString(line), 1.0).coords])
        t['shape_id'], dists = syn[key]
        st[t['trip_id']] = [(q, a_, d_, dist, z) for (q, a_, d_, _, z), dist in zip(s, dists)]
    print('trasy dopočítané po silnicích:', len(shapes), 'úseků bez silnice:', R.fails)
TI = {t['trip_id'] for t in trips}; SV = {t['service_id'] for t in trips}
st = {k: [(q, a_, d_, dist, SN.get(z, '')) for q, a_, d_, dist, z in v] for k, v in st.items() if k in TI}
routes, RI = [], {}
for rid in dict.fromkeys(t['route_id'] for t in trips):
    RI[rid] = len(routes); routes.append([RT[rid]['route_short_name'], KIND(int(RT[rid]['route_type'] or 3)), RT[rid].get('route_long_name') or ''])
services = {}
for c in T('calendar'):
    if c['service_id'] not in SV: continue
    services[c['service_id']] = [[int(c[d]) for d in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')],
                                 int(c['start_date']), int(c['end_date']), [], []]
for c in T('calendar_dates'):
    if c['service_id'] not in SV: continue
    s = services.setdefault(c['service_id'], [[0] * 7, 0, 0, [], []])
    s[3 if c['exception_type'] == '1' else 4].append(int(c['date']))
names, NI = [], {}
def nid(n):
    if n not in NI: NI[n] = len(names); names.append(n)
    return NI[n]
out = []
for t in trips:
    if routes[RI[t['route_id']]][1] != 2 and len(routes[RI[t['route_id']]][0]) > 4: continue   # poptávková doprava apod. bez pravidelné trasy; vlaky mají dlouhá čísla
    s = st.get(t['trip_id'], [])
    if len(s) < 2 or t['shape_id'] not in SI: continue
    L, gl = SLEN[t['shape_id']]; k = L / gl                     # vzdálenost z jízdního řádu -> délka trasy v mapě
    t0 = s[0][1]; seq = []; zs = []; dep = []
    for j, (_, a, d, dist, nm) in enumerate(s):
        dep.append(d - t0)                                   # odjezd podle jízdního řádu (do lišty sledovaného vozidla)
        if 0 < j < len(s) - 1 and d == a:                    # jízdní řád je po minutách: v zastávce stát ~20 s kolem času odjezdu
            gap = min(a - s[j - 1][2], s[j + 1][1] - d)
            w = min(10, gap // 4)
            a, d = a - w, d + w
        seq += [a - t0, round(dist * k)]
        if d > a: seq += [d - t0, round(dist * k)]              # pobyt v zastávce
        zs += [nid(nm), a - t0]
    fl = (1 if t.get('wheelchair_accessible') == '1' else 0) | (2 if t.get('bikes_allowed') == '1' else 0)
    out.append([RI[t['route_id']], SI[t['shape_id']], t['service_id'], t0, seq, nid(t['trip_headsign'] or s[-1][4]), zs, dep, t.get('trip_short_name') or '', fl])
out.sort(key=lambda q: q[3])
json.dump({'routes': routes, 'shapes': shapes, 'services': services, 'trips': out, 'names': names,
           'feed': next(iter(T('feed_info')), {}).get('feed_version', '') if 'feed_info.txt' in zf.namelist() else time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(Z)))}, open('site/mhd.json', 'w', encoding='utf-8'), separators=(',', ':'), ensure_ascii=False)
print('linek', len(routes), 'tras', len(shapes), 'spojů', len(out), 'kB', os.path.getsize('site/mhd.json') // 1000)
