# Vlastní úpravy dat, terénu a doplňků pro konkrétní město.
# Zkopíruj tento soubor do assets/custom_prep.py a uprav podle potřeby.
# Spouští se automaticky z prep.py v jednotlivých fázích (HOOK), takže prep.py zůstává čistý.

if HOOK == 'terrain':
    # Úprava mřížky terénu HX před vyhlazením.
    # K dispozici jsou proměnné: HX, gx, gy, STEP, HALF, CX, CY atd.
    # Například lokální snížení/zvýšení terénu v polygonu:
    pass

elif HOOK == 'terrain_po':
    # Úprava mřížky terénu HX až po vyhlazení (úzké prvky, které by vyhlazení rozmazalo, např. podjezd pod tratí).
    pass

elif HOOK == 'cemetery':
    # Úpravy hřbitova před generováním hrobů (např. aleje stromů, studna, vynechání ploch).
    # K dispozici jsou: trees, EXT_P, nograve, AREA, DRAWBOX atd.
    pass

elif HOOK == 'props':
    # Doplnění vlastních rekvizit do dictionary props (např. zvířata na pastvinách, lavičky).
    # K dispozici jsou: props, AREA, all_lines, buildings, wat, tree_pts atd.
    # Například:
    # props['moje_rekvizita'] = [[x, y, z, rotace, typ], ...]
    pass
