# Critères d'acceptation — Saint-Maurice-sur-Dargoire ULTRA 3 km

**Pas de statut « prêt en jeu » sans compilation SDK et test visuel.**

1. Périmètre : 3000 m en Lambert-93 depuis `config.json`, couverture complète 28,27 km².
2. Bâtiments : tous les emplacements IGN disponibles dans ce rayon, inventaire, provenance hauteur, cour intérieure, toitures.
3. Orthophoto : nombre de tuiles et progression dans `orthophoto_IGN_report.json`, pas de carré manquant, transition alpha sans couture.
4. Végétation : zones boisées seulement là où l'IGN les connaît, aucune collision avec les disques de l'église ou la Madone ; jardins et prairies conservés.
5. Relief : étudier le MNT/MNS LiDAR 50 cm avant toute modification du terrain ; pas d'altitudes IGN69 copiées directement comme WGS84 ellipsoïde.
6. SDK : compilation BGL/ModelLib/CGL sans erreur, textures KTX2 présentes et visibles, géométries correctement orientées.
7. Vols de contrôle : bourg, Madone du Peu, hameaux à 1–3 km, vue oblique 200 et 500 m au-dessus du sol ; comparer avec le jeu natif.
8. Performances : pas de chute de FPS disproportionnée sur RTX 4070, pas de bâtiments flottants, pas de superposition avec décor natif.
9. Monuments : **aucun fichier original modifié**, bâtiments/arbres du nouveau mod absents des emplacements réservés, anciens modèles conservés.
10. Dernière passe : corriger les formes de toiture les plus visibles et les points de repère après comparaison avec des photographies légalement exploitables.

La compilation dans le SDK ne garantit ni le rendu final, ni la présence de données LiDAR; l'intégration doit être inspectée en vol.
