#!/bin/bash
# Copier un dossier vers le NAS (ou n'importe quelle destination montée), de façon
# reprenable : la commande peut être relancée autant de fois que nécessaire, elle
# ne recopie que ce qui manque.
#
# Rien n'est effacé côté source, et rien n'est supprimé côté destination.
#
# Usage :
#   bash copie-vers-nas.sh "/Volumes/Disque/Users/tonton" "/Volumes/homes/benjamin/Save disque imac"
#   bash copie-vers-nas.sh --taille "/Volumes/Disque"        # pèse seulement, ne copie rien
#   bash copie-vers-nas.sh --liste ~/a-copier.txt "/Volumes/Disque/Users" "/Volumes/homes/..."
#
# --liste attend un fichier de chemins RELATIFS à la source, tel que produit par
# « inventaire.py manquants --liste-rsync » : seuls ces fichiers sont copiés, et
# ce qui existe déjà ailleurs ne traverse jamais le réseau.

set -u

if [ "${1:-}" = "--taille" ]; then
  source="${2:-}"
  [ -d "$source" ] || { echo "Dossier introuvable : $source" >&2; exit 1; }
  echo "Poids du premier niveau de $source :"
  du -sh "$source"/* 2>/dev/null | sort -h
  echo
  echo "Total :"
  du -sh "$source" 2>/dev/null
  exit 0
fi

liste=""
if [ "${1:-}" = "--liste" ]; then
  liste="${2:-}"
  shift 2
  [ -f "$liste" ] || { echo "Liste introuvable : $liste" >&2; exit 1; }
fi

source="${1:-}"
destination="${2:-}"

if [ -z "$source" ] || [ -z "$destination" ]; then
  echo "Usage : bash copie-vers-nas.sh \"<source>\" \"<destination>\"" >&2
  echo "        bash copie-vers-nas.sh --taille \"<source>\"" >&2
  exit 1
fi

command -v rsync >/dev/null 2>&1 || {
  echo "rsync est introuvable. Il est fourni avec macOS ; si la commande manque," >&2
  echo "installer les Command Line Tools : xcode-select --install" >&2
  exit 1
}

[ -d "$source" ] || { echo "Source introuvable : $source" >&2; exit 1; }
if [ ! -d "$destination" ]; then
  echo "Destination introuvable : $destination" >&2
  echo "Le partage réseau est-il monté ? Dans le Finder : Aller → Se connecter au serveur" >&2
  echo "(cmd+K), puis smb://NasDom._smb._tcp.local/homes" >&2
  exit 1
fi

echo "Source      : $source"
echo "Destination : $destination"
if [ -n "$liste" ]; then
  echo "Liste       : $liste ($(grep -c . "$liste") fichiers)"
else
  echo "Volume à transférer :"
  du -sh "$source" 2>/dev/null | sed 's/^/  /'
fi
echo
echo "Espace libre à destination :"
df -h "$destination" 2>/dev/null | awk 'NR==2 {print "  "$4" disponibles"}'
echo

# -r récursif, -l symlinks, -t dates. Pas de -p/-o/-g : un partage SMB
# n'accepte ni les permissions ni les propriétaires d'un volume macOS, et
# rsync échouerait sur chaque fichier.
# --partial reprend un fichier interrompu, ce qui compte en Wi-Fi.
# caffeinate empêche la mise en veille pendant la copie.
[ -n "$liste" ] && option_liste="--files-from=$liste" || option_liste=""

# shellcheck disable=SC2086
caffeinate -i rsync -rlt --partial --progress -v $option_liste \
  --exclude '.Spotlight-V100' \
  --exclude '.fseventsd' \
  --exclude '.Trashes' \
  --exclude '.DocumentRevisions-V100' \
  --exclude '.TemporaryItems' \
  --exclude '.DS_Store' \
  --exclude 'Caches' \
  "$source/" "$destination/"

etat=$?
echo
if [ $etat -eq 0 ]; then
  echo "Copie terminée sans erreur."
  echo "Vérification : relancer exactement la même commande. Si elle ne transfère"
  echo "plus rien, les deux côtés sont identiques."
else
  echo "rsync s'est arrêté avec le code $etat."
  echo "Des erreurs sur des liens symboliques ou des fichiers système sont sans"
  echo "conséquence pour des données personnelles. Relancer la commande reprend"
  echo "où elle s'est arrêtée."
fi
exit $etat
