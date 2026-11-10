"""python tests/test_mosty_hriste.py: most se pozná u silnic i u tratí, hřiště z OSM si nesou sport a povrch."""
import sys
sys.path.insert(0, '.'); sys.path.insert(0, 'nastroje')
import mosty, hriste

# Overture: silnice má příznak mostu v road_flags, trať v rail_flags
assert mosty.casti_mostu({'road_flags': [{'values': ['is_bridge'], 'between': [0.2, 0.6]}], 'rail_flags': None}) == [(0.2, 0.6)]
assert mosty.casti_mostu({'road_flags': None, 'rail_flags': [{'values': ['is_bridge'], 'between': None}]}) == [(0.0, 1.0)], 'most přes celou trať'
assert mosty.casti_mostu({'road_flags': [{'values': ['is_tunnel'], 'between': None}], 'rail_flags': None}) == [], 'tunel není most'

h = hriste.hriste([{'type': 'way', 'id': 1, 'tags': {'leisure': 'pitch', 'sport': 'tennis', 'surface': 'clay'}},
                   {'type': 'way', 'id': 2, 'tags': {'leisure': 'pitch'}},
                   {'type': 'relation', 'id': 3, 'tags': {'leisure': 'pitch', 'sport': 'beachvolleyball'}}])
assert h == {'w1': {'sport': 'tennis', 'surface': 'clay'}, 'r3': {'sport': 'beachvolleyball'}}, h
print('ok')
