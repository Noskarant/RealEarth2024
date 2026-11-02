# RealEarth Valmorel HD 0.1.5 — station de ski

Branche : `feature/valmorel-station-ski`. Cette version reste **séparée** du
Valmorel 0.1.4 précédemment validé en jeu.

## Ce qui est concrètement intégré

- **Deux bibliothèques CC0 :**
  - [Alpine Snow Village](https://3dassets.dev/packs/alpine-snow-village), 75 modèles disponibles
  - [Ski Resort and Snow Park](https://3dassets.dev/packs/ski-resort-and-snow-park), 85 modèles disponibles
- `scripts/ski_assets.py` récupère **23 modèles pertinents** par leurs noms
  depuis les manifests officiels JSON, puis télécharge les GLB source.
  Téléchargement au **premier build sur le PC Windows**, puis cache réutilisé
  dans `build/ski_assets/`.
- Conversion des coordonnées et `KHR_mesh_quantization` vers glTF 2.0
  avec attributs float standard, couleurs PBR, BIN et ModelInfo XML compatibles
  avec le pipeline de ModelLib de MSFS2024.
- Le pack utilisé ici contient **0 texture image** dans ses modèles (matériaux
  PBR colorés). On n'introduit donc pas des WebP ou des liens de textures
  externes non supportés, cause habituelle de violet. **Le pack Valmorel
  existant, avec 28 KTX2 compilés, demeure utilisé pour les bâtiments IGN.**
- Jusqu'à **26 chalets** remplacent des petits bâtiments IGN existants dont
  les empreintes, étages et proportions conviennent. Ce sont des remplacements,
  jamais un deuxième bâtiment superposé à l'ancien. Les autres bâtiments
  gardent leurs positions et volumes IGN.
- Environ **16 éléments statiques** sont posés sur terrain libre au voisinage
  de trois accès attestés : Pierrafort, Télébourg et Hôtel du Bourg.
  Comptabilisation et validation après génération.
  Exemples : petit terminal, billetterie, dameuse, enneigeur, motoneige,
  signalisation des pistes, bancs, rack à skis, éclairage.
- `building_gen.py` corrige les grandes empreintes en L : les toitures non
  plates et non rectangulaires reçoivent une pente suivant la vraie emprise
  IGN, au lieu du grand toit plat d'avant. Les géométries demeurent des
  approximations des toitures, pas des levés de charpente.
- `build_scenery.py` applique désormais le cap et l'échelle des assets
  individuellement, sans exclusion d'autogen pour les accessoires.

## Ce que cette étape ne prétend PAS reproduire

Les packs sont **stylisés et générés avec l'assistance d'IA**, pas des
photogrammétries d'immeubles de Valmorel. Certains modèles contiennent
de la neige sculptée même en été. Ne pas les confondre avec des façades
vérifiées individuellement.

Pour éviter de créer de fausses remontées, `scripts/ski_lifts.py`
cherche la **véritable géométrie OSM de Pierrafort** et son profil altimétrique
RGE ALTI IGN. Seulement si les deux jeux sont disponibles et cohérents, le
programme génère automatiquement deux câbles immobiles, des pylônes au sol
et des cabines suspendues statiques. Le contrôle couvre les deux gares
identifiées indépendamment ; il n'invente pas un alignement quand OSM échoue.

**Attention :** les positions des pylônes et des cabines sont interpolées
à intervalles réguliers sur le tracé cartographié et ne sont **pas** leurs
positions d'exploitation exactes. Le câble suit le relief IGN à environ
9 m au-dessus du terrain ; les altitudes FS2024 peuvent différer de l'IGN.
Sans données externes fiables, l'intégration saute cette remontée et le
journal l'indique clairement. Les autres remontées attendent un relevé
équivalent.

Sources : [OSM Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API),
[API altimétrique IGN](https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/calcul-altimetrique/),
[Sommet Pierrafort 1835 m](https://lalecherelesbains.valmorel.com/api/hebergements/Valmorel/Boucle%2Bde%2BRoche%2BBlanche%2B-%2BB13/6616725-27/).

**Attribution données géographiques :** © Contributeurs OpenStreetMap,
ODbL 1.0 ; © IGN, RGE ALTI, Géoplateforme.

Les positions des props à côté des accès connus sont **illustratives** et
choisies pour éviter les empreintes de bâtiments : elles ne sont pas
présentées comme des coordonnées GPS de vrais accessoires.

Points de référence :
- [Pierrafort](https://www.cirkwi.com/fr/point-interet/2628998-telecabine-de-pierrafort) : 45.458987, 6.44331.
- [Télébourg](https://www.explore-savoie.com/trains-et-remontees-mecaniques/telebourg-178060/) : 45.462095, 6.445026.
- [Hôtel du Bourg](https://hoteldubourg.com/fr/acces.html) : 45.461427, 6.443471.

## Installation — même lanceur, une seule fois changer de branche

Fermer FS2024. Puis dans PowerShell :

```powershell
cd D:\RealEarth2024
git fetch origin
git switch feature/valmorel-station-ski
.\MAJ_VALMOREL.bat
```

Si `git switch` refuse des modifications locales, **ne pas les
supprimer** : arrêter et demander une méthode de sauvegarde.

Ensuite, pour les prochains builds : double-cliquer uniquement sur
`D:\RealEarth2024\MAJ_VALMOREL.bat`. Il fera lui-même `git pull --ff-only`,
les tests de source, le téléchargement des assets CC0 si nécessaire, la
génération, la compilation SDK, la validation, la sauvegarde de l'ancienne
version et l'installation dans `Community`.

Le bouton de mise à jour **ne doit jamais écraser Community si l'une des étapes
échoue**. Ne pas démarrer FS2024 durant la compilation.

### Résultat attendu dans la console

- `CC0 GLB CONVERTER QA: OK`
- `CC0 station assets: 23 model types` (nombre exact vérifié)
- `IGN chalet replacements` supérieur ou égal à 8
- `Ski resort ground props` supérieur ou égal à 12
- `SKI RESORT MODEL QA: OK`
- Si données disponibles : `PIERRAFORT GONDOLA: OSM+IGN route verified` ; sinon avertissement et aucune ligne inventée
- SDK : 2 BGL, les KTX2 du pack Valmorel et la version **0.1.5**
- `RESULT : OK`, puis `SUCCESS`

### Limites de validation

Les références source, licences, noms et formats GLB ont été vérifiés en
ligne. Les scripts GitHub ont été écrits et contrôlés statiquement, mais
**le téléchargement des GLB sur le PC, leur conversion réelle, la
compilation SDK et le rendu en jeu de cette version 0.1.5 restent non
exécutés**. Conserver l'ancienne v0.1.4 comme référence jusqu'à contrôle
visuel. Les performances en jeu peuvent nécessiter des LOD ou des distances
de dessin ajustés.

## Correctif de démarrage — 2 novembre 2026

Premier essai Windows : `qa_ski_importer.py` échoue à
`ValueError: Imported GLB has no usable triangles`.
Le problème vient **du test généré** : il produisait un tétraèdre à
quatre triangles alors que `convert_glb()` refuse les modèles d'essai de
moins de dix triangles. Les packs n'avaient pas encore été téléchargés.

Correctif : remplacement du tétraèdre par une grille de 16 sommets et
18 triangles réels. Le test valide maintenant également les bornes et
l'application de la transformation `KHR_mesh_quantization`.
La règle de protection minimale du convertisseur est conservée.

La branche est mise à jour sur GitHub. Avec MSFS2024 fermé, relancer
**`MAJ_VALMOREL.bat`** : le lanceur fait `git pull --ff-only`
automatiquement. La version actuellement installée reste intacte jusqu'à
la réussite de toutes les étapes.

**Statut de validation :** correctif du script enregistré, attente du
nouveau journal Windows pour confirmer le test et le téléchargement
effectifs des GLB.

## Correctif service OSM — HTTP 502 du 2 novembre 2026

Le premier téléchargement/conversion des **23 modèles CC0** a réussi et le
pipeline a sélectionné **26 remplacements IGN et 16 accessoires**. La recherche
Overpass du tracé de la télécabine de Pierrafort a toutefois obtenu un
`HTTP Error 502: Bad Gateway`. C'est un incident du serveur cartographique
externe, non une erreur des modèles importés.

`scripts/ski_lifts.py` essaie désormais successivement les instances
`overpass.private.coffee`, `overpass-api.de` et `lz4.overpass-api.de`,
avec une relance courte et un cache seulement après vérification de la
correspondance aux deux terminus connus. Une QA hors réseau,
`scripts/qa_ski_lifts.py`, simule deux réponses HTTP 502 puis une réponse
valide et vérifie la reprise sur le serveur suivant et le cache.

**Important :** ce correctif ne modifie pas une compilation déjà en cours.
Il sera téléchargé automatiquement à la **prochaine ouverture du lanceur**.
Si les données OSM/IGN ne sont pas accessibles malgré cela, la télécabine
ne sera pas fabriquée sur un tracé inventé ; le reste du décor peut passer.

Sources sur les instances publiques :
https://wiki.openstreetmap.org/wiki/Overpass_API
https://overpass.private.coffee/
