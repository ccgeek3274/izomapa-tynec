# výška mostovek z laseru DMP 1G (ČÚZK, CC BY 4.0): body třídy 6 nad osou mostu (spouštět po dmp_fetch.py z kořene repa)
# Pravidla v prep.py (lávka 1 m, silnice 1,3 m nad vodou, 5,2 m nad cestou) jsou jen odhad: lávky přes řeku leží skoro na hladině,
# mosty nad nábřežím se zvlní. Laser změří skutečnou výšku a prep.py ji použije místo odhadu tam, kde měření je.
# -> assets/mosty_vysky.json: [[lat, lon, výška m n. m.], ...] po 2 m podél os mostů, jen spolehlivá měření
import glob, json, os, sys
import numpy as np, laspy, shapely, pyarrow.parquet as pq
from pyproj import Transformer

KROK = 2.0         # m mezi vzorky podél osy
DOSAH = 1.2        # m od osy mostu
MIN_BODU = 4
MAX_ROZPTYL = 1.5  # p90 - p10: víc znamená, že se míchá mostovka s něčím jiným (zábradlí stačí, lampy a stromy ne)
T = Transformer.from_crs(4326, 5514, always_xy=True)
TI = Transformer.from_crs(5514, 4326, always_xy=True)


def casti_mostu(r):
    """úseky segmentu (0..1), které jsou most; silnice mají příznak v road_flags, tratě v rail_flags"""
    fl = [f for k in ('road_flags', 'rail_flags') for f in (r.get(k) or [])]
    return [(0.0, 1.0) if f.get('between') is None else tuple(map(float, f['between'])) for f in fl if 'is_bridge' in (f.get('values') or [])]


def osy():
    files = ['data_all/segment.parquet'] if os.path.exists('data_all/segment.parquet') else sorted(glob.glob('data*/segment.parquet'))
    seen, out = set(), []
    for f in files:
        for r in pq.read_table(f, columns=['id', 'geometry', 'road_flags', 'rail_flags']).to_pylist():
            if r['id'] in seen: continue
            seen.add(r['id'])
            parts = casti_mostu(r)
            if not parts: continue
            g = shapely.from_wkb(r['geometry'])
            gk = shapely.transform(g, lambda c: np.column_stack(T.transform(c[:, 0], c[:, 1])))
            for a, b in parts:
                l = shapely.ops.substring(gk, a, b, normalized=True)
                if l.length < 8: continue          # propustky (BRIDGE_MIN v prep.py)
                n = max(2, int(l.length / KROK) + 1)
                out.append(np.array([(p.x, p.y) for p in (l.interpolate(t, normalized=True) for t in np.linspace(0, 1, n))]))
    return out


if __name__ == '__main__':
    import shapely.ops
    O = osy()
    if not O: sys.exit('v datech nejsou mosty')
    S = np.concatenate(O)
    vys = {}
    for f in sorted(glob.glob('build/dmp/*.laz')):
        h = laspy.open(f).header
        m = (S[:, 0] >= h.mins[0] - 2) & (S[:, 0] <= h.maxs[0] + 2) & (S[:, 1] >= h.mins[1] - 2) & (S[:, 1] <= h.maxs[1] + 2)
        if not m.any(): continue
        l = laspy.read(f); c = np.array(l.classification) == 6
        X, Y, Z = np.array(l.x)[c], np.array(l.y)[c], np.array(l.z)[c]
        near = np.zeros(len(X), bool)                  # předvýběr bodů u mostů (mřížka po 4 m)
        cells = {(int(x // 4), int(y // 4)) for x, y in S[m]}
        cx, cy = (X // 4).astype(int), (Y // 4).astype(int)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                near |= np.fromiter(((a + dx, b + dy) in cells for a, b in zip(cx, cy)), bool, len(cx))
        X, Y, Z = X[near], Y[near], Z[near]
        for i in np.where(m)[0]:
            x, y = S[i]; k = np.hypot(X - x, Y - y) < DOSAH
            if k.sum() < MIN_BODU: continue
            z = Z[k]; p10, p50, p90 = np.percentile(z, [10, 50, 90])
            if p90 - p10 > MAX_ROZPTYL: continue
            vys[i] = float(p50)
    out = []
    for i, z in sorted(vys.items()):
        lon, lat = TI.transform(*S[i])
        out.append([round(lat, 7), round(lon, 7), round(z, 2)])
    json.dump(out, open('assets/mosty_vysky.json', 'w'))
    print('mostů', len(O), 'vzorků', len(S), 'změřeno', len(out))
