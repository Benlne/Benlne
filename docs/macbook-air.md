# MacBook Air — le poste d'où l'on pilote

Relevé le 12 septembre 2026 par la session locale du MacBook, à la demande de la session web.
Numéro de série, UUID matériel et identifiants de provisionnement volontairement omis : le dépôt
est public.

## 1. Fiche machine

| | |
|---|---|
| Modèle | MacBook Air — Mac16,12 (référence MC6U4FN/A) |
| Puce | Apple M4 — 10 cœurs (4 performance, 6 efficacité) |
| Mémoire | 16 Go, unifiée, non extensible |
| Disque | 460 Go, dont 181 Go libres |
| Système | macOS Tahoe 26.6.2 (build 25G83) |
| Réseau | Wi-Fi ; Ethernet possible par adaptateur USB-C / Thunderbolt |

**La mémoire est son point faible, pas son processeur.** Une mesure du 28 août relevait 82 Mo
libres et 5,7 Go compressés en usage courant ; aujourd'hui, 49 % libres. 16 Go non extensibles
suffisent au pilotage, pas à des modèles de langage locaux ni à des traitements lourds en tâche
de fond : c'est le rôle du futur Mac mini, et en attendant celui de l'iMac pour tout ce qui doit
tourner longtemps.

## 2. Son rôle dans l'architecture

C'est le **poste de pilotage**, pas un nœud de calcul (voir [`architecture.md`](architecture.md)).
Il porte les sessions Claude Code locales, et c'est la seule machine qui voit à la fois ce dépôt,
le NAS et l'iMac.

| Accès | État constaté le 12/09/2026 |
|---|---|
| NAS | partage `homes` monté en `/Volumes/homes`, le même chemin que sur l'iMac |
| iMac, port SSH | **ouvert** depuis l'activation par `launchctl` (voir `CLAUDE.md`) |
| iMac, connexion SSH | **pas encore utilisable par un agent** : aucune clé déposée, et l'iMac n'est pas dans le `known_hosts` du MacBook. La première connexion demande le mot de passe de `tonton` |

Conséquence pratique : tant que `ssh-copy-id tonton@192.168.1.70` n'a pas été fait une fois à la
main, les commandes de la passation « `ssh tonton@192.168.1.70 '…'` » ne peuvent pas être lancées
par une session locale — elles se tapent dans le Terminal de l'iMac, sans le préfixe `ssh`.

## 3. Ce qui a été fait depuis ce poste

- Un scan du partage `benjamin` du NAS, lancé depuis le MacBook, **interrompu à mi-course**
  (101 315 fichiers, 311 Go). Il est **périmé** : l'inventaire final a été fait depuis l'iMac avec
  les index `nas-homes`, `nas-photo` et `nas-video`. Le `~/Inventaire/nas.tsv` partiel du MacBook
  ne doit servir à rien — il est incomplet, et il n'est pas dans ce dépôt.
