#!/bin/bash
# Donner à l'iMac sa propre voix sur GitHub : une clé SSH à son nom.
#
# Tant que cette machine n'a pas d'identifiants, la session Claude Code qui y tourne peut
# committer mais pas pousser — elle reste muette pour les autres surfaces, qui ne lisent
# que le dépôt. C'est le dernier maillon de la passation.
#
# Par défaut le script n'écrit RIEN : il fait l'état des lieux et affiche ce qu'il ferait.
# Il faut --apply pour qu'il agisse.
#
# Usage :
#   bash scripts/imac-github.sh            # diagnostic seul
#   bash scripts/imac-github.sh --apply    # crée la clé, configure git et le dépôt
#
# La clé privée ne sort jamais de la machine et n'est jamais affichée. Seule la clé
# publique est imprimée, pour être collée dans GitHub.

set -u

APPLIQUER=0
[ "${1:-}" = "--apply" ] && APPLIQUER=1

MACHINE="${HOSTNAME:-$(hostname -s 2>/dev/null || echo mac)}"
CLE="$HOME/.ssh/id_ed25519_github"
COMMENTAIRE="$(whoami)@$MACHINE"
DEPOT="${DEPOT:-$HOME/Benlne}"
NOM="${GIT_NOM:-Benjamin Laine}"
COURRIEL="${GIT_COURRIEL:-benjamin.laine@live.fr}"

titre() { echo; echo "=== $1 ==="; }

titre "État des lieux"

if [ -f "$CLE" ]; then
  echo "  clé SSH        : présente ($CLE)"
else
  echo "  clé SSH        : absente"
fi

if [ -d "$DEPOT/.git" ]; then
  echo "  dépôt          : $DEPOT"
  echo "  remote origin  : $(git -C "$DEPOT" remote get-url origin 2>/dev/null || echo 'aucun')"
  echo "  branche        : $(git -C "$DEPOT" rev-parse --abbrev-ref HEAD 2>/dev/null)"
  amont="$(git -C "$DEPOT" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || true)"
  if [ -n "$amont" ]; then
    echo "  non poussés    : $(git -C "$DEPOT" rev-list --count "$amont"..HEAD 2>/dev/null) commit(s)"
  else
    echo "  non poussés    : branche sans amont connu"
  fi
else
  echo "  dépôt          : introuvable en $DEPOT (variable DEPOT pour le désigner)"
fi

echo "  git user.name  : $(git config --global user.name  2>/dev/null || echo 'non défini')"
echo "  git user.email : $(git config --global user.email 2>/dev/null || echo 'non défini')"

# ssh -T renvoie 1 même quand tout va bien : GitHub n'ouvre pas de session interactive.
# C'est le texte de la réponse qui fait foi, pas le code de sortie.
reponse="$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 || true)"
case "$reponse" in
  *successfully\ authenticated*) echo "  GitHub en SSH  : reconnu — ${reponse%%.*}" ;;
  *Permission\ denied*)          echo "  GitHub en SSH  : refusé (clé inconnue de GitHub)" ;;
  *)                             echo "  GitHub en SSH  : ${reponse:-pas de réponse}" ;;
esac

if [ "$APPLIQUER" -eq 0 ]; then
  titre "Ce que ferait --apply"
  [ -f "$CLE" ] || echo "  ssh-keygen -t ed25519 -C \"$COMMENTAIRE\" -f $CLE -N ''"
  echo "  écrire l'entrée github.com dans ~/.ssh/config"
  echo "  git config --global user.name \"$NOM\" / user.email \"$COURRIEL\""
  echo "  basculer le remote origin de HTTPS vers git@github.com"
  echo
  echo "Rien n'a été modifié. Relancer avec --apply pour agir."
  exit 0
fi

titre "Application"

mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"

if [ -f "$CLE" ]; then
  echo "  clé déjà présente, conservée."
else
  # Pas de phrase de passe : cette machine tourne 24/7 sans personne devant, et doit
  # pouvoir pousser depuis une tâche planifiée. FileVault étant désactivé, une phrase
  # rangée dans le trousseau ne protégerait de rien que le disque ne livre déjà.
  ssh-keygen -t ed25519 -C "$COMMENTAIRE" -f "$CLE" -N '' -q
  echo "  clé créée."
fi
chmod 600 "$CLE"

if ! grep -qs '^Host github.com' "$HOME/.ssh/config" 2>/dev/null; then
  cat >> "$HOME/.ssh/config" <<CONFIG

Host github.com
  HostName github.com
  User git
  IdentityFile $CLE
  IdentitiesOnly yes
CONFIG
  echo "  ~/.ssh/config complété."
else
  echo "  ~/.ssh/config contient déjà une entrée github.com, laissée telle quelle."
fi
chmod 600 "$HOME/.ssh/config"

git config --global user.name  "$NOM"
git config --global user.email "$COURRIEL"
echo "  identité git réglée sur $NOM <$COURRIEL>."

if [ -d "$DEPOT/.git" ]; then
  actuel="$(git -C "$DEPOT" remote get-url origin 2>/dev/null || echo '')"
  case "$actuel" in
    git@github.com:*) echo "  remote déjà en SSH." ;;
    https://github.com/*)
      chemin="${actuel#https://github.com/}"
      git -C "$DEPOT" remote set-url origin "git@github.com:${chemin%.git}.git"
      echo "  remote basculé en SSH : $(git -C "$DEPOT" remote get-url origin)"
      ;;
    *) echo "  remote inattendu ($actuel), laissé tel quel." ;;
  esac
fi

titre "Clé publique à déclarer dans GitHub"
echo
cat "$CLE.pub"
echo
echo "  1. Copier la ligne ci-dessus (elle n'est pas secrète)."
echo "  2. L'ajouter sur https://github.com/settings/ssh/new — titre : $COMMENTAIRE"
echo "  3. Vérifier :  ssh -T git@github.com"
echo "  4. Pousser  :  git -C $DEPOT push -u origin \$(git -C $DEPOT rev-parse --abbrev-ref HEAD)"
