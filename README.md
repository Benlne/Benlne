# Bac à sable perso

Dépôt de travail personnel. Le projet d'analyse EuroMillions qui occupait ce dépôt était une
expérience : il a été retiré, son historique reste dans les commits antérieurs et sur la
branche `claude/euromillion-probabilites-ijasp0`.

## Contenu actuel

| Chemin | Rôle |
|---|---|
| [`docs/imac-2013.md`](docs/imac-2013.md) | Fiche machine + plan pour transformer l'iMac 21,5" de fin 2013 en machine de travail allumée en permanence |
| [`scripts/imac-preflight.sh`](scripts/imac-preflight.sh) | État des lieux de l'iMac, en lecture seule, sans numéro de série ni UUID dans la sortie |
| [`scripts/imac-24-7.sh`](scripts/imac-24-7.sh) | Réglages « jamais de veille, redémarre seul après coupure », en mode simulation par défaut |

## Le point de départ

L'iMac (iMac14,1, fin 2013) plafonne officiellement à **macOS Catalina 10.15.7**, alors que
Claude Code demande **macOS 13 ou plus récent**. C'est la raison exacte de l'échec
d'installation, et `docs/imac-2013.md` décrit les deux façons d'en sortir : passer la machine
sous macOS Sequoia avec OpenCore Legacy Patcher, ou faire tourner l'agent dans une machine
virtuelle Linux sans toucher à macOS.
