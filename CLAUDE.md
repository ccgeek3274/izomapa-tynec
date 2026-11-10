# izomapa – návod pro AI agenta

Uživatel chce izometrickou pixel-art mapu svého města („udělej mi izometrickou mapu Chrastavy“). Předloha je
https://izomapa.fun (Liberec). Liberec sám nedělej, ten si autor spravuje sám: když o něj uživatel požádá, nabídni
jiné město. Komunikuj česky, věcně, a před dlouhými kroky řekni, kolik budou trvat.

## Postup pro nové město

1. **Prostředí:** když chybí `.venv` nebo `node_modules`, spusť `./setup.sh`. Python vždy z `.venv`. Na Windows je to
   `.venv/Scripts/python` a skripty se pouštějí v Git Bash (`sh ./setup.sh`, `sh ./postav.sh`). Python pouštěj
   s `PYTHONUTF8=1`, jinak na Windows píše výpisy i soubory v cp1250 (padá na `²`, rozbije češtinu v JSON pro web).
2. **Založení:** `.venv/bin/python novy_mesto.py "Název"` (víceslovné nebo nejednoznačné názvy: `--dotaz "Název, okres X"`).
   Vypíše počet čtverců 2,3 × 2,3 km. Řekni uživateli, kolik to je a jak dlouho to potrvá (orientačně: stažení
   10–30 min, render 5–10 min na čtverec na Macu s Apple Silicon). U velkého města nabídni nejdřív centrum:
   `--max 4` (jen 4 čtverce kolem středu).
3. **Texty v `mesto.json`:** zkontroluj rod („Izometrický Liberec“, „Izometrická Chrastava“, „Izometrické Brno“),
   `podtitul` a `popis`. Vánoční strom: `vanocni_strom: [lat, lon]` hlavního náměstí.
   **MHD:** zeptej se uživatele: „Chceš v mapě i jezdící MHD podle jízdních řádů?“ Když ano, najdi sám, jestli má
   dopravce města vlastní veřejné GTFS, nebo je město v krajském systému, a doplň `mhd.gtfs` (URL zipu), `mhd.zdroj`
   (název dopravce) a `mhd.zdroj_url`. Krajské GTFS (IDS JMK, KORDIS) jde taky: `mhd.py` vezme jen autobusy, trolejbusy
   a tramvaje přes mapu, a když GTFS nemá `shapes.txt`, trasy dopočítá po silnicích (`road_route.py`). Upozorni ho, ať si ověří podmínky dopravce, a po stavbě ať trasy projde v mapě
   (vozidla jedou po silnicích, nestojí, nejezdí přes domy). Vlaky do mapy nepatří.
   Prohlížeč kreslí tramvaj jako tmavě červenou T3 a autobus bílý (`drawVehicle` ve `web/app.html`). Když má město
   trolejbusy, nebo jiné barvy vozidel, nabídni, že dokreslíš vlastní model (trolejbus se sběrači, tramvaj nebo autobus
   v barvách místního dopravce). Podklad jsou uživatelovy fotky nebo volně licencované fotky z Wikimedia Commons.
4. **Stavba:** `./postav.sh` (spouštěj na pozadí, běží dlouho). Kroky, které už mají výsledek, přeskakuje.
5. **Kontrola:** `python compose.py summer 8` udělá `build/nahled_summer.png`. Prohlédni si ho (švy mezi čtverci,
   prázdná místa, divné barvy) a pošli uživateli. Pak `npm run nahled` a mapa běží na http://localhost:8000.
6. **Doladění s uživatelem** (níže). Po každé úpravě: `./postav.sh render` (jen scény, render a web).
7. **Řekni uživateli na rovinu**, že mapu musí projít a porovnat se skutečností (data i ty se můžete mýlit),
   hlavně fakta v příbězích míst, než ji zveřejní. Kredit „Vytvořeno nástrojem izomapa“ v prohlížeči nech, pokud ho
   uživatel výslovně nechce odstranit.
8. **Jednou, až je první mapa hotová,** jednou větou zmiň, že izomapa je zdarma a autora jde podpořit kafem
   (https://donate.stripe.com/3cI6oA0PE7u65Y9cim8g000). Víckrát to neopakuj.
9. **Až bude mapa veřejně na webu,** řekni uživateli, že ji může přidat do katalogu map na https://izomapa.fun/mesta/
   (tlačítko „Přidat město“ založí žádost na GitHubu: obec, kraj, odkaz, autor a nepovinný popis do 120 znaků).
   Nabídni, že mu žádost předvyplníš. Řekni to jednou.

## Co ladit a jak

Automaticky z dat vyjde celé město. Ručně je potřeba:

- **Dominanty** (kostel, radnice, zámek, rozhledna) → `assets/dominanty.json`. Požádej uživatele o fotky z více
  stran, ideálně do složky `fotky/<název stavby>/` (je v `.gitignore`). Formát položky:
  `{"name", "lat", "lon", "text", "spec": {...}}`, kde `spec`:
  - `wc` barva zdí, `rc` barva střechy (RGB), `r` tvar střechy (`hipped`, `gabled`, `flat`…), `h` výška zdí, `rh` výška střechy,
    `win` styl oken, `face` [lat, lon] bodu, ke kterému je průčelí (náměstí),
  - `towers` [{`at` front/back/c/n/s/e/w…, `side` posun podél průčelí, `w`, `h`, `top` spire/helm/tiered/dome/pyramid/cone/none,
    `to` výška špičky, `tc` barva, `clock`, `round`, `stone`, `ruin`}], `chimneys`, `blocks` (nástavby), `canopy`, `skylights`,
  - `lm` vlastní model: specifické modely pro dané město nepiš do `render.html`, ale do `assets/custom_models.js` (ukázka v `priklady/custom_models.js`), v `dominanty.json` pak stačí `spec: {"lm": "nazev_modelu"}`.
  - `only`: samostatná stavba bez budovy v datech (zřícenina, rozhledna).
  Napárování na budovu: bod uvnitř půdorysu, jinak největší budova do 25 m (`match_doms` v `prep.py`).
  Ukázka je v `priklady/dominanty.json`.
- **Vlastní kód a lokální úpravy města nepatří do sdíleného `prep.py` ani `render.html`!** Pro specifické úpravy terénu, hřbitovů a rekvizit použij `assets/custom_prep.py` (fáze `HOOK` `terrain` / `cemetery` / `props`, ukázka v `priklady/custom_prep.py`). Pro specifické 3D modely použij `assets/custom_models.js`. Oba soubory jsou v `.gitignore` a načítají se automaticky, takže hlavní kód zůstává čistý pro upstream git.
- **Příběhy míst** → `mista.json`: `[{"nazev", "lat", "lon", "text"}]`. Texty piš jen z ověřených zdrojů (web obce,
  Památkový katalog, Wikipedie s odkazem). Když si nejsi jistý, zeptej se uživatele. Nic si nevymýšlej.
  Ukázka je v `priklady/mista.json`.
- **Chyby v datech:** špatná výška → zkontroluj `build/dmp_kontrola.csv`; chybějící nebo nesmyslná budova → nejlepší
  je opravit ji v OpenStreetMap (a za pár týdnů se propíše do Overture), jinak pravidlo v `prep.py`.
- **Vlaky:** `"vlak"` v `mesto.json` vybírá model z katalogu `TRAINS` ve `web/app.html`: `regiopanter`, `regioshark`, `regionova`, `vuz810`, `cityelefant`, `rychlik`. Buď text, nebo `{"vychozi": "regionova", "linky": {"číslo linky": "rychlik"}}`, když na mapě jezdí víc druhů. Bez této volby se vlaky nekreslí, potřebují tvary tras v GTFS. Výchozí model je `regionova`. Nový model je jeden řádek v katalogu.
- **Barvy střech:** `.venv/bin/python nastroje/strechy.py` (ortofoto po 0,4 m/px, 7 km čtverec ~10 min) vyrobí `assets/strechy_orto.json`, `prep.py` je pak použije u všech budov místo náhodných. Dominanty mají přednost.
- **Zeleň na zpevněných plochách:** po `nastroje/strechy.py` spusť `nastroje/povrchy.py` (`build/zelen_maska.png`). Zpevněné a průmyslové plochy, které jsou na ortofotu zelené, se změní na trávu a náměstí, které je z více než poloviny zelené, na park se stromy.
- **Ruční povrchy** → `assets/upresneni.json`: `"plochy": [{"k": "plaza", "q": [[lat, lon], …]}]` (třídy `plaza`, `plaza2`, `deck`, `park`; kreslí se přes cesty). Stromy podle ortofota: `assets/oblasti.json`, `{"název": {"poly": [[lat, lon], …], "trees": [[lat, lon, výška, jehličnan]], "b": {}, "b_auto": {}, "skryt": true}}` (náhodné stromy v polygonu zmizí, `skryt` zachová pořadí ostatních, takže se nemění jejich barvy ani švy).
- **Směr hřebene:** `.venv/bin/python nastroje/hrebeny.py` (po `dmp_fetch.py`) zapíše do `assets/hrebeny.json` jen jisté případy, kde laser ukazuje hřeben podél kratší strany.
- **Hustota aut (volitelné):** `.venv/bin/python nastroje/scitani.py` a v `mesto.json` `"doprava": {"kraj": "Název kraje"}`. Volitelně `"useky": {"číslo silnice": ["úsek sčítání", …]}` vybere přesné úseky, jinak se bere medián silnice v kraji. Počet aut na mapě je ilustrace poměrů, ne skutečný počet. Na silnici jezdí 40 % špičkové hustoty (`CAR_DENS` v `web/app.html`), na telefonu, při pomalém připojení a v úsporném režimu z toho jen třetina. Pojistka pro velká města: na celé mapě nejvýš 1 000 aut, na slabších zařízeních 300 (`MAX_CARS`). Rampy (`subclass` link) mají pětinu intenzity a nejvýš 50 km/h.
- **Typy budov (jen Česko):** `.venv/bin/python nastroje/ruian.py` vyrobí `assets/ruian_budovy.json` (způsob využití a podlaží z veřejné služby RÚIAN). `prep.py` jím doplní jen prázdný nebo obecný typ a podlaží tam, kde není laser. Třída `apartments` znamená plochou střechu, proto ji dostane jen budova, u které plochou střechu potvrdí laser. Po změně je potřeba nový render.
- **Komíny, věže, nádrže, potrubí:** `.venv/bin/python nastroje/kominy.py` vyrobí `assets/kominy.json` a `assets/potrubi.json` z OSM (výška z tagu `height`). Komín od 100 m dostane výstražné pruhy. Vzhled jednoho komína: `assets/upresneni.json`, `"kominy": [{"lat", "lon", "wc": barva, "pr": 0}]`. Po změně je potřeba nový render dotčených čtverců.
- **Železniční přejezdy (volitelné):** `.venv/bin/python nastroje/prejezdy.py` vyrobí `assets/prejezdy.json` z OSM (`railway=level_crossing`), `prep.py` je přiřadí silnicím, které tam kříží kolej. Přejezd se zavře asi 25 s před příjezdem vlaku podle jízdních řádů a otevře, až projede poslední vůz; auta před ním čekají ve frontě. Bez souboru nebo bez vlaků v MHD auta nečekají. Render není potřeba, stačí `prep.py`, `overlay.py` a `build_html.py`.
- **Mosty z laseru:** `.venv/bin/python nastroje/mosty.py` (po `dmp_fetch.py`, spouští ho i `postav.sh`) změří výšku mostovek z bodů DMP 1G a uloží `assets/mosty_vysky.json`. `prep.py` ji použije místo odhadu z pravidel (lávka 1 m nad vodou, 5,2 m nad cestou); když laser ukáže mostovku na úrovni terénu modelu (vyhlazený terén nad podjezdem), most se nezvedá.
- **Terén z laseru:** `.venv/bin/python nastroje/teren.py` (spouští ho i `postav.sh`) stáhne listy DMR 5G ČÚZK (~3 MB na list) a s body terénu z DMP 1G udělá `build/teren_laser.npz` (mřížka 5 m pro celou mapu). `prep.py` ho použije místo hrubého zdrojového terénu (~10 m/px), který se u řek, náspů a podjezdů mýlí o metry. Bez souboru zůstane zdrojový terén.
- **Hřiště (volitelné):** `.venv/bin/python nastroje/hriste.py` vyrobí `assets/hriste.json` z OSM (sport a povrch). Overture antuku nerozliší a sport zahodí; s tímto souborem kreslí `prep.py` antukové kurty s tenisovými čarami a písek u plážového volejbalu. Hřiště, která se jen dotýkají, mají každé své čáry. Ruční oprava povrchu: `assets/upresneni.json`, `"hriste": {"w<OSM id>": {"surface": "clay"}}` (lepší je doplnit `surface` přímo v OSM).
- **Obchody, služby a turistické cíle (volitelné):** `.venv/bin/python nastroje/osm_mista.py` vyrobí `assets/osm_mista.json` z OSM (druh česky, otevírací doba, web; co se bere, určuje `DRUHY`). `overlay.py` je přiřadí budovám (karta: druh, otevřeno, odkaz na web; budova bez názvu dostane název obchodu nebo služby) a ostatní dá jako klikací body. Bere i bezejmenné pomníky (s nápisem), kříže, boží muka, zvoničky, sochy, vrcholy s výškou, studánky, stromy a dětská hřiště; odkaz na Wikipedii z tagu, přes Wikidata nebo podle polohy. V prohlížeči mají zajímavosti pixelové ikonky (vrstva Zajímavosti, i v budově: kostel, zvonička). Města, vesnice a osady (`assets/osm_obce.json`) a pojmenované vrcholy jsou popisky při oddálení, klik ukáže kartu. Stačí `overlay.py` a `build_html.py`, render není potřeba.
- **Zastávky (volitelné):** `.venv/bin/python nastroje/zastavky.py` (po `mhd.py`, potřebuje `build/gtfs.zip`) vyrobí `assets/zastavky.json`: autobusová nástupiště z jízdních řádů (každá strana silnice zvlášť) a železniční stanice s nástupišti z OSM. `prep.py` pak dá přístřešek ke každému nástupišti na kraj vozovky otevřený k silnici (bod z Overture jen tam, kde jízdní řád nic nemá), nakreslí nástupiště vlaků (i ta zakreslená v OSM jen čarou) a na ně přístřešek otevřený ke koleji. Po změně je potřeba nový render.
- **Vodáci (volitelné):** `.venv/bin/python nastroje/reky.py` vyrobí `assets/reky.json` (osy `waterway=river` z OSM ve směru toku, řeky s aspoň 1,5 km v mapě). `overlay.py` je dá do `overlay.json` (`rivers`) a prohlížeč po nich v létě ve dne pouští žluté kánoe se dvěma vodáky po proudu, asi jednu na 1,1 km řeky (≈ 2 na čtverec). Loď pluje od vstupu řeky do mapy po výstup, pak zmizí a za chvíli vypluje znovu; pod mostem není vidět. Render není potřeba.
- **Jezy** (`waterway=weir`) kreslí `prep.py` do terénu: betonová koruna a pěna na níže položené straně.
- **Hřiště jsou vodorovná:** `prep.py` srovná terén pod každým hřištěm (kurty do 3 m od sebe jako jednu plošinu) na medián terénu pod ním. Kde zdrojový terén neodpovídá skutečnosti, oprav ho v `assets/custom_prep.py` (fáze `terrain_po`, např. podle laseru) – hřiště se srovná až na opravený terén.
- **Les a pole:** maska lesa z ortofota (`nastroje/les.py`), pole ze ZABAGED (`nastroje/zabaged.py`, `nastroje/pole.py`).
  Když les nesedí, uprav prahy barev v `nastroje/les.py` a ověř na `build/orto_cele.jpg`.

Rychlá kontrola jednoho místa bez celého čtverce:
`python prep.py data_c0_-1 0,-1` a `node render.mjs mpp=0.2 dir=build/c0_-1 out=build/test season=summer alpha=1 "tiles=7_3;7_4"`.
Ukazuj uživateli výřezy před a po.

- **Hlášení nepřesností** (volitelné): `"hlaseni": true` v `mesto.json` zobrazí v kartě tlačítko a `build_html.py`
  zkopíruje `hlaseni/admin.html` do `site/`. Potřebuje server z `hlaseni/` (Cloudflare Worker + D1, návod v README).
  Nabídni to, až bude mapa veřejně; nasazení a heslo dělá uživatel sám. Jiný hosting = přepsat `hlaseni/worker.js`.
  Při nasazení uživateli řekni, ať nastaví i tajný `SALT` (`npx wrangler secret put SALT`, dlouhý náhodný řetězec):
  bez něj se otisk IP počítá s veřejnou výchozí solí a z uniklé databáze jde IP dopočítat. `TURNSTILE_SECRET` nezapínej,
  formulář v mapě neposílá token a všechna hlášení by pak selhala.

## Pravidla

- **Nikdy neobkresluj ze screenshotů Google Maps, Apple Maps ani Mapy.cz** (podmínky to zakazují). Tvary, barvy střech a
  polohy ber z ortofota ČÚZK (WMS `https://ags.cuzk.gov.cz/arcgis1/services/ORTOFOTO/MapServer/WMSServer`), z dat
  a z fotek, které uživatel sám pořídil.
- Fotky a podklady uživatele do gitu nepatří (`fotky/`, `podklady/` jsou v `.gitignore`).
- Patička nápovědy s uvedením zdrojů dat (OpenStreetMap, ČÚZK, dopravce) musí zůstat.
- Funguje jen v Česku (ČÚZK). Pro jinou zemi řekni, co chybí: laserové výšky, ortofoto, ZABAGED.
- Hosting řeší uživatel. Výsledek je statická složka `site/`. Doporuč jen, ať zvolí hosting, který zvládne hodně souborů
  (hlášení nepřesností potřebují server, viz výše).

## Jak to funguje (pro úpravy kódu)

- `geo.py`: souřadnice a kamera (dimetrie 2:1, pohled od jihozápadu), čte `mesto.json`. Čtverec (0, 0) je střed města,
  i roste na východ, j na sever. `MARGIN` 80,5 m: každý čtverec kreslí i pás sousedů (budovy, stromy) kvůli švům.
- `prep.py DATA i,j`: scéna čtverce do `build/` (0,0) nebo `build/c<i>_<j>/`. Obecná pravidla budov: činžák (navazující
  nepravidelné budovy v husté zástavbě) má šikmou střechu, panelák (navazující obdélníky se stejnou hloubkou) plochou;
  plochá střecha také tam, kde laser měří vršek skoro stejně jako medián. Kostel má vždy věž. Garáže = řada malých
  budov bez typu.
- mosty a lávky: úsek s `is_bridge` (OSM/Overture) delší než 8 m se nemaluje do terénu, ale je 3D mostovka (`scene.bridges`):
  nad cestou nebo tratí pod mostem zvednutá na 5,2 m (trať 6 m), nad vodou trochu nad hladinu, v rozpětí horní konvexní obálka (bez propadů).
  Nájezdy (žádné „skokánky“): mostovka pokračuje do navazující cesty stejného druhu (i když most končí uprostřed segmentu, až 8 kusů / 200 m)
  a výška nad terénem klesá nejvýš o `GRADE` (silnice 6 %, trať 3 %, lávka 8 %) – nájezd tak kopíruje svah. Ta část cesty se pak
  nekreslí do terénu (auta jedou po mostovce). Navazující kusy jednoho mostu se nejdřív spojí (linemerge). Bez navazující cesty
  konec přistane strměji (max. 20 %). V `render.html` je mostovka souvislý pás (pokos na ohybech, výška vyhlazená); do 2,5 m nad
  terénem je to zemní násyp se svahem 1:0,5 bez zábradlí a pilířů; kde se dotýká jiná mostovka (`covered`), boky a zábradlí se nekreslí.
  Šířka silnic: `rwidth` v `prep.py` (jednosměrný pás dvoupásové silnice 60 %, sjezd `link` max. 5 m). Silnice: boky, betonové zábradlí, pilíře po 22 m, středová čára; lávky úzké se sloupkovým
  zábradlím. Auta jedou po mostovce (`roads` v info_src), MHD z jízdních řádů přes `decks` v overlay.json (`deckZ` v app.html).
  Tunel kratší než 60 m je podjezd: kreslí se jako cesta (nad ním vede most), delší tunely se nekreslí.
- `render.html` + `render.mjs`: three.js v headless Chromiu po dlaždicích, varianty `spring summer autumn winter lights`.
  Na macOS s GPU (Metal), na Windows s GPU (Direct3D 11). Výstup se může o odstín lišit mezi běhy, proto se renderuje vždy celý čtverec.
- `dzi.py`: paleta a Deep Zoom pyramidy (WebP). `compose.py`: složený náhled. `preview.py`: rychlý náhled pro web.
- `overlay.py`: klikací vrstva (obrys budovy = konvexní obal půdorysu dole a nahoře). Po úpravě budov vždy spustit
  a obrys zkontrolovat v prohlížeči.
- `build_html.py` vyrobí i `site/og.jpg` (náhled pro sdílení, výřez středu), když je v `mesto.json` vyplněné `url`; vlastní `site/og.jpg` nepřepíše. Pokud existuje složka `obce/*.json` (více obcí v jedné mapě), vyrobí pro každou obec i `site/index_<obec>.html` a `site/obce/<obec>/og.jpg` s vlastním výchozím pohledem (`"pohled": [lat, lon, km]`, volitelně `"domu_celek": true`) a texty.
- `web/app.html`: prohlížeč (OpenSeadragon + animovaná vrstva: auta, MHD, lyžaři, kouř, počasí). Texty `{{…}}`
  doplní `build_html.py` z `mesto.json` (příp. `obce/<obec>.json`).
