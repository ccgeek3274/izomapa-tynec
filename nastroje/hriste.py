# druh sportu a povrch hřišť z OpenStreetMap (Overpass, ODbL, bez registrace); Overture obojí zjednoduší
# (antuka -> „recreation_paved“, sport chybí), prep.py podle toho kreslí antuku, písek a tenisové čáry
# assets/hriste.json: {"w123": {"sport": "tennis", "surface": "clay"}, ...}; spouštět z kořene repa: python nastroje/hriste.py
import json, subprocess, sys, time; sys.path.insert(0, '.')
import geo


def dotaz(q, pokusu=4):
    for i in range(pokusu):
        r = subprocess.run(['curl', '-s', '-f', '-m', '180', '-A', 'izomapa-tools/1.0', '--data-urlencode', f'data={q}',
                            'https://overpass-api.de/api/interpreter'], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip(): return json.loads(r.stdout)['elements']
        time.sleep(20 * (i + 1))                     # Overpass bývá přetížený
    sys.exit('Overpass neodpovídá, zkus to později.')


def hriste(prvky):
    out = {}
    for e in prvky:
        t = e.get('tags', {})
        h = {k: t[k] for k in ('sport', 'surface') if t.get(k)}
        if h: out[e['type'][0] + str(e['id'])] = h
    return out


if __name__ == '__main__':
    x0, y0, x1, y1 = geo.extent(geo.MARGIN + 20)
    lo0, la0 = geo.to_lonlat(x0, y0); lo1, la1 = geo.to_lonlat(x1, y1); b = f'{la0},{lo0},{la1},{lo1}'
    h = hriste(dotaz(f'[out:json][timeout:120];(way["leisure"="pitch"]({b});relation["leisure"="pitch"]({b}););out tags;'))
    json.dump(h, open('assets/hriste.json', 'w'), indent=0)
    from collections import Counter
    print('hřišť', len(h), dict(Counter(q.get('sport', '?') for q in h.values()).most_common(6)),
          dict(Counter(q.get('surface', '?') for q in h.values()).most_common(6)))
