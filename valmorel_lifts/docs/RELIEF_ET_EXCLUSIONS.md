# Périmètre strict : télécabines et relief uniquement si vérifié

L'ancien package `realearth-valmorel-hd` incluait des bâtiments modélisés et des exclusions de bâtiments génériques ; l'utilisateur l'a volontairement retiré car son apparence n'était pas satisfaisante. **Ne pas le réinstaller ni le réutiliser intégralement.**

Les fichiers trouvés dans la branche `main`, notamment `scripts/build_scenery.py` et `scripts/build_models.py`, décrivent des placements et des modèles de bâtiments. Les références à RGE ALTI concernent leur élévation d'ancrage ; elles ne prouvent pas l'existence d'une modification autonome du DEM des crêtes.

Le premier package `realearth-valmorel-telecabines` contient donc **ModelLib + BGL de gares seulement**, sans terrain ni autogen exclusion.

Un futur module de relief de Valmorel devra être dans un package propre, avec provenance IGN/licences, limites géographiques, captures comparatives, compilation SDK et QA en jeu. Une amélioration de crêtes ne doit pas écraser les bâtiments ni supprimer la végétation standard.
