# Installer macOS Sequoia sur l'iMac14,1 avec OpenCore Legacy Patcher

Procédure pas à pas pour cette machine précise : iMac14,1, SSD interne Samsung 860 EVO 250 Go,
Catalina 10.15.8, FileVault désactivé, compte administrateur, clé USB de 16 Go disponible.

**Pas de sauvegarde Time Machine** : le filet de sécurité est le volume Catalina, laissé intact
et démarrable pendant toute l'opération. Lire la section « Risques » avant de commencer.

Durée : 2 à 3 heures, dont une heure de téléchargement. Prévoir de ne pas être pressé.

## 0. Risques, en clair

Ce qui **ne touche pas** aux données existantes :

- ajouter un volume APFS dans le conteneur (les volumes partagent l'espace, rien n'est
  repartitionné) ;
- écrire OpenCore dans la partition EFI `disk0s1` (partition de démarrage, 210 Mo, vide de
  données) ;
- installer Sequoia sur le nouveau volume.

Ce qui peut réellement mal tourner :

| Risque | Probabilité | Parade |
|---|---|---|
| Erreur de manipulation dans Utilitaire de disque (effacer le mauvais volume) | faible mais réelle | Lire deux fois le nom du volume avant de valider. Ne jamais toucher à `MACINTOSH SSD` ni à `Container disk1` lui-même |
| Sequoia inutilisable après patches (graphismes, Wi-Fi) | modérée | Redémarrer sur Catalina avec <kbd>alt</kbd>, tout est resté en place |
| Disque plein pendant l'installation | modérée (250 Go pour deux systèmes) | Vérifier 60 Go libres avant de commencer |
| Panne du SSD pendant l'opération | très faible | Aucune. C'est le risque accepté faute de sauvegarde |

**Avant de commencer**, copier sur la clé USB ou dans un cloud tout ce qui serait irremplaçable
(photos, documents). `scripts/imac-pre-sequoia.sh` affiche le poids des dossiers personnels
pour savoir de quoi on parle. Dix minutes qui suppriment le seul vrai regret possible.

En dernier recours, Catalina se réinstalle depuis la récupération Internet
(<kbd>cmd</kbd>+<kbd>alt</kbd>+<kbd>R</kbd> au démarrage) : le volume `Recovery` est toujours
là, et ce modèle récupère son système d'origine depuis les serveurs d'Apple.

## 1. Vérifications préalables

```bash
curl -fsSL https://raw.githubusercontent.com/Benlne/Benlne/claude/imac-hardware-info-bc2vlq/scripts/imac-pre-sequoia.sh | bash
```

Le script ne modifie rien. Il vérifie les droits d'administration, l'espace libre, les Command
Line Tools, la présence de la clé USB, et affiche le poids des dossiers personnels à mettre à
l'abri. Il conclut par un feu vert ou rouge.

## 2. Créer le volume `Sequoia`

Dans **Utilitaire de disque** (Applications → Utilitaires) :

1. Menu **Présentation → Afficher tous les appareils**. Sans ça, le conteneur n'apparaît pas.
2. Sélectionner **`Container disk1`** dans la colonne de gauche (pas `MACINTOSH SSD`, pas
   `disk0`).
3. Cliquer sur **+** (Ajouter un volume APFS).
4. Nom : `Sequoia`. Format : **APFS**. Ne pas cocher de quota.
5. Ajouter.

Le volume apparaît immédiatement, de taille nulle : c'est normal, les volumes APFS prennent
l'espace au fur et à mesure. Rien d'autre n'a bougé.

## 3. Récupérer OpenCore Legacy Patcher

1. Aller sur la page des *releases* de `dortania/OpenCore-Legacy-Patcher`, version **2.5.0**.
2. Télécharger **`OpenCore-Patcher-GUI.app.zip`**.
3. Décompresser, déplacer l'app dans **Applications**.
4. Premier lancement : si macOS refuse d'ouvrir l'app, **clic droit → Ouvrir**, puis confirmer.

## 4. Créer l'installeur Sequoia sur la clé USB

Dans OCLP :

1. **Create macOS Installer** → **Download macOS Installer**.
2. Choisir la dernière **macOS Sequoia 15.x**. Le téléchargement fait environ 15 Go — c'est la
   partie longue, surtout en Wi-Fi.
3. Une fois terminé, OCLP propose d'écrire l'installeur sur un disque : choisir la clé USB.
   **Son contenu est effacé.**
4. Saisir le mot de passe administrateur quand il est demandé. L'écriture prend 20 à 30 minutes.

> Si l'écriture échoue avec une erreur de `createinstallmedia`, c'est la limite connue d'un
> installeur récent lancé depuis Catalina. Contournement : créer la clé depuis un Mac plus
> récent, ou depuis le Sequoia une fois installé — mais dans ce cas il faut d'abord réussir
> l'installation par un autre chemin. Me le signaler, on reprendra là-dessus.

## 5. Installer OpenCore sur le disque interne

Toujours dans OCLP :

1. **Build and Install OpenCore**.
2. OCLP détecte `iMac14,1` tout seul — vérifier que c'est bien ce qui s'affiche.
3. **Build OpenCore**, puis **Install to disk**.
4. Choisir le disque **`disk0`**, puis la partition **EFI `disk0s1`**.
5. Redémarrer quand OCLP le propose.

À ce stade, rien n'est encore installé comme système : OpenCore est juste un chargeur de
démarrage posé à côté. Catalina démarre toujours normalement.

## 6. Installer Sequoia

1. Redémarrer en maintenant <kbd>alt</kbd> jusqu'au sélecteur de démarrage.
2. Choisir **EFI Boot** (icône OpenCore). Le sélecteur d'OpenCore s'affiche ensuite.
3. Choisir **Install macOS Sequoia** (la clé USB).
4. Dans l'installeur, choisir le volume **`Sequoia`** comme destination. **Vérifier le nom
   deux fois.**
5. L'installation redémarre la machine plusieurs fois. À chaque redémarrage, si le sélecteur
   Apple apparaît, reprendre **EFI Boot** ; le sélecteur OpenCore poursuit ensuite tout seul.
6. Créer le compte utilisateur quand l'installeur le demande — un compte administrateur.

## 7. Appliquer les root patches

C'est l'étape qui fait fonctionner les graphismes. Sans elle, l'interface est saccadée.

1. Sur le Sequoia fraîchement installé, OCLP se relance en général tout seul et propose le
   patch. Sinon, réinstaller l'app OCLP et ouvrir **Post-Install Root Patch**.
2. **Start Root Patching**. Pour le Iris Pro 5200 (Haswell), OCLP télécharge et installe
   `MetallibSupportPkg` : connexion Internet nécessaire.
3. Redémarrer.
4. Vérifier : les animations sont fluides, « À propos de ce Mac » affiche Sequoia, le Wi-Fi
   fonctionne.

## 8. Finitions

1. **Disque de démarrage** : Réglages Système → Général → Disque de démarrage → `Sequoia`.
2. **Mises à jour automatiques : désactiver.** Réglages Système → Général → Mise à jour de
   logiciels → Mises à jour automatiques → tout désactiver. Chaque mise à jour de macOS efface
   les root patches ; elles se font à la main, en gardant une demi-heure devant soi pour
   relancer OCLP juste après.
3. **Réglages 24/7** :
   ```bash
   curl -fsSLo ~/imac-24-7.sh https://raw.githubusercontent.com/Benlne/Benlne/claude/imac-hardware-info-bc2vlq/scripts/imac-24-7.sh
   bash ~/imac-24-7.sh --apply
   ```
4. **Claude Code** :
   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   claude
   ```
5. **SSH** : Réglages Système → Général → Partage → Session à distance, puis clé publique
   uniquement.
6. **Ethernet** si possible, plutôt que le Wi-Fi, pour une machine joignable en permanence.

## 9. Si ça tourne mal

| Symptôme | Réponse |
|---|---|
| Sequoia ne démarre pas | Redémarrer avec <kbd>alt</kbd>, choisir `MACINTOSH SSD` : Catalina revient, intact |
| Interface saccadée, fenêtres lentes | Root patches non appliqués ou effacés par une mise à jour : relancer OCLP → Post-Install Root Patch |
| Plus de Wi-Fi après mise à jour | Même cause, même réponse |
| Le sélecteur OpenCore n'apparaît plus | Redémarrer avec <kbd>alt</kbd> → EFI Boot. Si l'entrée a disparu, refaire l'étape 5 depuis Catalina |
| Tout annuler | Démarrer sur Catalina, supprimer le volume `Sequoia` dans Utilitaire de disque, et effacer le dossier `EFI/OC` de la partition EFI |

Dans tous les cas : Catalina reste démarrable tant que son volume n'a pas été touché. C'est le
point sur lequel toute cette procédure est construite.
