# Saint-Maurice-sur-Dargoire — église seule (MSFS 2024)

Branche dédiée à la **nouvelle église**, créée à partir de `main`, indépendante des branches Madone, bancs, clocher et Valmorel.

- Modèle : `eglise_saint_maurice_texturee.glb` fourni dans la conversation du 5 novembre 2026.
- GPS : **45.5829444444, 4.6312222222** (45°34′58.6″N 4°37′52.4″E).
- Add-on autonome : `realearth-saint-maurice-eglise`.
- 40 meshes source, nef + abside + clocher ; 8 textures.
- La grande dalle `Sol` est **désactivée** dans le projet préparé.
- Masquage ciblé : uniquement les bâtiments natifs (polygones OSM/détectés + rectangles de bâtiments), sans exclure les arbres, ni modifier le TIN ou le terrain.
- `heading_degrees=0` et pose au sol sont **provisoires** ; orientation et placement visuel à vérifier en jeu.

## Fichiers de livraison

Le **ZIP indépendant remis dans cette même conversation** contient la version complète : modèle original GLB, textures PNG, binaires glTF, projet SDK, `build_install.py`, `INSTALLER_EGLISE.bat`, tests et guide. Ces données d'image restent hors GitHub public, en attendant la vérification des droits de republication.

La compilation sous **SDK Windows FS2024** est indispensable. Ce n'est pas un module `Community` prêt à déposer directement : les BGL et KTX2 ne peuvent pas être générés ici sans `fspackagetool.exe`.

## Isolation

L'installation du ZIP n'opère que sur `Community/realearth-saint-maurice-eglise`, avec sauvegarde de cette seule scène si elle existe déjà. Elle ne touche jamais à :
- `realearth-saint-maurice-vierge`
- `realearth-saint-maurice-bancs`
- `realearth-saint-maurice-nature`
- aucune scène Valmorel / village HD

**Attention :** les exclusions de bâtiments ne peuvent être validées qu'après compilation puis lancement de MSFS2024. Les buildings provenant des données TIN peuvent ne pas disparaître.
