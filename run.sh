#!/usr/bin/env bash
# Lanceur unique AI Choir Parts.
#   ./run.sh                      -> interface web (http://127.0.0.1:5000)
#   ./run.sh extract morceau.mp3  -> extraction voix/chœurs
#   ./run.sh arrange melodie.wav  -> génère les pupitres depuis une mélodie
set -e
cd "$(dirname "$0")"

# Installe l'environnement au premier lancement uniquement
if [ ! -d .venv ]; then
  echo "→ Première installation (venv + dépendances). Ça peut prendre quelques minutes…"
  python3 -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip
  ./.venv/bin/pip install -q -r requirements.txt
  ./.venv/bin/pip install -q pyworld 2>/dev/null || echo "pyworld optionnel non installé (repli qualité basique)."
  echo "→ Installation terminée."
fi
source .venv/bin/activate

case "${1:-web}" in
  extract) shift; python separate.py "$@" ;;
  arrange) shift; python arrange.py "$@" ;;
  web|"")  python app.py ;;
  *)       echo "Usage : ./run.sh [web|extract <fichier>|arrange <fichier>]" ;;
esac
