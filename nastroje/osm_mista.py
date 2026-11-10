# obchody, služby, úřady a turistické cíle z OpenStreetMap (Overpass, ODbL, bez registrace) pro karty v prohlížeči
# Overture places jsou řidší a bez otevírací doby; OSM má u obchodů často otevírací dobu, web a přesnou polohu.
# Pomníky, kříže, zvoničky, sochy, vrcholy, studánky, stromy a hřiště i bez názvu (stačí druh), s nápisem nebo popisem z OSM.
# Odkaz na Wikipedii: tag wikipedia, jinak česká Wikipedie přes wikidata (API Wikidat), jinak stránka na Wikidatech.
# -> assets/osm_mista.json: [{"id": "n123", "lat", "lon", "nazev", "druh", "otevreno", "web", "wiki", "popis", "ele"}, ...]
#    overlay.py je přiřadí budovám (bod v půdorysu) a ostatní dá jako klikací body (v prohlížeči ikonky ve vrstvě Zajímavosti).
# -> assets/osm_obce.json: [{"nazev", "lat", "lon", "druh", "obyv", "wiki"}, ...] města, vesnice a osady (popisky při oddálení)
# spouštět z kořene repa: python nastroje/osm_mista.py   (DRUHY níže určují, co se do mapy dostane)
import json, re, sys, urllib.parse, urllib.request; sys.path.insert(0, '.'); sys.path.insert(0, 'nastroje')
import geo
from hriste import dotaz

# klíč=hodnota -> český druh; jen tyto prvky se do mapy dostanou
DRUHY = {
    'shop': {'supermarket': 'supermarket', 'convenience': 'potraviny', 'bakery': 'pekárna', 'butcher': 'řeznictví',
             'greengrocer': 'ovoce a zelenina', 'doityourself': 'stavebniny a hobby', 'hardware': 'železářství',
             'garden_centre': 'zahradnictví', 'sports': 'sportovní potřeby', 'chemist': 'drogerie', 'pet': 'chovatelské potřeby',
             'shoes': 'obuv', 'clothes': 'oblečení', 'cheese': 'sýry', 'farm': 'farmářský obchod', 'florist': 'květinářství',
             'tyres': 'pneuservis', 'car_repair': 'autoservis', 'car': 'autosalon', 'hairdresser': 'kadeřnictví',
             'optician': 'optika', 'books': 'knihkupectví', 'electronics': 'elektro', 'furniture': 'nábytek', 'beverages': 'nápoje',
             'kiosk': 'trafika', 'gas': 'prodej plynu', 'bicycle': 'jízdní kola', 'variety_store': 'smíšené zboží'},
    'amenity': {'restaurant': 'restaurace', 'pub': 'hospoda', 'bar': 'bar', 'cafe': 'kavárna', 'fast_food': 'rychlé občerstvení',
                'ice_cream': 'zmrzlina', 'pharmacy': 'lékárna', 'post_office': 'pošta', 'townhall': 'úřad', 'school': 'škola',
                'kindergarten': 'mateřská škola', 'library': 'knihovna', 'police': 'policie', 'fire_station': 'hasiči',
                'bank': 'banka', 'fuel': 'čerpací stanice', 'place_of_worship': 'kostel', 'community_centre': 'kulturní dům',
                'bus_station': 'autobusové nádraží', 'boat_rental': 'půjčovna lodí', 'public_bookcase': 'knihobudka',
                'doctors': 'lékař', 'dentist': 'zubař', 'clinic': 'zdravotní středisko', 'veterinary': 'veterinář',
                'cinema': 'kino', 'theatre': 'divadlo', 'arts_centre': 'kulturní centrum'},
    'tourism': {'hotel': 'hotel', 'guest_house': 'penzion', 'museum': 'muzeum', 'viewpoint': 'vyhlídka',
                'attraction': 'turistický cíl', 'camp_site': 'kemp', 'gallery': 'galerie', 'hostel': 'ubytovna', 'chalet': 'chata k pronájmu'},
    'historic': {'castle': 'hrad', 'ruins': 'zřícenina', 'memorial': 'pomník', 'monument': 'pomník', 'archaeological_site': 'archeologické naleziště'},
    'leisure': {'sports_centre': 'sportovní areál', 'fitness_centre': 'posilovna', 'swimming_pool': 'koupaliště',
                'playground': 'dětské hřiště', 'fitness_station': 'venkovní posilovna', 'picnic_table': 'piknik', 'firepit': 'ohniště'},
    'man_made': {'observation_tower': 'rozhledna', 'cross': 'kříž'},
    'natural': {'peak': 'vrchol', 'spring': 'pramen', 'tree': 'strom'},
}
DRUHY['historic'].update({'wayside_cross': 'kříž', 'wayside_shrine': 'boží muka'})
DRUHY['tourism'].update({'artwork': 'umělecké dílo', 'picnic_site': 'piknik'})
DRUHY['amenity'].update({'bbq': 'ohniště'})
PAMATNIK = {'plaque': 'pamětní deska', 'stone': 'pamětní kámen', 'statue': 'socha', 'war_memorial': 'válečný pomník', 'bust': 'busta'}
# druhy, které se do mapy dostanou i bez názvu (karta pak ukáže druh, popis nebo nápis)
BEZ_NAZVU = {'vyhlídka', 'knihobudka', 'rozhledna', 'zřícenina', 'pomník', 'pamětní deska', 'pamětní kámen', 'válečný pomník', 'busta',
             'socha', 'umělecké dílo', 'kříž', 'boží muka', 'zvonička', 'vrchol', 'pramen', 'studánka', 'strom', 'památný strom',
             'dětské hřiště', 'venkovní posilovna', 'piknik', 'ohniště', 'kemp'}
MESICE = dict(zip('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), 'leden únor březen duben květen červen červenec srpen září říjen listopad prosinec'.split()))
OBEC = {'town': 'město', 'village': 'vesnice', 'hamlet': 'osada', 'suburb': 'část obce', 'neighbourhood': 'čtvrť', 'isolated_dwelling': 'samota'}
DNY = {'Mo': 'po', 'Tu': 'út', 'We': 'st', 'Th': 'čt', 'Fr': 'pá', 'Sa': 'so', 'Su': 'ne', 'PH': 'svátky'}


def druh(t):
    if t.get('tourism') == 'attraction' and t.get('historic'): return None          # popíše se jako historic
    tt = t.get('tower:type', '').split(';')
    if t.get('man_made') == 'tower' and 'observation' in tt: return 'rozhledna'
    if t.get('man_made') == 'tower' and 'bell_tower' in tt: return 'zvonička'
    if t.get('historic') in ('memorial', 'monument'): return PAMATNIK.get(t.get('memorial'), 'pomník')
    if t.get('tourism') == 'artwork' and t.get('artwork_type') in ('statue', 'sculpture', 'bust'): return 'socha'
    if t.get('natural') == 'tree' and t.get('denotation') == 'natural_monument': return 'památný strom'
    if t.get('natural') == 'spring' and 'studán' in (t.get('name') or '').lower(): return 'studánka'
    for k in ('amenity', 'tourism', 'historic', 'man_made', 'natural', 'leisure', 'shop'):     # čerpací stanice s prodejem plynu je čerpací stanice
        m = DRUHY[k]
        if t.get(k) in m:
            d = m[t[k]]
            if k == 'amenity' and t[k] == 'place_of_worship' and t.get('building') == 'chapel': d = 'kaple'
            return d
    return None


def otevreno(s):
    """OSM opening_hours -> čitelná čeština (jednoduché tvary; složitější se nechají, jak jsou)"""
    if not s: return None
    if s.strip() == '24/7': return 'nonstop'
    out = s.replace(' off', ' zavřeno').replace('; ', ', ').replace(';', ', ')
    out = re.sub(r'\b(Mo|Tu|We|Th|Fr|Sa|Su|PH)\b', lambda m: DNY[m.group(1)], out)
    out = re.sub(r'\b(' + '|'.join(MESICE) + r')\b', lambda m: MESICE[m.group(1)], out)
    out = re.sub(r'(?<=[a-zúáčěří.])-(?=[a-zúáčěří])', '–', out)                         # po-pá -> po–pá
    out = re.sub(r'\b0(\d):', r'\1:', out)                                             # 07:00 -> 7:00
    out = re.sub(r'(\d:\d\d)-(\d)', r'\1–\2', out)
    return out


def web(t):
    w = t.get('website') or t.get('contact:website') or t.get('url')
    if not w: return None
    return w if w.startswith('http') else 'https://' + w


def wiki(t, cswiki):
    """odkaz na článek: cs Wikipedie z tagu nebo přes wikidata, jinak Wikipedie v jiném jazyce, jinak Wikidata"""
    w, q = t.get('wikipedia', ''), t.get('wikidata')
    if w.startswith('cs:'): return 'https://cs.wikipedia.org/wiki/' + w[3:].replace(' ', '_')
    if q and q in cswiki: return 'https://cs.wikipedia.org/wiki/' + cswiki[q].replace(' ', '_')
    if ':' in w: return f'https://{w.split(":")[0]}.wikipedia.org/wiki/' + w.split(':', 1)[1].replace(' ', '_')
    if q: return 'https://www.wikidata.org/wiki/' + q
    return None


def cs_clanky(qids):
    """wikidata Q… -> název článku na cs Wikipedii (API Wikidat, po 50)"""
    out, qids = {}, sorted(set(qids))
    for i in range(0, len(qids), 50):
        url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'ids': '|'.join(qids[i:i + 50]), 'props': 'sitelinks', 'sitefilter': 'cswiki', 'format': 'json'})
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'izomapa-tools/1.0'}), timeout=60))
        except Exception as e:
            print('Wikidata neodpovídají, odkazy zůstanou na Wikidata:', e); return out
        for q, ent in d.get('entities', {}).items():
            sl = (ent.get('sitelinks') or {}).get('cswiki')
            if sl: out[q] = sl['title']
    return out


def clanek_obce(nazev, lat, lon):
    """článek cs Wikipedie o vesnici podle polohy (geosearch do 2 km): název přesně, nebo „Název (upřesnění)“"""
    url = 'https://cs.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'query', 'list': 'geosearch', 'gscoord': f'{lat}|{lon}', 'gsradius': 2000, 'gslimit': 50, 'format': 'json'})
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'izomapa-tools/1.0'}), timeout=60))
    except Exception:
        return None
    for g in sorted(d.get('query', {}).get('geosearch', []), key=lambda g: g['dist']):
        if g['title'] == nazev or g['title'].startswith(nazev + ' ('): return 'https://cs.wikipedia.org/wiki/' + g['title'].replace(' ', '_')
    return None


def popis(t, n):
    """nápis (pomníky, desky) nebo popis z OSM, když už není v názvu"""
    if t.get('inscription'): return 'Nápis: „' + t['inscription'].strip().strip('"„“') + '“'
    d = (t.get('description') or '').strip()
    return d if d and d != n else None


def mista(prvky, cswiki={}):
    out = []
    for e in prvky:
        t = e.get('tags') or {}
        d = druh(t)
        if not d: continue
        lat, lon = (e['lat'], e['lon']) if 'lat' in e else (e['center']['lat'], e['center']['lon']) if 'center' in e else (None, None)
        if lat is None: continue
        n = t.get('name') or t.get('brand')
        if not n and t.get('description') and len(t['description']) <= 70 and not t['description'].endswith('.'):
            n = t['description']                                   # „Pomník padlým v Těptíně“, „Zvonička v Ládví“ (OSM tu má jen popis)
        if n and d in ('pošta', 'hrad') and d not in n.lower(): n = f'{d.capitalize()} {n}'      # „Týnec nad Sázavou“ -> „Pošta Týnec nad Sázavou“
        if not n and d not in BEZ_NAZVU: continue                                              # bezejmenné jen tam, kde druh stačí
        if d in ('strom', 'památný strom') and not n and t.get('species:cs'): n = t['species:cs']
        ele = t.get('ele', '').replace(',', '.') if d in ('vrchol', 'rozhledna', 'vyhlídka') else ''
        out.append({k: v for k, v in {'id': e['type'][0] + str(e['id']), 'lat': round(lat, 7), 'lon': round(lon, 7), 'nazev': n, 'druh': d,
                                      'otevreno': otevreno(t.get('opening_hours')), 'web': web(t), 'wiki': wiki(t, cswiki),
                                      'popis': popis(t, n), 'ele': float(ele) if re.fullmatch(r'\d+(\.\d+)?', ele) else None}.items() if v})
    return out


if __name__ == '__main__':
    x0, y0, x1, y1 = geo.extent(geo.MARGIN + 20)
    (lo0, lo1), (la0, la1) = geo.to_lonlat([x0, x1], [y0, y1])
    bb = f'{la0:.5f},{lo0:.5f},{la1:.5f},{lo1:.5f}'
    q = ('[out:json][timeout:180];(' + ''.join(f'nwr["{k}"~"^({"|".join(m)})$"]({bb});' for k, m in DRUHY.items())
         + f'nwr["tower:type"~"observation|bell_tower"]({bb});node["place"~"^({"|".join(OBEC)})$"]({bb});'
         f'rel["boundary"="administrative"]["admin_level"~"^(8|10)$"]["wikipedia"]({bb}););out tags center;')
    E = dotaz(q)
    cswiki = cs_clanky(e['tags']['wikidata'] for e in E if (e.get('tags') or {}).get('wikidata') and not e['tags'].get('wikipedia', '').startswith('cs:'))
    M = mista([e for e in E if 'place' not in e.get('tags', {}) and 'boundary' not in e.get('tags', {})], cswiki)
    hranice = {e['tags']['name']: e['tags'] for e in E if e['type'] == 'relation' and e['tags'].get('name')}   # obce a části obcí s odkazem
    for m in M:                    # pojmenované vrcholy: článek podle polohy (Grybla, Vlková)
        if m['druh'] == 'vrchol' and m.get('nazev') and not m.get('wiki'):
            w = clanek_obce(m['nazev'], m['lat'], m['lon'])
            if w: m['wiki'] = w
    json.dump(M, open('assets/osm_mista.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    O = [{k: v for k, v in {'nazev': e['tags']['name'], 'lat': round(e['lat'], 7), 'lon': round(e['lon'], 7), 'druh': OBEC[e['tags']['place']],
                            'obyv': int(e['tags']['population']) if e['tags'].get('population', '').isdigit() else None,
                            'wiki': wiki(e['tags'], cswiki) or wiki(hranice.get(e['tags']['name'], {}), cswiki)
                                    or clanek_obce(e['tags']['name'], e['lat'], e['lon'])}.items() if v}
         for e in E if e['type'] == 'node' and e.get('tags', {}).get('place') in OBEC and e['tags'].get('name')]
    json.dump(O, open('assets/osm_obce.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('míst', len(M), 'z toho s odkazem na Wikipedii', sum('wikipedia.org' in m.get('wiki', '') for m in M), '| obcí a osad', len(O))
