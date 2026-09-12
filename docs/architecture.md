# Architecture : où vit quoi

Note d'architecture pour le poste de travail personnel permanent. Elle répond à une intention :
pouvoir agir sur les projets perso depuis n'importe où — iPhone, MacBook Air, PC du bureau — et
disposer d'une machine à demeure qu'un agent peut piloter.

## 1. Le centre n'est pas la machine, c'est le dépôt

L'intuition naturelle est de faire de l'iMac le centre de gravité : tout y vit, on s'y connecte
de partout. C'est une erreur de conception, pour une raison simple : **une machine de 2013,
en Wi-Fi, sous un macOS rustiné, ne peut pas être une dépendance dure**. Un disque qui lâche,
une mise à jour qui casse les patches OpenCore, une coupure de courant pendant les vacances, et
tout devient inaccessible.

Le centre, c'est **GitHub**. Un dépôt par projet, et c'est lui qui rend un projet joignable de
partout, par n'importe quel agent, que l'iMac soit allumé ou non.

L'iMac devient alors ce qu'il doit être : **un environnement d'exécution parmi deux**, celui qui
sait faire ce que le cloud ne sait pas.

> **Le test de conception** : si l'iMac meurt cette nuit, qu'est-ce qui est perdu ?
> La bonne réponse est « une après-midi de réinstallation, rien d'autre ». Tant que c'est vrai,
> l'architecture est saine. Dès qu'un projet ne vit que sur l'iMac, elle ne l'est plus.

## 2. Répartition des rôles

| | Sessions cloud (claude.ai/code) | iMac |
|---|---|---|
| Joignable depuis | n'importe quel navigateur, sans rien installer | Tailscale ou réseau local |
| Disponibilité | toujours | dépend d'une machine de 13 ans |
| État entre deux sessions | aucun, conteneur neuf à chaque fois | **permanent** |
| Accès au NAS et au réseau local | non | **oui** |
| Processus longs, services, tâches planifiées | non | **oui** |
| Données qui ne doivent pas sortir de la maison | non | **oui** |
| Coût du calcul | facturé au plan | gratuit, la machine tourne déjà |

**Règle d'usage** : tout ce qui est « lire et modifier un dépôt » se fait en session cloud, y
compris depuis l'iPhone. L'iMac sert à ce que cette liste-là ne couvre pas.

## 3. Ce que l'iMac apporte vraiment

C'est la partie « un ordinateur à disposition de l'agent », et elle a quatre usages concrets :

1. **La mémoire longue.** Bases de données locales, caches, historiques, gros fichiers de
   travail qui n'ont pas leur place dans un dépôt git.
2. **Les tâches planifiées sans humain devant.** Claude Code en mode non interactif
   (`claude -p "..."`) dans une tâche planifiée : la nuit, il tire les dépôts, lance les tests,
   ouvre une pull request quand quelque chose casse. C'est ça, l'agent avec une machine.
3. **Le réseau local.** Le NAS, les fichiers de la maison, les services internes — inaccessibles
   depuis un conteneur cloud, triviaux depuis l'iMac.
4. **Les données qui ne doivent pas quitter la maison.** Tout traitement sensible s'exécute ici
   et n'en sort pas.

Ce que l'iMac ne fera pas : modèles de langage en local (pas de GPU exploitable, 16 Go non
extensibles), compilations très lourdes, et tout ce qui exige Windows.

## 3 bis. NAS et iMac : le stockage d'un côté, le calcul de l'autre

Les scripts de scraping tournaient sur le NAS. Ils passent sur l'iMac, et c'est le bon sens :

- un CPU de NAS ne fait pas tourner **un navigateur headless**, et sans Chromium on ne récupère
  rien d'une page qui se rend en JavaScript — c'est la limite décisive, pas la puissance brute ;
- quatre cœurs Haswell, 16 Go et un SSD encaissent plusieurs workers en parallèle ;
- un vrai Python et un vrai gestionnaire de paquets, au lieu des contraintes d'un système de NAS.

Le NAS ne disparaît pas du schéma, il **redevient ce qu'il fait de mieux** : du stockage durable
et redondant. L'iMac calcule, le NAS conserve.

Trois règles qui découlent de ce partage :

1. **Planifier avec `launchd`, pas avec `cron`.** L'iMac n'a pas la disponibilité d'un NAS :
   il redémarre, il est parfois éteint. `launchd` rattrape une exécution manquée au réveil,
   `cron` la perd définitivement.
2. **Écrire les sorties sur le NAS, mais vérifier que le partage est monté avant d'écrire.**
   Un point de montage absent reste un dossier local ordinaire : le script croit écrire sur le
   NAS et remplit en silence le SSD de 250 Go. Toujours tester le montage, échouer bruyamment
   sinon.
3. **Rendre chaque job idempotent et rattrapable.** Il doit pouvoir être relancé sans doublon,
   et reprendre la fenêtre manquée quand la machine était éteinte. Sur une machine qui n'est pas
   de l'infrastructure, c'est ce qui remplace la haute disponibilité.

Un mot pratique sur le scraping lui-même : les requêtes partiront de l'IP de la maison. Un
rythme raisonnable et le respect des limites du site ne sont pas de la politesse abstraite —
c'est ce qui évite de faire bloquer la connexion de la maison, NAS et iPhone compris.

## 3 ter. Ranger : archives par machine, données vivantes par sujet

Les fichiers sont aujourd'hui éparpillés sur plusieurs appareils. L'iMac devient l'endroit qui
sait ce qui existe et où. Deux étages, à ne pas confondre :

```
NAS/
  Archives/
    imac-2013-09-2026/      ← vidage figé du disque d'origine, jamais modifié
    macbook-air-…/          ← idem pour chaque machine, à sa date
  Actuel/
    Photos/                 ← la donnée vivante, rangée par sujet
    Documents/
    Projets/
```

**Une archive se range par machine et par date ; la donnée vivante se range par sujet.** Un
vidage d'appareil est figé, en écriture unique : il répond à « qu'y avait-il sur cette machine
en septembre 2026 ». Ranger durablement la donnée courante par appareil, en revanche, conduit
au même dossier Photos en quatre exemplaires sans savoir lequel fait foi. Les appareils
changent, les sujets non.

L'archive est donc une étape, pas une destination : on vide, puis on trie vers `Actuel/`, puis
l'archive ne sert plus que de filet.

### L'index, c'est ce qui fait de l'iMac un centre

Savoir ce qui existe suppose un index, pas une mémoire. `scripts/inventaire.py` le construit :

```bash
python3 inventaire.py scan "/Volumes/Macintosh HD/Users" --nom imac-2013
python3 inventaire.py scan "/Volumes/homes/benjamin" --nom nas
python3 inventaire.py chercher "facture"
python3 inventaire.py doublons
```

Il produit des TSV dans `~/Inventaire`, lisibles dans un tableur. Le scan ne lit pas le contenu
des fichiers, il est donc rapide ; la recherche de doublons ne lit que les fichiers qui ont
exactement la même taille qu'un autre, ce qui évite de parcourir tout l'inventaire. Rien n'est
jamais supprimé : le script montre, la décision reste humaine.

C'est l'outil qui rend le tri possible. Sur 268 Go venus d'une machine et un NAS déjà rempli,
les doublons se comptent en dizaines de gigaoctets.

## 4. Les trois chemins d'accès

| D'où | Comment | Pour quoi |
|---|---|---|
| **iPhone** | claude.ai/code dans le navigateur | Le quotidien. Lancer une tâche sur un dépôt, relire, valider une PR. Taper dans un terminal SSH sur un écran de téléphone est une fausse bonne idée |
| **MacBook Air** | Claude Desktop → environnement **SSH** vers l'iMac | Le mode le plus complet : les sessions s'exécutent sur l'iMac, avec ses fichiers et son réseau, l'interface est en local |
| **PC du bureau** | claude.ai/code | Rien à installer, rien à configurer sur une machine qui ne t'appartient pas. Ne jamais y poser de clé SSH |
| **En direct** | clavier et écran de l'iMac | L'installation, le dépannage, les manipulations de disque |

Le fil entre les trois reste le dépôt : ce qui n'est pas commité n'existe pas pour les autres
chemins.

## 5. Réseau et sécurité

- **Tailscale**, jamais de redirection de port sur la box. L'iMac reçoit une adresse stable
  joignable depuis l'iPhone et le MacBook, sans rien exposer sur Internet. En prime, le NAS
  devient joignable de l'extérieur par le même canal.
- **SSH par clé publique uniquement**, authentification par mot de passe refusée.
- **Rien sur le PC du bureau** : pas de clé SSH, pas de Tailscale, pas de session authentifiée
  qui survive. Le navigateur suffit.
- **Les secrets ne sont jamais dans un dépôt.** Fichier local hors dépôt, chargé par
  l'environnement. Le dépôt est public.
- **Un compte dédié** à l'agent, distinct du compte administrateur quotidien, avec seulement
  les partages NAS dont il a besoin.

## 6. Le Mac mini est déjà dans le plan

L'iMac est explicitement provisoire. La contrainte à respecter dès maintenant : **tout ce qui
est fait sur l'iMac doit être rejouable ailleurs**. D'où la forme de ce dépôt — des scripts et
des procédures écrites, pas des réglages cliqués et oubliés.

Le jour du Mac mini, la migration doit tenir en : cloner ce dépôt, lancer les scripts, se
connecter. Si elle demande plus, c'est qu'un réglage a été fait à la main sans être écrit. Toute
manipulation manuelle non documentée est une dette payable ce jour-là.

## 7. Organisation des projets

```
~/Projets/
  baluchon/      ← un dépôt GitHub, cloné
  tmnh/          ← un dépôt GitHub, cloné
  benlne/        ← ce dépôt : machine, procédures, index des projets
```

Un `CLAUDE.md` par projet : c'est ce qui donne le même contexte à une session cloud lancée
depuis l'iPhone et à une session locale sur l'iMac. C'est la seule mémoire réellement partagée
entre les chemins d'accès — les conversations, elles, ne se rejoignent pas.

## 8. Ce que cela ajoute à la feuille de route

Au-delà de l'installation de Sequoia et des réglages 24/7 :

- [ ] Tailscale sur l'iMac, l'iPhone et le MacBook Air
- [ ] Compte dédié à l'agent
- [ ] `~/Projets` et clonage des dépôts existants
- [ ] Un `CLAUDE.md` par projet
- [ ] Une première tâche planifiée en `claude -p` pour valider le principe
- [ ] Montage du partage NAS au démarrage
- [ ] Vérifier le test de conception : débrancher l'iMac une journée et constater que rien
      d'essentiel ne s'arrête
