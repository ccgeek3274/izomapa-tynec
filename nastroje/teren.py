# terén celé mapy z laseru ČÚZK (CC BY 4.0): DMR 5G (body reliéfu) + body terénu (třída 2) z DMP 1G, když jsou stažené
# Zdrojový terén (Terrarium, ~10 m/px) se u řek a náspů mýlí o metry: podjezdy, hřiště a nábřeží pak vycházejí špatně.
# -> build/teren_laser.npz: mřížka 5 m v lokálních souřadnicích čtverce (0, 0), uzly na násobcích 5 m (shodné s mřížkou
#    v prep.py), výška = průměr laserových bodů v buňce; místa bez bodů (voda, budovy) dopočítaná z okolí.
# python nastroje/teren.py   (z kořene repa; listy DMR 5G se stáhnou do build/dmr/, ~3 MB na list)
import glob, os, re, subprocess, sys
import numpy as np, laspy, shapely
from pyproj import Transformer
sys.path.insert(0, '.')
import geo

STEP = 5.0
OKRAJ = geo.MARGIN + 30 * STEP          # pás kolem mapy (mřížka v prep.py sahá MARGIN + ~20 kroků za čtverec)
OUT = 'build/teren_laser.npz'
TI = Transformer.from_crs(5514, 4326, always_xy=True)
T = Transformer.from_crs(4326, 5514, always_xy=True)


def listy():
    """listy DMR 5G, které zasahují do mapy (i s okrajem)"""
    os.makedirs('build/dmr', exist_ok=True)
    a = 'build/dmr/atom.xml'
    if not os.path.exists(a):
        subprocess.run(['curl', '-sL', '-m', '300', '-o', a, 'https://atom.cuzk.gov.cz/DMR5G-SJTSK/DMR5G-SJTSK.xml'], check=True)
    lon0, lon1, lat0, lat1 = geo.bbox_lonlat(OKRAJ)
    mapa = shapely.box(lon0, lat0, lon1, lat1)
    out = []
    for e in open(a, encoding='utf8').read().split('<entry>')[1:]:
        p = re.search(r'<georss:polygon>(.*?)<', e); k = re.search(r'DMR5G-SJTSK_([A-Z0-9]+)\.xml', e)
        if not (p and k): continue
        v = list(map(float, p.group(1).split()))
        if shapely.box(min(v[1::2]), min(v[0::2]), max(v[1::2]), max(v[0::2])).intersects(mapa): out.append(k.group(1))
    return out


def stahni(n):
    z = f'build/dmr/{n}.laz'
    if os.path.exists(z): return z
    subprocess.run(['curl', '-sfL', '-m', '300', '-o', f'build/dmr/{n}.zip', f'https://openzu.cuzk.gov.cz/opendata/DMR5G/epsg-5514/{n}.zip'], check=True)
    subprocess.run(['unzip', '-oq', f'build/dmr/{n}.zip', '-d', 'build/dmr'], check=True); os.remove(f'build/dmr/{n}.zip')
    return z


def dopln(h):
    """místa bez bodů: nejbližší změřená hodnota, pak vyhlazení jen uvnitř děr (řeka nemá schod uprostřed)"""
    ok = np.isfinite(h)
    if ok.all(): return h
    # nejbližší soused postupným rozšiřováním (bez scipy)
    f = np.where(ok, h, 0.0); w = ok.astype(float); hole = ~ok
    v = f.copy(); known = ok.copy()
    while not known.all():
        p = np.pad(np.where(known, v, 0.0), 1); q = np.pad(known.astype(float), 1)
        s = p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
        c = q[:-2, 1:-1] + q[2:, 1:-1] + q[1:-1, :-2] + q[1:-1, 2:]
        new = ~known & (c > 0)
        if not new.any(): break
        v[new] = s[new] / c[new]; known |= new
    for _ in range(200):                # Laplace jen v dírách, změřené body drží
        p = np.pad(v, 1, mode='edge')
        v = np.where(hole, (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4, v)
    return v


if __name__ == '__main__':
    x0, y0, x1, y1 = geo.extent(OKRAJ)
    x0, y0 = np.floor(x0 / STEP) * STEP, np.floor(y0 / STEP) * STEP
    x1, y1 = np.ceil(x1 / STEP) * STEP, np.ceil(y1 / STEP) * STEP
    nx, ny = int(round((x1 - x0) / STEP)) + 1, int(round((y1 - y0) / STEP)) + 1
    S = np.zeros((ny, nx)); C = np.zeros((ny, nx))          # řádek 0 = sever (y1), jako v prep.py
    L = listy(); print('listů DMR 5G', len(L))
    soubory = [stahni(n) for n in L]
    lon0, lon1, lat0, lat1 = geo.bbox_lonlat(OKRAJ)
    kx, ky = T.transform([lon0, lon1, lon0, lon1], [lat0, lat0, lat1, lat1])
    bb = shapely.box(min(kx), min(ky), max(kx), max(ky))
    for f in soubory + sorted(glob.glob('build/dmp/*.laz')):
        h = laspy.open(f).header
        if not shapely.box(h.mins[0], h.mins[1], h.maxs[0], h.maxs[1]).intersects(bb): continue
        l = laspy.read(f)
        k = np.ones(len(l.x), bool) if '/dmr/' in f else np.array(l.classification) == 2
        X, Y, Z = np.array(l.x)[k], np.array(l.y)[k], np.array(l.z)[k]
        lo, la = TI.transform(X, Y); gx, gy = geo.to_local(lo, la)
        ix = np.rint((gx - x0) / STEP).astype(int); iy = np.rint((y1 - gy) / STEP).astype(int)
        m = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
        np.add.at(S, (iy[m], ix[m]), Z[m]); np.add.at(C, (iy[m], ix[m]), 1)
        print(os.path.basename(f), int(m.sum()), 'bodů')
    H = np.where(C > 0, S / np.maximum(C, 1), np.nan)
    print('uzlů', H.size, 'změřeno', round(100 * float(np.isfinite(H).mean()), 1), '%')
    H = dopln(H)
    np.savez_compressed(OUT, h=H.astype(np.float32), x0=x0, y1=y1, step=STEP, n=C.astype(np.uint16))
    print('->', OUT, H.shape, 'výšky', round(float(H.min()), 1), '–', round(float(H.max()), 1), 'm n. m.')
