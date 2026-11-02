# Statue de la Vierge — Saint-Maurice-sur-Dargoire (Chabanière)

Branche indépendante : `feature/vierge-saint-maurice` (base `main`).
Le décor de Valmorel reste inchangé. La statue aura **son propre package**
FS2024 pour éviter tout conflit avec `realearth-valmorel-hd`.

## Déposer le fichier Blender

1. Dans Blender, ouvrir le modèle original (.blend).
2. `Fichier > Données externes > Empaqueter les ressources`
   (`File > External Data > Pack Resources`), pour embarquer si possible
   les images des matériaux.
3. `Fichier > Enregistrer sous`, nom : `vierge_saint_maurice.blend`.
4. Sur GitHub, sélectionner la branche `feature/vierge-saint-maurice`.
   Ouvrir ce dossier `statue_saint_maurice/source` et utiliser
   `Add file > Upload files` pour ajouter le `.blend`.
   Si le site refuse la taille du fichier, envoyer le fichier en pièce
   jointe dans la conversation ou pousser par Git depuis le PC.
   Éviter tout fichier >100 Mo sans Git LFS.

**Important :** ne pas déposer des fichiers Blender dans les sources de
Valmorel. Le fichier source restera séparé du package compilé.

## Données nécessaires avant de fixer le placement

- Le **point GPS exact** (latitude, longitude, par exemple un lien de
  coordonnées Google Maps) du **centre de la base du monument**, et non du
  centre-bourg.
- La **dimension réelle approximative** du monument (tour / socle et
  statue, hauteur en mètres).
- Un ou deux **photos** du monument / de son orientation pour faire
  correspondre l'axe du modèle à la réalité.
- Vérifier que le fichier Blender contient le **monument complet** (la
  base en maçonnerie et la statue), pas seulement la figure de la Vierge.

Ne pas confondre le lac de la Madone avec le monument de la Vierge.
Les coordonnées d'un centre-ville, du lac ou d'une randonnée ne
permettent pas de placer précisément la statue dans MSFS.

## Travail prévu après réception du modèle

1. Inspecter les objets Blender, origines, unités, dimensions et matériaux.
2. Exporter le modèle via le plugin Blender du SDK Microsoft Flight Simulator
   2024, avec source glTF / bin et dossier `texture` au singulier.
3. Générer les fichiers de métadonnées `*.png.xml` attendus par le SDK
   pour la conversion de textures en KTX2.
4. Générer le `ModelInfo` avec GUID stable et un XML de placement
   `SceneryObject` aux coordonnées validées, terrain-relative (AGL).
5. Créer un **package indépendant** avec AssetGroup ModelLib + BGL.
6. Compiler sur le PC Windows équipé du SDK, contrôler les BGL/KTX2
   et tester dans MSFS 2024 (orientation, taille, hauteur et textures).

Références officielles :
- https://docs.flightsimulator.com/msfs2024/html/1_Introduction/Using_The_SDK.htm
- https://docs.flightsimulator.com/msfs2024/retail/models-and-textures/plugins/blender-plugin/the-blender-plugins/

La branche et ce document ne constituent **pas** encore un package utilisable
dans le jeu : il manque le modèle Blender et le point GPS confirmé.
