# IA locale sur l'iMac — le nœud d'inférence

Note de décision. Elle répond à une intention : disposer d'un modèle de langage qui tourne à la
maison, pour exécuter des agents, sans que les données sortent et sans consommer le plan.

Elle ne concerne **pas** Claude Desktop, et c'est le premier malentendu à écarter.

## 1. Deux circuits, à ne pas confondre

| | Claude Desktop | L'IA locale |
|---|---|---|
| Rôle | le travail de fond, les sessions, le pilotage | exécuter des agents sans humain devant |
| Modèle | **Anthropic**, par l'abonnement | un modèle ouvert, sur la machine |
| Machine | MacBook Air, iMac | **iMac seulement** |
| Où passent les données | chez Anthropic | nulle part |

Les deux cohabitent sans se gêner : le service local écoute sur `localhost:11434` et n'intercepte
rien. Claude Desktop continue de parler à Anthropic.

### Le piège déjà rencontré

Claude Desktop propose un **Gateway** (menu *Configuration d'inférence*) qui permet de changer de
fournisseur d'inférence. Il a été basculé une fois sur Ollama, avec le modèle
`gemma4:31b-cloud`. Deux conséquences, toutes deux indésirables :

- **Ce n'était pas local.** Le suffixe `-cloud` d'un modèle Ollama signifie que le démon local
  détecte le marqueur, attache les identifiants du compte et **relaie la requête vers les
  serveurs d'Ollama**. Vu de l'application rien ne change — elle parle toujours à `localhost` —
  mais l'inférence se fait ailleurs et les prompts sortent de la maison. C'est prévu pour faire
  tourner des modèles trop gros pour une machine personnelle.
- **Claude n'était plus dans le circuit.** Le plan Anthropic était contourné pour rien.

Au passage, le Gateway crée son propre espace de travail, dont la liste de sessions est vide :
les sessions des autres environnements n'y apparaissent pas. **Rien n'est perdu** — c'est un
cloisonnement d'affichage, pas une suppression.

**Règle** : Claude Desktop reste sur Anthropic. Un modèle dont le nom porte `-cloud` ou `:cloud`
n'est pas un modèle local.

## 2. Le verrou système est levé

Ollama demande **macOS 12 minimum** sur Intel. L'iMac était sous Catalina 10.15, donc sous la
barre — la même marche qui bloquait Claude Code (13+) et Claude Desktop (11+).

**Sequoia 15 étant installé via OCLP, le prérequis est satisfait.** Il n'y a plus rien à
débloquer : le service s'installe tel quel. Le support Intel d'Ollama n'a pas été abandonné, il
est simplement bridé — voir le point suivant.

## 3. Ce que le Haswell peut réellement servir

C'est ici qu'est la vraie contrainte, et elle est matérielle.

**Pas de GPU exploitable.** L'Iris Pro 5200 est compatible Metal, mais Ollama ne s'en sert pas
pour l'inférence sur Intel : l'accélération Metal vise Apple Silicon. On est donc en **calcul
processeur pur**, sur 4 cœurs Haswell à 2,7 GHz.

**Le plafond n'est pas le processeur, c'est la mémoire.** Générer un jeton oblige à relire
l'intégralité des poids du modèle. Avec de la DDR3L-1600 en double canal — environ 25 Go/s — le
débit maximum se calcule directement. Les 16 Go ne sont pas la contrainte : un 8B quantifié en
Q4 y tient largement.

### Le piège qui coûte un facteur quatre

**Mesuré sur la machine le 14 septembre 2026**, et c'est le point le plus important de cette
note :

| Réglage | Débit mesuré sur `qwen3.5:4b` |
|---|---|
| `num_thread 4` (défaut d'Ollama) | **0,6 à 1 jeton/s** |
| `num_thread 3` | **3,5 à 4 jetons/s** |

Un quart de la vitesse, pour un réglage par défaut. La cause : Ollama voit 4 cœurs et les prend
tous les quatre, mais **WindowServer en occupe déjà un** (relevé à 113 % de CPU). Les threads
d'inférence se battent alors avec l'affichage, et tout s'effondre.

Sur cette machine, **toujours laisser un cœur à macOS**. C'est fait dans la variante
`qwen3.5-agent` (voir point 5) ; tout nouveau modèle tiré devra recevoir le même traitement,
faute de quoi il paraîtra inutilisable alors qu'il ne l'est pas.

### Ordres de grandeur pour les autres tailles

Ces valeurs-là restent **estimées** par la bande passante, calées sur la mesure ci-dessus :

| Modèle (Q4) | Poids | Attendu, avec `num_thread 3` |
|---|---|---|
| un 3B | ~2 Go | 4 à 6 jetons/s |
| `qwen3.5:4b` | ~2,5 Go | **3,5 à 4 jetons/s — mesuré** |
| un 8B | ~5 Go | 2 à 3 jetons/s |

## 4. La conséquence : des agents asynchrones, pas interactifs

À 2 ou 3 jetons/s, attendre devant l'écran n'a aucun sens. Mais c'est exactement le profil de
cette machine : **allumée en permanence, sans personne devant**. La lenteur ne coûte rien tant
que personne n'attend.

La conception qui en découle :

- **Une file de tâches, pas une conversation.** L'agent prend un travail, le traite, dépose le
  résultat dans un dépôt ou sur le NAS. Il est consulté plus tard, depuis le MacBook Air.
- **Déclenchement par `launchd`**, pas en ligne de commande interactive — et `launchd` rattrape
  les exécutions manquées, ce que `cron` ne fait pas.
- **Des tâches courtes et cadrées.** Classer, résumer, extraire, reformuler, étiqueter : ce qui
  se fait en un ou deux appels.

Ce qui reste hors de portée, et il faut l'assumer : **les boucles longues à beaucoup d'outils**.
Un modèle de 8B y dérive déjà sur une machine rapide ; à 2 jetons/s, chaque dérive se paie en
minutes. Tout ce qui demande du raisonnement soutenu reste chez Claude.

> **Le test** : si la tâche a besoin d'une réponse dans la minute, ou d'un enchaînement de plus
> de trois outils, elle n'est pas pour l'iMac.

## 5. Ce qui est installé — fait le 14 septembre 2026

| | |
|---|---|
| Moteur | **Ollama**, depuis le `.dmg` officiel notarié (binaire universel), signature vérifiée avant installation, dans `/Applications/Ollama.app` |
| Serveur | `127.0.0.1:11434` |
| Modèle | **`qwen3.5:4b`** — appel d'outils vérifié sur un outil factice, il le déclenche correctement |
| Variante réglée | **`qwen3.5-agent`** — `num_thread 3`, `num_ctx 8192`, créée par Modelfile |

C'est `qwen3.5-agent` qu'il faut appeler, pas le modèle nu : c'est elle qui porte le réglage à
trois threads du point 3.

Pour vérifier l'état, ou reproduire ailleurs :

```bash
ollama list                        # ce qui est réellement sur le disque
ollama ps                          # ce qui est chargé, et où
ollama run qwen3.5-agent --verbose # --verbose affiche les jetons/s réels
```

Un modèle dont le nom se termine par `-cloud` ou `:cloud` n'apparaîtra quasiment pas dans
`ollama list` : il n'y a rien de stocké, puisqu'il s'exécute ailleurs (voir point 1).

### Budget disque

Le SSD interne fait 250 Go et porte désormais **deux systèmes**, Catalina et Sequoia. Vérifier
`df -h` avant de télécharger : chaque modèle pèse de 2 à 5 Go, et il est tentant d'en accumuler.
Prévoir une enveloppe et s'y tenir ; `ollama rm` pour ce qui ne sert pas.

## 6. Exposer le service au MacBook Air

Par défaut Ollama n'écoute que sur `localhost` : depuis le MacBook Air, rien n'est joignable.
Pour l'ouvrir :

```bash
launchctl setenv OLLAMA_HOST 0.0.0.0:11434
brew services restart ollama
```

**L'API d'Ollama n'a aucune authentification.** Quiconque atteint le port peut interroger le
modèle, en charger un autre, et faire consommer la machine. Donc, dans l'ordre de préférence :

1. **Tailscale** — n'exposer que sur l'interface du réseau privé, jamais sur le Wi-Fi de la
   maison. C'est la voie prévue par [`architecture.md`](architecture.md).
2. **Un tunnel SSH** depuis le MacBook Air (`ssh -L 11434:localhost:11434 tonton@…`), qui ne
   demande aucun changement de configuration côté iMac.

Ne jamais ouvrir ce port sur la box. Il n'y a rien à mettre devant pour le protéger.

## 7. Ce que cette note change ailleurs

[`architecture.md`](architecture.md) listait « modèles de langage en local » parmi ce que l'iMac
ne ferait pas, au motif qu'il n'a pas de GPU exploitable. Le motif reste exact ; la conclusion
change. La machine **peut** servir un petit modèle, à condition d'accepter le régime asynchrone
décrit au point 4. La ligne a été corrigée en conséquence.

Cela ne déplace pas le centre de gravité : le dépôt reste le centre, et le test de conception
tient toujours. **Si l'iMac meurt cette nuit, on perd un service d'inférence reconstructible en
une commande** — pas des données.

## 8. Ce que le Mac mini changera

Une puce Apple Silicon apporte l'accélération Metal et la mémoire unifiée, soit un ordre de
grandeur sur la vitesse. Les modèles de 8B y deviennent confortables, les 14B envisageables.

Tout ce qui est écrit ici reste valable : mêmes commandes, même service, mêmes agents. Seule la
ligne du tableau au point 3 change, et le point 4 cesse d'être une contrainte pour devenir un
simple choix. **Rien de ce qui sera construit sur l'iMac n'est à jeter.**
