"""Conversion des pistes WAV vers un format partageable (MP3 / WMA) via ffmpeg."""

import os
import shutil
import subprocess

FFMPEG = shutil.which("ffmpeg")
if FFMPEG is None:  # repli : binaire ffmpeg fourni par imageio-ffmpeg (utile en cloud / Mac sans brew)
    try:
        import imageio_ffmpeg
        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG = None

# Réglages d'encodage par format
_CODECS = {
    "mp3": ["-codec:a", "libmp3lame", "-q:a", "2"],   # ~190 kbps VBR, universel
    "wma": ["-codec:a", "wmav2", "-b:a", "192k"],      # Windows Media Audio
}

SUPPORTED = ("wav", "mp3", "wma")


def has_ffmpeg():
    return FFMPEG is not None


def to_wav(src, out_dir=None):
    """Convertit n'importe quel audio (webm/opus, m4a/aac, mp4, ogg, mp3…) en WAV mono 22050 Hz.
    Indispensable pour décoder de façon fiable les enregistrements micro du navigateur
    (iOS = mp4/aac, Android = webm/opus). Renvoie le chemin du WAV, ou src si ffmpeg absent."""
    if not has_ffmpeg():
        return src
    base = os.path.splitext(os.path.basename(src))[0]
    dst = os.path.join(out_dir or os.path.dirname(src), base + "_in.wav")
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "22050", dst],
        check=True,
    )
    return dst


def convert(src_wav, fmt):
    """Convertit src_wav vers fmt. Renvoie le chemin du fichier final.
    - fmt 'wav' : renvoie le fichier tel quel.
    - ffmpeg absent : renvoie le WAV et laisse l'appelant prévenir l'utilisateur.
    """
    fmt = fmt.lower()
    if fmt == "wav":
        return src_wav
    if fmt not in _CODECS:
        raise ValueError(f"Format non supporté : {fmt} (attendus : {', '.join(SUPPORTED)})")
    if not has_ffmpeg():
        return src_wav
    dst = os.path.splitext(src_wav)[0] + "." + fmt
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", src_wav, *_CODECS[fmt], dst],
        check=True,
    )
    return dst


def convert_all(wav_paths, fmt, remove_wav=True):
    """Convertit une liste de WAV. Renvoie la liste des chemins finaux.
    Supprime les WAV source si un autre format a bien été produit."""
    out = []
    for w in wav_paths:
        final = convert(w, fmt)
        out.append(final)
        if remove_wav and final != w and os.path.exists(final):
            try:
                os.remove(w)
            except OSError:
                pass
    return out
