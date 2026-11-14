# Correctif V0.3 — échec de compilation ModelLib (14 novembre 2026)

L'écran du SDK indique **30 commandes effectuées, 3 échouées**, avec erreur générique `PackageBuilder::_EndTreatCommands`. Les avertissements `ASOBO_normal_map_convention` ne sont pas des erreurs bloquantes en soi.

## Défaut concret détecté dans les sources

Trois textures PNG des inscriptions / logos, extraites des GLB fournis, étaient au format **3935 × 1070** :

- `valmorel_planchamp_cabine_type_a_00.png`
- `valmorel_planchamp_gare_amont_02.png`
- `valmorel_planchamp_gare_aval_02.png`

Or le SDK MSFS 2024 demande des côtés **multiples de 4 pixels**, au moins 8 × 8 :
https://docs.flightsimulator.com/msfs2024/retail/models-and-textures/textures/texturing-technical-information/

La concordance entre **3 textures non conformes et 3 commandes échouées** est un indice fort, **pas encore une preuve absolue** : le premier message d'erreur SDK détaillé n'a pas été fourni.

## Correction

Les textures sont désormais **3936 × 1072**. Padding d'un pixel à droite et deux pixels en bas par prolongation de la bordure (aucun pixel d'origine modifié, UV presque identiques). Les trois PNG corrigés sont fournis dans l'archive V0.3, sous `assets/texture_overrides/` ; le script `prepare_sdk.py` utilise ces fichiers et échoue explicitement si un atlas non conforme n'a pas de remplacement valide.

L'archive V0.3 a été validée localement pour **8 GLB sources, 11 textures PNG conformes, 4 gares de prévisualisation**. Les binaires de modèles et le master Blender restent identiques. Les bâtiments de station et le relief ne sont pas inclus.

**Relancer le lanceur Windows avec FS2024 fermé** après extraction V0.3 dans `D:\RealEarth2024\`. Le SDK officiel doit encore compiler ce package sur le PC de l'utilisateur.

Si erreur persistante : envoyer le **premier** message `ERROR` ou `Failed` visible **avant** `_EndTreatCommands`, et pas seulement la synthèse finale. Ne pas installer de package partiellement compilé.
