# Contexte pour Claude

Dépôt personnel de Benjamin. Il sert aujourd'hui à une seule chose : faire de l'**iMac 21,5"
de fin 2013** une machine de travail allumée en permanence, sur laquelle Claude Code puisse
tourner, en attendant l'achat d'un Mac mini. **C'est fait depuis le 12/09/2026** — restent les
finitions et le premier usage réel.

Le dépôt est **public** : aucun numéro de série, aucun UUID matériel, aucun secret ne doit y
être écrit.

## À lire avant d'agir

| Document | Contenu |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Où vit quoi. Le dépôt au centre, l'iMac comme nœud de calcul, le NAS comme stockage |
| [`docs/imac-2013.md`](docs/imac-2013.md) | Fiche machine, diagnostic, état d'avancement |
| [`docs/sequoia-oclp.md`](docs/sequoia-oclp.md) | Procédure d'installation de macOS Sequoia via OpenCore Legacy Patcher |

## La machine

iMac14,1 — Core i5-4570R (Haswell, 4 cœurs, 2,7 GHz), 16 Go (maximum du modèle), SSD Samsung
860 EVO 250 Go, Wi-Fi seul. Compte `tonton`, administrateur. FileVault désactivé, SIP actif.

Deux systèmes sur le SSD, et il faut savoir sur lequel on parle :

| Volume | Système | Rôle |
|---|---|---|
| `Sequoia` | macOS Sequoia 15.7.9 (24G830), via OCLP | le système de travail, Claude Code y tourne |
| `MACINTOSH SSD` | macOS Catalina 10.15.8 | le filet de sécurité, intact, démarrable avec alt |

**Le blocage central est levé.** Claude Code exige macOS 13+ et l'iMac14,1 plafonne
officiellement à Catalina : c'est ce qui a motivé tout le reste. OpenCore Legacy Patcher a réglé
la question, root patches compris — accélération graphique et Wi-Fi fonctionnels.

Périphériques : un Hitachi 1 To externe (le disque d'origine de la machine, encore en APFS,
313 Go occupés dont 268 dans `Users`), et un NAS en SMB
(`smb://NasDom._smb._tcp.local/homes`).

## Passation entre surfaces

La conversation vit dans une session Claude Code **web**, sans route vers le réseau de la
maison ; les mains sont dans une session **locale** sur le MacBook Air, qui a le NAS et l'iMac
en SSH mais ne voit pas ce fil. Les deux ne communiquent que par ce dépôt.

**[`docs/passation.md`](docs/passation.md) porte l'état exact, les décisions prises et les
commandes à enchaîner.** C'est le premier fichier à lire pour reprendre le travail.

## Où on en est

Fait : sauvegarde du vieux disque vers le NAS (46,4 Go réellement uniques sur 276 Go inventoriés),
Hitachi 1 To reconverti en cible Time Machine, Sequoia installé via OCLP, root patches appliqués,
Claude Code et Claude Desktop en service sur la machine, réglages d'énergie 24/7.

En cours : donner à l'iMac ses identifiants GitHub (`scripts/imac-github.sh`) — sans quoi la
session qui y tourne peut committer mais pas pousser, et reste donc muette pour les autres
surfaces.

Ensuite : SSH par clé publique seule, Tailscale, `~/Projets` avec un `CLAUDE.md` par projet, et la
première tâche planifiée — par `launchd`, pas `cron` : `launchd` rattrape les exécutions manquées.

## Règles de travail

- **Ne jamais effacer le Hitachi 1 To** tant que `inventaire.py manquants` n'a pas confirmé que
  tout ce qu'il porte existe ailleurs, et que la copie n'a pas été vérifiée par une seconde
  passe de `rsync` qui ne transfère plus rien.
- Les 26 Go de `Users/tilila` ne sont pas ceux de Benjamin : archive séparée à son nom, et
  c'est à elle de décider de ce qui est gardé.
- Les scripts de ce dépôt sont **en lecture seule par défaut** ; ce qui modifie le système
  simule d'abord et exige `--apply`.
- Les scripts se lancent sur l'iMac depuis les URL brutes GitHub, **figées sur un commit** et
  jamais sur la branche : le CDN sert une version périmée pendant plusieurs minutes après un
  push.
- Ne rien acheter pour l'iMac : c'est un bac à sable, tout doit être rejouable sur le Mac mini.
  Ce qui est fait deux fois à la main doit devenir un script du dépôt.
- Écrire en français, y compris les commentaires de code et les messages de commit.

## Pièges de cette machine

- `zsh` n'accepte pas de commentaire en fin de commande collée (`zsh: number expected`), et
  casse sur un script collé au lieu d'être téléchargé.
- `apt` n'existe pas sur macOS ; le `/usr/bin/apt` d'Apple est un outil Java sans rapport.
- Un disque externe en APFS n'apparaît pas dans `diskutil list external physical` : il faut
  passer par les volumes montés et remonter au disque porteur.
- Time Machine sous Catalina exige du HFS+ : il propose de reformater un disque APFS, ce n'est
  pas un défaut du disque.
- `git` et `python3` peuvent répondre « présent » sans être installés (stubs macOS).
- **Les numéros de disque changent d'une session à l'autre.** Le disque externe portant la
  sauvegarde Time Machine a été vu `disk4` puis `disk2` le même jour. Toute consigne qui désigne
  un disque par son numéro est dangereuse : identifier par le **nom du volume**, et relire
  l'identifiant au moment d'agir.
- **OCLP doit être installé sur le système qu'il patche, et lancé depuis lui.** Lancé depuis un
  autre volume, `Start Root Patching` échoue sur un `FileNotFoundError` visant son assistant
  privilégié — avec un message qui laisse croire à un problème de téléchargement de
  `MetallibSupportPkg`.
- **Activer SSH sur cette machine ne marche ni par la case à cocher ni par `systemsetup`.** La
  case « Session à distance » du panneau Partage reste bloquée sur « Démarrage… » sans jamais
  charger le service, et `sudo systemsetup -setremotelogin on` est refusé faute d'« Accès
  complet au disque » pour le Terminal. Ce qui fonctionne :
  ```bash
  sudo launchctl enable system/com.openssh.sshd
  sudo launchctl load -w /System/Library/LaunchDaemons/ssh.plist
  nc -z 127.0.0.1 22 && echo "sshd écoute"
  ```
  Diagnostiquer en testant `127.0.0.1` avant l'adresse du réseau : cela sépare « le service ne
  tourne pas » de « le réseau bloque ».
