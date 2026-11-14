# Correctif V0.6.2 — installation sans recompilation (14 novembre 2026)

Après le test V0.6.1 sur Windows, l'utilisateur voit :
- `Validation SUCCESS`
- `PackageBuilder Finished, 0 skipped, 37 done and 0 failed`
- la console demeure bloquée sans confirmation d'installation.

Le SDK a compilé correctement les modèles et le BGL, mais le processus du lanceur ne s'est pas terminé. **Le package V0.6.1 n'est pas confirmé installé**.

Le correctif autonome `CORRECTIF_VALMOREL_V062_SANS_RECOMPILER.zip` a été préparé en conversation. Il inclut un script PowerShell install-only, indépendant du SDK, qui :

1. Localise `D:\RealEarth2024\VALMOREL_TELECABINES_V061_CORRECTIF_COMPILATION\valmorel_lifts\project\Packages\realearth-valmorel-telecabines`.
2. Vérifie la stabilité des fichiers, le manifest `0.1.1`, le layout, **1 BGL ModelLib, 1 BGL placements et 11 KTX2 minimum**, les tailles et signatures.
3. Vérifie que l'XML source comporte au moins 70 placements et l'exclusion ciblée de Pierrafort amont (pour éviter une régression à V0.5).
4. Copie le seul package dans le Community de FS2024, après sauvegarde et avec restauration en cas d'échec.

Le script n'appelle pas le SDK, ne fait aucun accès/écriture à WindowsApps et ne touche pas à l'ancien `realearth-valmorel-hd`.

**Statut de validation :** archive ZIP et scripts générés/inspectés hors Windows. Pas de test SDK, PowerShell 5.1 ni rendu en jeu sur la machine de l'utilisateur. Si l'état du build n'est pas conforme, aucun remplacement de la V0.5 n'a lieu.

Documentation SDK : https://docs.flightsimulator.com/msfs2024/
