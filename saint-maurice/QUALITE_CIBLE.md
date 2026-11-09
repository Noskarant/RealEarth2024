# Qualité visée et ce qui manque nécessairement pour « j'y suis »

1. **Vue de 100 à 1 000 m AGL** : amélioration la plus solide via vrais bâtiments IGN et orthophoto couvrant 3 km. Contrôler les raccords, les textures et l'absence de doublons.
2. **Vue de 20 à 100 m AGL** : l'aspect des façades nécessite **des photos ou un scan 3D** bâtiment par bâtiment. Les fenêtres générées automatiquement ne sont que des estimations. Ne pas les présenter comme des copies fidèles.
3. **Relief** : MNT/MNS IGN LiDAR HD utiles pour quantifier la forme des collines. Le remplacement automatique de l'élévation du simulateur n'est pas encore un flux exploitable/validé dans cette édition du SDK. Ne pas superposer un maillage DEM fixe de 28 km² sans raccords et tests : risque majeur de relief flottant et de conflits avec les routes.
4. **Végétation** : les polygones IGN reconstituent la trame des boisements. Les arbres isolés peuvent être relevés dans OSM, mais les vrais objets Tree requièrent des GUID du SDK réellement installés.
5. **Église et Madone** : modèles existants laissés intacts ; le nouveau décor est généré hors des zones interdites. Vérifier leurs coordonnées GPS réelles dans les packages locaux avant le premier vol.
6. **Performances** : mesurer dans le DevMode FS2024, avec RTX 4070/12 Go VRAM : FPS, temps de chargement, draw calls, texture budget et nombre d'objets. Adapter la taille des clusters et les LOD seulement à partir de ces observations.

**Preuve d'achèvement exigée :** build SDK sans erreur + package Community installable + 4 captures comparatives A/B depuis exactement la même position, heure et météo + contrôle à 100, 300 et 800 m d'altitude AGL + contrôle de 3 hameaux + église et Madone sans doublon.
