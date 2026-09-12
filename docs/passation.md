# Passation à la session locale du MacBook Air

Ce fichier existe parce que la conversation et les mains ne sont pas au même endroit. Le fil de
discussion vit dans une session Claude Code **web**, qui n'a aucune route vers le réseau de la
maison. La session **locale** du MacBook Air, elle, a le NAS en SMB et l'iMac en SSH — mais ne
sait rien de ce fil. Le dépôt est le seul canal qui traverse les deux.

Lire d'abord [`CLAUDE.md`](../CLAUDE.md), puis [`docs/architecture.md`](architecture.md).

## Accès

| Quoi | Comment |
|---|---|
| iMac | `ssh tonton@192.168.1.70` — compte administrateur, macOS Catalina 10.15.8 |
| NAS | `smb://NasDom._smb._tcp.local/homes`, monté en `/Volumes/homes` |
| Vieux disque | branché **sur l'iMac**, monté en `/Volumes/Macintosh HD` (externe, APFS, 313 Go) |

Le vieux disque est physiquement sur l'iMac : toute copie doit être **lancée sur l'iMac** et
écrire directement vers le NAS. Ne pas faire transiter 75 Go par le MacBook.

## Ce qui est déjà fait

- Réglages d'énergie 24/7 appliqués sur l'iMac (plus de veille, redémarrage après coupure).
- Command Line Tools installés, vérifications préalables au vert, zéro point bloquant.
- Index du dossier personnel actuel de l'iMac : 53 077 fichiers, 37,5 Go (`imac-actuel`).
- Index du vieux disque : 183 058 fichiers, 275,9 Go (`imac-2013`).

Les index sont dans `~/Inventaire/*.tsv` **sur l'iMac**, et se lisent avec
`scripts/inventaire.py` (`liste`, `dossiers`, `chercher`, `manquants`, `doublons`).

## Décisions déjà prises

| Dossier de `Users/laine` | Poids | Décision |
|---|---|---|
| `Music` | 126,6 Go | **écarté** — décision de Benjamin |
| `Dropbox` | 24,5 Go | **écarté** — déjà dans le cloud |
| `Library` | 22,3 Go | **écarté** — caches et préférences d'un système mort |
| `Downloads` | 2,5 Go | écarté sauf surprise |
| `Documents` + `Desktop` + `Movies` | ~31 Go | **à copier** |
| `Pictures` | 42,6 Go | **à copier en entier pour l'instant** |

Sur `Pictures` : trois bibliothèques se recouvrent — `Bibliothèque Photos.photoslibrary`
(17,3 Go, celle en service), `Bibliothèque iPhoto.migratedphotolibrary` (9,3 Go) et
`Bibliothèque iPhoto.photoslibrary` (8,3 Go). Ne pas trancher maintenant : selon la façon dont
la migration s'est faite, Photos peut *référencer* des originaux restés dans l'ancienne
bibliothèque. On copie tout, on triera en ouvrant les deux.

`Users/tilila` (26 Go) n'appartient pas à Benjamin : archive séparée à son nom, et c'est à elle
de décider de ce qui est gardé.

Total provisoire à copier : **~75 Go**, avant confrontation au NAS.

## Ce qui reste à faire, dans l'ordre

1. **Indexer le NAS** — c'est la pièce manquante, sans elle `manquants` n'a rien à comparer.
   Viser le dossier qui porte déjà les sauvegardes, pas toute la racine : le parcours SMB coûte
   un aller-retour réseau par dossier.
   ```bash
   ssh tonton@192.168.1.70 'python3 ~/inventaire.py scan "/Volumes/homes/benjamin" --nom nas'
   ```
2. **Établir la liste réelle à copier**, en excluant les dossiers écartés ci-dessus.
   ```bash
   ssh tonton@192.168.1.70 'python3 ~/inventaire.py manquants imac-2013 \
       --reference nas imac-actuel \
       --racine "/Volumes/Macintosh HD/Users" --liste-rsync ~/a-copier.txt'
   ```
   Puis retirer de `~/a-copier.txt` les chemins sous `laine/Music`, `laine/Dropbox`,
   `laine/Library` et `laine/Downloads`.
3. **Copier**, depuis l'iMac, vers `Archives/imac-2013-09-2026/` sur le NAS.
   ```bash
   ssh tonton@192.168.1.70 'bash ~/copie-vers-nas.sh --liste ~/a-copier.txt \
       "/Volumes/Macintosh HD/Users" "/Volumes/homes/benjamin/Save disque imac"'
   ```
   Lancer dans un `nohup` ou un `screen` pour que la copie survive à la fin de la session SSH.
4. **Vérifier** : relancer exactement la même commande. Si elle ne transfère plus rien, les deux
   côtés sont identiques. **C'est la seule preuve acceptable avant l'étape suivante.**
5. **Reformater le 1 To** en HFS+ et lancer la première sauvegarde Time Machine de l'iMac.
6. Enchaîner sur [`docs/sequoia-oclp.md`](sequoia-oclp.md).

## Interdits

- **Ne jamais effacer le Hitachi 1 To** avant que l'étape 4 ait été faite et constatée.
- **Ne jamais pousser `~/Inventaire/*.tsv` dans ce dépôt** : ces fichiers listent le chemin de
  183 000 fichiers personnels, et le dépôt est public.
- Ne pas proposer d'installer Claude Code ou Claude Desktop sur l'iMac : il est sous Catalina,
  le minimum est macOS 13.
- Ne rien acheter pour l'iMac.

## Pour rendre la main

Ce qui est décidé ou découvert s'écrit ici ou dans `docs/imac-2013.md`, et se pousse sur la
branche `claude/imac-hardware-info-bc2vlq`. C'est par là que la session web en prendra
connaissance — elle ne voit rien d'autre.
