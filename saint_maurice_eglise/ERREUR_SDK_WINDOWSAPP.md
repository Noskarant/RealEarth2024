# Diagnostic pour l'erreur fspackagetool.exe (WindowsApps)
Le 5 novembre 2026, le SDK sur le PC de l'utilisateur retourne :
`The given path does not exist: C:\Program Files\WindowsApps\Microsoft.Limitless_1.9.21.0_x64__8wekyb3d8bbwe\FlightSimulator2024.exe`.

Le projet de l'eglise passe la phase de preparation et les 6 tests statiques. L'erreur est produite par le **Package Tool** au moment de lancer la compilation Windows. **Aucun addon Community n'a ete installe ou remplace.**

## Verification sans modification
1. Lancer `DIAGNOSTIC_SDK.bat` depuis le ZIP v0.1.1 (lecture seule).
2. Comparer `Get-AppxPackage -Name Microsoft.Limitless` (version et InstallLocation) avec le chemin signale par fspackagetool.
3. Dans Microsoft Store > Bibliotheque, verifier les mises a jour FS2024, Xbox et Gaming Services.
4. Si necessaire, Windows > Applications > Xbox et Gaming Services > Options avancees > **Reparer**. Ne pas utiliser Reinitialiser sans raison.
5. Ouvrir une fois FS2024, fermer le jeu, et verifier la mise a jour du SDK depuis Aide en mode developpeur.
6. Relancer `INSTALLER_EGLISE.bat` dans le ZIP correctif v0.1.1. En cas d'echec, consulter `DERNIER_JOURNAL_SDK.txt`.

Ne pas modifier les permissions de `C:\Program Files\WindowsApps`, ni effacer les addons Madone/bancs/nature.

**Limite :** ce diagnostic ne corrige pas automatiquement une reference Microsoft Store/Xbox invalide. La recompilation dans le Project Editor de MSFS2024 peut etre envisagee si le SDK en ligne de commande continue a echouer.

Le modele GLB, les textures et l'installateur complet restent dans l'archive privee, hors GitHub public.
