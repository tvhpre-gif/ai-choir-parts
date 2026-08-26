#!/bin/bash
# ============================================================
#  AI Choir Parts — lancement en UN CLIC (macOS)
#  Double-clique ce fichier dans le Finder.
#  Au tout premier lancement, l'installation se fait toute seule
#  (quelques minutes). Ensuite, c'est immédiat.
# ============================================================

# Se placer dans le dossier du projet, quel que soit l'endroit du double-clic
cd "$(dirname "$0")" || exit 1

pause() {
  echo ""
  echo "Appuie sur une touche pour fermer cette fenêtre…"
  read -n 1 -s
}

echo "=============================="
echo "   AI Choir Parts"
echo "=============================="
echo ""

# 1) Python 3 est-il présent ?
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python 3 n'est pas installé sur ce Mac."
  echo "   Installe-le depuis https://www.python.org/downloads/"
  echo "   puis relance ce fichier."
  pause
  exit 1
fi

# 2) Première installation (environnement + dépendances) si nécessaire
if [ ! -d ".venv" ]; then
  echo "→ Première installation. Ça prend quelques minutes, c'est normal…"
  echo ""
  python3 -m venv .venv || { echo "❌ Échec de création de l'environnement."; pause; exit 1; }
  ./.venv/bin/pip install --upgrade pip >/dev/null 2>&1
  ./.venv/bin/pip install -r requirements.txt || { echo "❌ Échec d'installation des dépendances."; pause; exit 1; }
  # pyworld = voix transposée de meilleure qualité (optionnel : repli automatique s'il manque)
  ./.venv/bin/pip install pyworld >/dev/null 2>&1 || echo "ℹ️  pyworld non installé (qualité de transposition basique en repli)."
  echo ""
  echo "✓ Installation terminée."
  echo ""
fi

# 3) Rappel ffmpeg (nécessaire pour l'export MP3/WMA) — non bloquant
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ℹ️  ffmpeg n'est pas détecté : l'export sera en WAV."
  echo "   Pour du MP3, installe Homebrew puis : brew install ffmpeg"
  echo ""
fi

# 4) Ouvrir le navigateur dès que le serveur est prêt, puis démarrer l'app
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo "→ Démarrage… ton navigateur va s'ouvrir sur AI Choir Parts."
if [ -n "$IP" ]; then
  echo ""
  echo "  📱 SUR TON ANDROID (même Wi-Fi que ce Mac), ouvre dans Chrome :"
  echo "         http://$IP:5000"
  echo "     puis menu ⋮ → « Ajouter à l'écran d'accueil » pour l'installer comme une app."
  echo ""
fi
echo "  ⚠️  Garde cette fenêtre OUVERTE pendant l'utilisation."
echo "      Ferme-la (ou Ctrl-C) pour arrêter l'application."
echo ""
( sleep 4; open "http://127.0.0.1:5000" ) &

./.venv/bin/python app.py

echo ""
echo "AI Choir Parts est arrêté. Tu peux fermer cette fenêtre."
pause
