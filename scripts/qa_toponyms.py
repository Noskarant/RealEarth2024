import json, unicodedata
fc = json.load(open(r'D:\RealEarth2024\data\raw\toponymie.geojson', encoding='utf-8'))
def norm(s):
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()
want = ['valmorel','meiller','avancher','planchamp','lanchette','mottet','creve','nielard','cheval','montolivet','cheval noir']
seen = set()
for f in fc['features']:
    p = f['properties']; nm = p.get('graphie_du_toponyme') or ''
    if not any(w in norm(nm) for w in want): continue
    g = f['geometry']
    c = g['coordinates'] if g['type'] == 'Point' else g['coordinates'][0][0]
    key = (nm, p.get('classe_de_l_objet'))
    if key in seen: continue
    seen.add(key)
    print(f"{nm} | {p.get('classe_de_l_objet')} | {p.get('statut_du_toponyme')} | {c[1]:.6f} {c[0]:.6f}")
