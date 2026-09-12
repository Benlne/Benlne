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

`Users/tilila` (25,8 Go) n'appartient pas à Benjamin : archive séparée sous
`Save disque imac/tilila/`, et c'est à elle de décider de ce qui est gardé. Pour son compte on
ne trie pas — on prend tout **sauf `Library` (14,6 Go) et `.wdc` (807 Mo)**, soit environ 10 Go.
Deux dossiers à ne surtout pas perdre : `Zotero` (737 Mo, sa bibliothèque de références) et
`Thèse gardes.nvpx`.

Total provisoire, avant confrontation au NAS : **~75 Go pour `laine`, ~10 Go pour `tilila`**.

## Ce qui est déjà sur le NAS

- `Save disque imac/` — créé le 12/09/2026 à 09:32, **vide**. Aucune copie n'a encore eu lieu.
- `Archives IMAC/laine/` — une archive plus ancienne du même iMac, couvrant 2020-2022. Elle
  doit impérativement être incluse dans l'index `nas`, puisqu'elle réduira d'autant la liste
  des fichiers à copier.

## Le verdict de l'inventaire — 12/09/2026

Quatre index confrontés : `imac-2013` (le vieux disque), `imac-actuel`, et trois partages du
NAS — `nas-homes`, `nas-photo`, `nas-video`.

| | |
|---|---|
| Total sur le vieux disque (`Users`) | 265,5 Go |
| Déjà en sécurité ailleurs | **90,9 Go** — inutile de les copier |
| Écartés volontairement | **128,2 Go** |
| **À copier** | **46,4 Go, 6 120 fichiers** |

Écarté : `/laine/Music/`, `/Dropbox/`, `/Library/`, `/Downloads/`, `/.wdc/`, `/.dropbox/`,
`/.cache/`, `/Google Drive/`, les extensions `.mkv .avi .dmg .iso .img`, et les dossiers
`/Film : Cinéma/` et `Torrent9`. Les extensions `.mp4` et `.mov` sont **délibérément
conservées** : c'est là que vivent les vidéos de famille et les rushes du mariage, alors que
`.mkv` et `.avi` ne portent ici que des téléchargements.

Le scan des partages `photo` et `video` du NAS a été décisif : sans eux, 90,9 Go auraient été
recopiés pour rien.

Reste dans ces 46,4 Go une duplication interne aux trois bibliothèques photo — le même `.mov`
présent dans `Photos.photoslibrary`, `iPhoto.photoslibrary` et `iPhoto.migratedphotolibrary`.
On ne la traite pas maintenant : `manquants` compare la source aux références, pas la source à
elle-même, et surtout le tri des bibliothèques photo se fera plus tard, une fois la copie en
sécurité. Mieux vaut archiver 15 Go de trop que perdre un original référencé.

## Ce qui reste à faire, dans l'ordre

1. **Indexer le NAS** — c'est la pièce manquante, sans elle `manquants` n'a rien à comparer.
   Viser le dossier qui porte déjà les sauvegardes, pas toute la racine : le parcours SMB coûte
   un aller-retour réseau par dossier.
   ```bash
   ssh tonton@192.168.1.70 'python3 ~/inventaire.py scan "/Volumes/homes/benjamin" --nom nas'
   ```
   Le scan peut aussi se faire depuis le MacBook, où le partage est monté : `manquants` compare
   par taille et par nom, jamais par chemin, donc un index construit là-bas vaut celui construit
   sur l'iMac. Il faudra seulement **recopier `nas.tsv` dans le `~/Inventaire` de l'iMac**, car
   c'est là que vivent les deux autres index et que `manquants` les lit.
2. **Établir la liste réelle à copier**, en excluant les dossiers écartés ci-dessus.
   ```bash
   ssh tonton@192.168.1.70 'python3 ~/inventaire.py manquants imac-2013 \
       --reference nas imac-actuel \
       --racine "/Volumes/Macintosh HD/Users" --liste-rsync ~/a-copier.txt'
   ```
   Puis retirer de `~/a-copier.txt` les chemins sous `laine/Music`, `laine/Dropbox`,
   `laine/Library` et `laine/Downloads`.
3. **Copier**, depuis l'iMac, vers le dossier que Benjamin a créé sur le NAS :
   `/Volumes/homes/benjamin/Save disque imac`, avec un sous-dossier par compte —
   `laine/` et `tilila/`. C'est la destination qui fait foi ; toute mention d'un autre chemin
   ailleurs dans ce dépôt est une erreur de rédaction.
   ```bash
   ssh tonton@192.168.1.70 'bash ~/copie-vers-nas.sh --liste ~/a-copier.txt \
       "/Volumes/Macintosh HD/Users" "/Volumes/homes/benjamin/Save disque imac"'
   ```
   Lancer dans un `nohup` ou un `screen` pour que la copie survive à la fin de la session SSH.
4. **Vérifier** : relancer exactement la même commande. Si elle ne transfère plus rien, les deux
   côtés sont identiques. **C'est la seule preuve acceptable avant l'étape suivante.**
5. **Reformater le 1 To** en HFS+ et lancer la première sauvegarde Time Machine de l'iMac.
6. Enchaîner sur [`docs/sequoia-oclp.md`](sequoia-oclp.md).

## La copie est faite et vérifiée — 12/09/2026

- Première passe : **49 777 121 868 octets transférés, aucune erreur**, environ une heure à
  13,5 Mo/s en Wi-Fi.
- Seconde passe, la seule qui vaut preuve : **748 Ko envoyés, aucun fichier listé, `speedup`
  de 66 483**. Les deux côtés sont identiques.

Les 46,4 Go sont en sécurité dans `/Volumes/homes/benjamin/Save disque imac`, répartis en
`laine/` et `tilila/`.

## La question de `Music` est tranchée — le formatage est autorisé

**La collection est déjà sur le NAS**, dans `Archives IMAC/laine/Music/`, l'archive de
2020-2022. Vérifié fichier par fichier :

```
[imac-2013]  1019.6 Mo  .../laine/Music/Bibliothèque musicale/Jazz/Miles Davis -  Bitches Brew 1970 /B1 - Bitches Brew.flac
[nas-homes]  1019.6 Mo  /Volumes/homes/benjamin/Archives IMAC/laine/Music/Bibliothèque musicale/Jazz/M9IIZA~W/B1 - Bitches Brew.flac
```

Les chiffres le confirment à l'échelle du volume : en retirant `/laine/Music/` des exclusions,
les 126,6 Go ne sont pas passés dans « écartés » mais dans « déjà ailleurs », qui saute de
90,9 à 217,4 Go.

**Une réserve, sans gravité pour les données.** Le dossier `Miles Davis -  Bitches Brew 1970 `
est devenu `M9IIZA~W` sur le NAS : espaces doubles et espace final que le partage n'a pas su
écrire, d'où un nom court fabriqué. Les fichiers sont intacts, quelques noms de dossiers
d'albums sont illisibles. C'est une perte de rangement, réparable à froid.

### Ce que le formatage détruira, en connaissance de cause

| | |
|---|---|
| `laine/Music` | 126,6 Go — **déjà sur le NAS**, aucune perte |
| `Dropbox` (les deux comptes) | 27 Go — dans le cloud, aucune perte |
| Films, séries, `Downloads`, caches, `.wdc` | sans regret |
| `laine/Library` | 22,3 Go — **perte réelle mais assumée**, dont d'anciennes sauvegardes d'iPhone dans `MobileSync/Backup` |
| `tilila/Library` | 14,6 Go — idem |

Le seul poste qui disparaît vraiment est `Library`. Si une vieille sauvegarde d'iPhone comptait,
c'est le moment de le dire ; sinon le disque peut être formaté.

## Le 1 To est devenu la cible Time Machine — 12/09/2026

Le disque a été formaté et la première sauvegarde lancée. À partir de là, l'iMac a une
sauvegarde système complète, et la phase d'installation de Sequoia peut commencer.

**Le profil de risque a changé, et dans le mauvais sens.** Le Hitachi ne porte plus des données
dupliquées ailleurs : il porte désormais **la seule sauvegarde système de la machine**. Or
l'étape suivante consiste précisément à désigner un disque à effacer, pour y écrire l'installeur
Sequoia.

**Quand OCLP demandera sur quel disque écrire l'installeur : ce sera la clé USB de 16 Go, jamais
le Hitachi 1 To.** Relire le nom et la taille affichés avant de valider. Une confusion à cette
étape détruit la sauvegarde au moment précis où elle protège l'opération.

## Interdits

- **Le Hitachi 1 To porte maintenant la sauvegarde Time Machine.** Il ne doit plus jamais être
  désigné comme cible d'un effacement — en particulier pas à OCLP, qui demandera un disque pour
  y écrire l'installeur Sequoia. Ce disque-là, c'est la clé USB de 16 Go.
- **Ne jamais pousser `~/Inventaire/*.tsv` dans ce dépôt** : ces fichiers listent le chemin de
  183 000 fichiers personnels, et le dépôt est public.
- Ne pas proposer d'installer Claude Code ou Claude Desktop sur l'iMac : il est sous Catalina,
  le minimum est macOS 13.
- Ne rien acheter pour l'iMac.

## Pour rendre la main

Ce qui est décidé ou découvert s'écrit ici ou dans `docs/imac-2013.md`, et se pousse sur la
branche `claude/imac-hardware-info-bc2vlq`. C'est par là que la session web en prendra
connaissance — elle ne voit rien d'autre.
