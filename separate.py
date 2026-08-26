"""
AI Choir Parts — pipeline d'extraction (version testable).

Ce que ce script fait RÉELLEMENT :
  1. voix / instrumental            -> Roformer          (fiable)
  2. voix principale / chœurs       -> modèle karaoke    (qualité moyenne)
  3. chœurs -> aigus / graves       -> split de registre (approximation honnête)

Ce que ce script NE fait PAS :
  - il ne sépare PAS proprement Soprano vs Alto vs Ténor vs Basse.
    Cette séparation n'existe pas aujourd'hui pour un mix produit.
    Les pistes "aigus"/"graves" sont un partage du SPECTRE, pas des voix isolées :
    utile pour faire ressortir la ligne haute (souvent la soprano), mais ça bave.

Usage :
    python separate.py mon_morceau.mp3
    python separate.py mon_morceau.mp3 --out exports/ --crossover 400
"""

import argparse
import json
import os
import shutil
import sys

import numpy as np
import soundfile as sf
import librosa


# --- Modèles (noms tels qu'attendus par audio-separator) -------------------
# Si un nom ne charge pas, lance :  audio-separator --list_models
VOCAL_MODEL = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
KARAOKE_MODEL = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"


def _pick(paths, must_contain, must_not=()):
    """Retrouve un stem dans la liste renvoyée par audio-separator via son nom de fichier."""
    for p in paths:
        base = os.path.basename(p).lower()
        if must_contain.lower() in base and all(m.lower() not in base for m in must_not):
            return p
    return None


def _load_separator(output_dir):
    try:
        from audio_separator.separator import Separator
    except ImportError:
        sys.exit("audio-separator n'est pas installé. Fais : pip install -r requirements.txt")
    return Separator(output_dir=output_dir, output_format="WAV")


def separate_stems(input_path, work_dir):
    """Étapes 1 et 2 : renvoie (instrumental, lead, backing) — chemins de fichiers réels."""
    sep = _load_separator(work_dir)

    print("→ Étape 1/3 : voix / instrumental (Roformer)…")
    try:
        sep.load_model(model_filename=VOCAL_MODEL)
    except Exception as e:
        sys.exit(f"Échec du chargement de {VOCAL_MODEL} ({e}).\n"
                 f"Vérifie les noms dispo avec :  audio-separator --list_models")
    out1 = sep.separate(input_path)
    out1 = [os.path.join(work_dir, p) if not os.path.isabs(p) else p for p in out1]
    vocals = _pick(out1, "vocals", must_not=("instrumental",))
    instrumental = _pick(out1, "instrumental")
    if not vocals:
        sys.exit("Impossible de retrouver le stem 'voix'. Sortie du modèle : " + str(out1))

    print("→ Étape 2/3 : voix principale / chœurs (modèle karaoke)…")
    try:
        sep.load_model(model_filename=KARAOKE_MODEL)
        out2 = sep.separate(vocals)
        out2 = [os.path.join(work_dir, p) if not os.path.isabs(p) else p for p in out2]
        lead = _pick(out2, "vocals", must_not=("instrumental",))
        backing = _pick(out2, "instrumental")  # les modèles karaoke nomment le reste "Instrumental"
    except Exception as e:
        print(f"  ⚠ Modèle karaoke indisponible ({e}). On garde la nappe voix complète comme 'chœurs'.")
        lead, backing = None, vocals

    return instrumental, lead, backing


def split_register(backing_path, out_low, out_high, crossover_hz=400.0):
    """Étape 3 : partage spectral doux des chœurs en 'graves' et 'aigus'.
    Ce n'est PAS une séparation de voix — c'est un filtre par fréquence à pente douce."""
    y, sr = sf.read(backing_path, always_2d=True)  # (samples, channels)
    n_fft = 4096
    hop = n_fft // 4
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    width = max(crossover_hz * 0.5, 80.0)
    mask_low = 1.0 / (1.0 + np.exp((freqs - crossover_hz) / width))  # ~1 en bas, ~0 en haut
    mask_high = 1.0 - mask_low

    low_ch, high_ch = [], []
    for c in range(y.shape[1]):
        S = librosa.stft(y[:, c], n_fft=n_fft, hop_length=hop)
        low = librosa.istft(S * mask_low[:, None], hop_length=hop, length=len(y[:, c]))
        high = librosa.istft(S * mask_high[:, None], hop_length=hop, length=len(y[:, c]))
        low_ch.append(low)
        high_ch.append(high)

    sf.write(out_low, np.stack(low_ch, axis=1), sr)
    sf.write(out_high, np.stack(high_ch, axis=1), sr)


def run_pipeline(input_path, out_dir, crossover_hz=400.0, fmt="mp3"):
    """Pipeline complet. Renvoie (tracks {nom_fichier -> chemin}, résumé)."""
    import audioexport
    os.makedirs(out_dir, exist_ok=True)
    work_dir = os.path.join(out_dir, "_work")
    os.makedirs(work_dir, exist_ok=True)

    instrumental, lead, backing = separate_stems(input_path, work_dir)

    wavs = {}

    def keep(src, name):
        if src and os.path.exists(src):
            dst = os.path.join(out_dir, name)
            shutil.copyfile(src, dst)
            wavs[name] = dst

    keep(instrumental, "instrumental.wav")
    keep(lead, "voix_principale.wav")
    keep(backing, "choeurs.wav")

    summary = {
        "niveau_1_voix_instrumental": bool(instrumental),
        "niveau_2_lead_choeurs": bool(lead),
        "niveau_3_satb": False,  # jamais vrai : non résoluble sur mix produit
        "crossover_hz": crossover_hz,
        "format": fmt,
        "avertissement": (
            "Les pistes 'aigus'/'graves' sont un partage du spectre des chœurs, "
            "pas une séparation Soprano/Alto. Elles bavent."
        ),
    }

    if backing and os.path.exists(backing):
        print("→ Étape 3/3 : split de registre des chœurs (aigus / graves)…")
        low = os.path.join(out_dir, "choeurs_graves.wav")
        high = os.path.join(out_dir, "choeurs_aigus.wav")
        split_register(backing, low, high, crossover_hz)
        wavs["choeurs_aigus.wav"] = high   # ≈ ligne haute, souvent soprano
        wavs["choeurs_graves.wav"] = low   # ≈ alto / ténor / basse
        summary["registre_split"] = True

    # Conversion vers le format demandé (mp3/wma), sinon WAV
    tracks = {}
    for name, wav in wavs.items():
        final = audioexport.convert(wav, fmt)
        if final != wav and os.path.exists(wav):
            os.remove(wav)
        tracks[os.path.basename(final)] = final
    summary["ffmpeg_manquant"] = (fmt != "wav" and not audioexport.has_ffmpeg())

    with open(os.path.join(out_dir, "resume.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    shutil.rmtree(work_dir, ignore_errors=True)
    return tracks, summary


def main():
    ap = argparse.ArgumentParser(description="AI Choir Parts — extraction (version testable)")
    ap.add_argument("input", help="fichier audio MP3/WAV/M4A")
    ap.add_argument("--out", default="exports", help="dossier de sortie (défaut: exports/)")
    ap.add_argument("--crossover", type=float, default=400.0,
                    help="fréquence de partage aigus/graves en Hz (défaut: 400)")
    ap.add_argument("--format", default="mp3", choices=["mp3", "wma", "wav"],
                    help="format d'export (défaut: mp3)")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"Fichier introuvable : {args.input}")

    tracks, summary = run_pipeline(args.input, args.out, args.crossover, args.format)
    if summary.get("ffmpeg_manquant"):
        print("⚠ ffmpeg introuvable : export laissé en WAV. Installe-le (brew install ffmpeg) pour du MP3/WMA.")

    print("\n=== Terminé ===")
    for name, path in tracks.items():
        print(f"  {name:22s} -> {path}")
    print("\nRésumé honnête :")
    print(f"  Niveau 1 (voix/instru)   : {'OK' if summary['niveau_1_voix_instrumental'] else 'non'}")
    print(f"  Niveau 2 (lead/chœurs)   : {'OK' if summary['niveau_2_lead_choeurs'] else 'non'}")
    print(f"  Niveau 3 (SATB nommé)    : non disponible (limite technique réelle)")
    print(f"  Chœurs aigus/graves      : approximation de registre, pas une séparation de voix")


if __name__ == "__main__":
    main()
