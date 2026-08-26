# AI Choir Parts — version testable

Isole les voix d'un morceau pour répéter ta partie. Traitement **réel**, pas de simulation.

## Lancement en un clic (Mac)

Double-clique **`demarrer.command`**. Au premier lancement, tout s'installe automatiquement
(quelques minutes), puis ton navigateur s'ouvre sur AI Choir Parts. Garde la fenêtre Terminal
ouverte pendant l'utilisation ; ferme-la pour arrêter l'app.

> **La 1re fois, macOS peut bloquer un fichier téléchargé.** Si double-cliquer ne fait rien ou
> affiche « développeur non identifié » : clic droit sur `demarrer.command` → **Ouvrir** →
> **Ouvrir**. À faire une seule fois.
> (Alternative en Terminal : `xattr -d com.apple.quarantine demarrer.command`.)

Prérequis : **Python 3** ([python.org](https://www.python.org/downloads/)) et, pour l'export MP3,
**ffmpeg** (`brew install ffmpeg`). Le lanceur te prévient si l'un manque.

## Ce que ça fait vraiment

| Niveau | Sortie | Fiabilité |
|---|---|---|
| 1 | `instrumental.wav` + voix | ✅ bon (Roformer) |
| 2 | `voix_principale.wav` + `choeurs.wav` | 🟡 moyen (modèle karaoke) |
| 3 | `choeurs_aigus.wav` / `choeurs_graves.wav` | 🟠 **approximation de registre** |

**À lire une fois.** Les pistes *aigus / graves* sont un **partage du spectre** des chœurs
(filtre par fréquence à pente douce), **pas** une séparation Soprano/Alto/Ténor/Basse.
Une vraie séparation SATB sur un mix produit n'existe pas aujourd'hui. Concrètement :
- « aigus » fait ressortir la ligne haute (souvent la soprano) — utile pour l'apprendre,
- mais les voix se chevauchent, donc ça bave. C'est un aide-mémoire, pas un stem propre.

## Installation

Prérequis : Python 3.10+ et **ffmpeg**.

```bash
# ffmpeg (Mac)
brew install ffmpeg

cd ai-choir-parts
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Au **premier** lancement, les modèles se téléchargent (plusieurs centaines de Mo), puis sont mis en cache.

## Utilisation — une seule commande

`run.sh` crée l'environnement au premier lancement, puis exécute le mode voulu.

```bash
chmod +x run.sh        # une fois

./run.sh                        # interface web (http://127.0.0.1:5000)
./run.sh extract morceau.mp3    # EXTRACTION : sépare voix / chœurs / aigus / graves
./run.sh arrange melodie.wav    # ARRANGEMENT : génère les pupitres depuis une mélodie
```

### Mode EXTRACTION
Part d'un morceau existant et sépare ce qui s'y trouve.
Sorties dans `exports/` : `instrumental`, `voix_principale`, `choeurs`, `choeurs_aigus`, `choeurs_graves`.
Option `--crossover 400` (Hz du partage aigus/graves).

### Mode ARRANGEMENT (chante ta ligne → obtiens les autres voix)
Part d'**une seule voix a cappella** (tu la chantes puis l'enregistres, ou tu uploades un mp3).

L'app :
1. détecte tes notes (F0) et calcule ta **justesse** (écart en cents vs gamme tempérée) ;
2. **identifie ton pupitre** d'après ta tessiture (menu « Je chante » pour forcer) ;
3. génère les 3 autres pupitres en **harmonie parallèle** : ta ligne décalée d'un intervalle
   diatonique *régulier* (≈ une tierce par voix d'écart), plafonné pour rester naturel ;
4. **transpose ta propre voix** (mêmes paroles, même phrasé) à ces hauteurs, formants préservés
   (vocodeur WORLD) — le contour de ta mélodie est conservé, donc c'est fluide et intelligible.

Champ **Tonalité** optionnel (ex. `C minor`) si la détection auto se trompe.
Un pupitre = ta voix transposée, en **MP3** (⬇) ; partition MIDI/MusicXML fournie.
CLI : `--part tenor`, `--key "G major"`, `--format wma`.

> Limites : c'est de l'harmonie *parallèle* (même mélodie transposée), pas l'arrangement exact
> de ton groupe ; c'est ton timbre sur toutes les voix ; la basse (transposition vers le grave)
> est plus fragile, surtout sur un enregistrement compressé — enregistre au propre (mémo vocal
> en pièce silencieuse, pas WhatsApp) pour un meilleur résultat.

> C'est une harmonisation **générée** (règles diatoniques), pas l'arrangement exact d'un morceau donné,
> et les pistes sont des sons de synthèse faits pour entendre les notes.

L'**interface web** (double-clic sur `demarrer.command`) propose les deux modes au choix, avec
un mixeur multipiste synchronisé (**volume / mute / solo / boucle A-B**) et un bouton **⬇ MP3**
par pupitre. Pour le mode arrangement, la **partition** (MusicXML + MIDI) est aussi téléchargeable.

## Format des fichiers exportés

Par défaut tout sort en **MP3** (universel, léger, partageable par WhatsApp/téléphone).

```bash
./run.sh extract morceau.mp3 --format mp3    # défaut
./run.sh extract morceau.mp3 --format wma    # Windows Media Audio
./run.sh extract morceau.mp3 --format wav    # non compressé
./run.sh arrange melodie.wav --format wma
```

L'**interface web** exporte en MP3 (lecture + bouton ⬇ MP3 par piste) : le navigateur ne lit pas
le WMA. Si tu tiens au WMA, passe par la ligne de commande ci-dessus.
La conversion utilise **ffmpeg** (déjà requis) ; s'il manque, les fichiers restent en WAV avec un avertissement.

> Conseil : pour partager avec le groupe, le **MP3** est le choix sûr (tout appareil le lit).
> Le WMA est surtout utile si un logiciel Windows précis l'exige.

## Perf

Sur Mac (CPU/MPS), compte **plusieurs minutes par morceau**. C'est normal.
Pas de faux indicateur de progression : la page attend réellement la fin du traitement.

## Si un modèle ne se charge pas

Les noms de modèles peuvent évoluer. Liste ceux disponibles :

```bash
audio-separator --list_models
```

puis ajuste `VOCAL_MODEL` / `KARAOKE_MODEL` en haut de `separate.py`.

## Prochaines étapes (pas dans cette version)

- **Mode arrangement** : générer une harmonisation SATB depuis la mélodie (plus fiable que l'extraction).
- **Mode expérimental a cappella** : brancher les modèles SATB de recherche (MTG-UPF) — uniquement sur
  des enregistrements a cappella propres, clairement étiqueté.
- Détection de sections (couplet/refrain), ralenti sans changement de ton, transcription MIDI/MusicXML.
