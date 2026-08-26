"""
AI Choir Parts — interface web locale (Flask).

Lance :   python app.py
Puis ouvre http://127.0.0.1:5000

Le traitement d'un morceau prend plusieurs minutes sur Mac (CPU/MPS).
La page attend la fin (pas de faux indicateur de progression).
"""

import os
import uuid

from flask import Flask, request, render_template, send_from_directory, abort

from separate import run_pipeline
from arrange import run_arrangement, FR

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOADS = os.path.join(BASE, "uploads")
EXPORTS = os.path.join(BASE, "exports")
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(EXPORTS, exist_ok=True)

ALLOWED = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4", ".aac", ".opus"}

# Mode EXTRACTION : libellés (clés = nom sans extension)
LABELS = {
    "voix_principale": ("Voix principale", "Lead isolé du reste des voix."),
    "choeurs_aigus":   ("Chœurs — registre aigu", "≈ ligne haute (souvent soprano). Partage de spectre : ça bave."),
    "choeurs_graves":  ("Chœurs — registre grave", "≈ alto / ténor / basse. Partage de spectre : ça bave."),
    "choeurs":         ("Tous les chœurs", "Toutes les voix d'accompagnement ensemble."),
    "instrumental":    ("Instrumental", "Le morceau sans les voix."),
}
ORDER = ["voix_principale", "choeurs_aigus", "choeurs_graves", "choeurs", "instrumental"]

# Mode ARRANGEMENT : libellés des pupitres générés
LABELS_ARR = {
    "soprano": ("Soprano — ta mélodie", "La ligne que tu as chantée."),
    "alto":    ("Alto", "Voix générée sous la mélodie."),
    "tenor":   ("Ténor", "Voix générée."),
    "bass":    ("Basse", "Voix générée, la plus grave."),
}
ORDER_ARR = ["soprano", "alto", "tenor", "bass"]

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", tracks=None, error=None,
                           kind=None, info=None, extras=[], justesse=None)


@app.route("/analyser", methods=["POST"])
def analyser():
    f = request.files.get("audio")
    if not f or f.filename == "":
        return render_template("index.html", tracks=None, error="Aucun fichier envoyé.")
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED:
        return render_template("index.html", tracks=None,
                               error=f"Format non supporté ({ext}). Enregistre ou importe un audio (MP3, M4A, WAV…).")

    mode = request.form.get("mode", "arrange")
    job = uuid.uuid4().hex[:8]
    raw_path = os.path.join(UPLOADS, f"{job}{ext}")
    f.save(raw_path)
    out_dir = os.path.join(EXPORTS, job)

    # Décodage universel : tout enregistrement micro (webm/opus iOS-mp4…) -> WAV mono 22050
    import audioexport
    try:
        in_path = audioexport.to_wav(raw_path)
    except Exception:
        in_path = raw_path

    try:
        if mode == "extract":
            crossover = float(request.form.get("crossover", 400) or 400)
            produced, _ = run_pipeline(in_path, out_dir, crossover, "mp3")
            by_stem = {os.path.splitext(n)[0]: n for n in produced}
            tracks = [{"file": f"{job}/{by_stem[s]}", "title": LABELS[s][0], "note": LABELS[s][1]}
                      for s in ORDER if s in by_stem]
            return render_template("index.html", tracks=tracks, kind="extract",
                                   info=None, extras=[], justesse=None, error=None, job=job)
        else:  # arrangement
            sung_part = request.form.get("part", "auto")
            if sung_part not in ("auto", "soprano", "alto", "tenor", "bass"):
                sung_part = "auto"
            key_in = (request.form.get("key") or "").strip() or None
            produced, key, score, ff_missing, part_used, just = run_arrangement(
                in_path, out_dir, key_in, "mp3", sung_part)
            by_stem = {os.path.splitext(n)[0]: n for n in produced}
            tracks = []
            for s in ORDER_ARR:
                if s in by_stem:
                    note = ("Ta voix — la ligne que tu as chantée."
                            if s == part_used else "Ta voix transposée sur ce pupitre.")
                    tracks.append({"file": f"{job}/{by_stem[s]}", "title": LABELS_ARR[s][0], "note": note})
            extras = []
            if "choeur_complet" in by_stem:
                extras.append({"file": f"{job}/{by_stem['choeur_complet']}",
                               "label": "Chœur complet (les 4 voix)"})
            if score:
                for p in score:
                    extras.append({"file": f"{job}/{os.path.basename(p)}",
                                   "label": os.path.basename(p)})
            detected = " (détecté)" if sung_part == "auto" else ""
            info = (f"Tu chantes : {FR[part_used]}{detected}. Tonalité : {key}. "
                    f"Chaque pupitre = ta voix (mêmes paroles) transposée — téléchargeable en MP3 (⬇).")
            return render_template("index.html", tracks=tracks, kind="arrange",
                                   info=info, extras=extras, justesse=just, error=None, job=job)
    except SystemExit as e:
        return render_template("index.html", tracks=None, error=str(e))


@app.route("/audio/<job>/<name>")
def audio(job, name):
    safe = os.path.normpath(name)
    if safe.startswith("..") or "/" in safe:
        abort(404)
    as_dl = request.args.get("dl") == "1"
    return send_from_directory(os.path.join(EXPORTS, job), safe, as_attachment=as_dl)


@app.route("/sw.js")
def sw():
    return send_from_directory(os.path.join(BASE, "static"), "sw.js", mimetype="application/javascript")


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(os.path.join(BASE, "static"), "manifest.webmanifest",
                               mimetype="application/manifest+json")


if __name__ == "__main__":
    # host 0.0.0.0 = accessible depuis le téléphone sur le même Wi-Fi
    debug = os.environ.get("CHOIR_DEBUG") == "1"
    app.run(host="0.0.0.0", debug=debug, port=5000)
