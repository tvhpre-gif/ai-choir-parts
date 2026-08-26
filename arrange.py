"""
AI Choir Parts — mode ARRANGEMENT.

Rendu par défaut, pensé pour APPRENDRE une partie et bien la DISTINGUER :
  - TA voix (avec tes paroles) est gardée pour TON pupitre (référence).
  - Les 3 autres pupitres sont rendus avec un SON CLAIR et distinct (type orgue),
    à leur vraie hauteur -> chaque note s'entend nettement, juste, sans bouillie.

Chaîne :
  1. Détection F0 note par note (librosa.pyin).
  2. Justesse : écart en cents vs gamme tempérée.
  3. Identification du pupitre chanté (tessiture) — ou choix manuel.
  4. Harmonisation SATB : chaque voix placée dans SA tessiture (accords diatoniques).
  5. Synthèse d'un son clair pour les voix générées ; ta voix gardée pour ta partie.
  6. Export MP3/WMA/WAV + partition MIDI/MusicXML.
"""

import argparse
import os
import sys

import numpy as np
import soundfile as sf
import librosa

PARTS = ["soprano", "alto", "tenor", "bass"]
RANK = {"soprano": 0, "alto": 1, "tenor": 2, "bass": 3}
RANGES = {"soprano": (60, 81), "alto": (55, 74), "tenor": (48, 67), "bass": (40, 60)}
CENTERS = {"soprano": 70, "alto": 64, "tenor": 57, "bass": 50}
FR = {"soprano": "Soprano", "alto": "Alto", "tenor": "Ténor", "bass": "Baryton/Basse"}


# ---------- 1-2. Mélodie + justesse ----------
def track_melody(path):
    y, sr = librosa.load(path, sr=22050, mono=True)
    f0, _, _ = librosa.pyin(
        y, sr=sr, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C6"),
        frame_length=2048,
    )
    times = librosa.times_like(f0, sr=sr)

    events, cur, buf = [], None, []
    for i, f in enumerate(f0):
        m = None if (f is None or np.isnan(f)) else int(round(librosa.hz_to_midi(f)))
        if m is None:
            if cur:
                cur["f0s"] = buf; events.append(cur); cur, buf = None, []
            continue
        if cur and m == cur["midi"] and times[i] - cur["end"] < 0.12:
            cur["end"] = float(times[i]); buf.append(float(f))
        else:
            if cur:
                cur["f0s"] = buf; events.append(cur)
            cur = {"midi": m, "start": float(times[i]), "end": float(times[i])}; buf = [float(f)]
    if cur:
        cur["f0s"] = buf; events.append(cur)

    events = [e for e in events if e["end"] - e["start"] >= 0.12]
    if not events:
        sys.exit("Aucune note détectée. Chante a cappella, clairement, dans un endroit silencieux.")

    for e in events:
        fmed = float(np.median(e.pop("f0s"))) if e.get("f0s") else librosa.midi_to_hz(e["midi"])
        midi_f = 69 + 12 * np.log2(fmed / 440.0)
        nearest = int(round(midi_f))
        e["midi"] = nearest
        e["f0"] = fmed
        e["cents"] = (midi_f - nearest) * 100.0
        e["note"] = librosa.midi_to_note(nearest)
    return events, sr, y


def justesse(events):
    vals = [abs(e["cents"]) for e in events]
    avg = float(np.mean(vals)) if vals else 0.0
    verdict = ("très juste" if avg < 10 else "juste" if avg < 20
               else "à travailler" if avg < 35 else "souvent faux")
    rows = [{
        "note": e["note"], "dur": round(e["end"] - e["start"], 2),
        "cents": round(e["cents"]),
        "dir": "♯ trop haut" if e["cents"] > 5 else "♭ trop bas" if e["cents"] < -5 else "juste",
    } for e in events]
    return {"avg": round(avg), "verdict": verdict, "rows": rows}


# ---------- 3-4. Pupitre + harmonisation SATB (par tessiture) ----------
def detect_part(events):
    med = float(np.median([e["midi"] for e in events]))
    return min(CENTERS, key=lambda p: abs(CENTERS[p] - med))


def diatonic_triads(k):
    sc = k.getScale()
    pref = {1: 5, 4: 4, 5: 5, 6: 3, 2: 2, 3: 1, 7: 1}
    triads = []
    for d in range(1, 8):
        root = sc.pitchFromDegree(d)
        third = sc.pitchFromDegree((d + 1) % 7 + 1)
        fifth = sc.pitchFromDegree((d + 3) % 7 + 1)
        triads.append({"root": root.pitchClass,
                       "pcs": [root.pitchClass, third.pitchClass, fifth.pitchClass],
                       "w": pref[d]})
    return triads


def nearest_in_range(pc, lo, hi, target):
    cands = [m for m in range(lo, hi + 1) if m % 12 == pc]
    if not cands:
        cands = [pc + 12 * o for o in range(2, 8) if lo - 7 <= pc + 12 * o <= hi + 7]
    return min(cands, key=lambda m: abs(m - target)) if cands else target


def build_parts(events, key_str=None, sung_part=None):
    """Écarte les 4 pupitres dans des voix DISTINCTES autour du chanteur,
    en PLAFONNANT chaque transposition à une octave (±12 demi-tons) : s'adapte
    automatiquement à toute voix (basse, ténor, alto, soprano)."""
    from music21 import stream, note as m21note, key as m21key
    his = sung_part if sung_part in PARTS else detect_part(events)

    s = stream.Stream()
    for e in events:
        n = m21note.Note(); n.pitch.midi = e["midi"]; n.quarterLength = 1
        s.append(n)
    try:
        k = m21key.Key(*key_str.split()) if key_str else s.analyze("key")
    except Exception:
        k = s.analyze("key")

    triads = diatonic_triads(k)
    parts = {p: [] for p in PARTS}
    for e in events:
        m = e["midi"]; pc = m % 12
        chord = max([t for t in triads if pc in t["pcs"]] or triads, key=lambda t: t["w"])
        cpcs = set(chord["pcs"])
        # notes d'accord disponibles à ±1 octave autour du chanteur
        window = [x for x in range(m - 12, m + 13) if x % 12 in cpcs]
        voices = {his: m}
        used = {m}
        for p in PARTS:
            if p == his:
                continue
            steps = RANK[his] - RANK[p]              # >0 : p est plus aigu que le chanteur
            offset = max(-12, min(12, steps * 4))    # ~une tierce par voix d'écart, plafonné à l'octave
            target = m + offset
            avail = [x for x in window if x not in used] or window
            pick = min(avail, key=lambda x: abs(x - target))
            voices[p] = pick; used.add(pick)
        for p in PARTS:
            parts[p].append({"midi": voices[p], "start": e["start"], "end": e["end"]})
    return parts, str(k), his


# ---------- 5. Synthèse d'un son clair (voix générées) ----------
def synth(events, sr, total):
    buf = np.zeros(int(total * sr) + sr, dtype=np.float32)
    for e in events:
        f = 440.0 * 2 ** ((e["midi"] - 69) / 12.0)
        n = int((e["end"] - e["start"]) * sr)
        if n <= 0:
            continue
        t = np.arange(n) / sr
        vib = 1 + 0.005 * np.sin(2 * np.pi * 5 * t)
        # timbre type orgue doux : fondamentale + harmoniques
        w = (np.sin(2*np.pi*f*t*vib) + 0.35*np.sin(2*2*np.pi*f*t)
             + 0.15*np.sin(3*2*np.pi*f*t) + 0.07*np.sin(4*2*np.pi*f*t))
        env = np.ones(n)
        a, r = int(0.02*sr), int(0.06*sr)
        if a: env[:a] = np.linspace(0, 1, a)
        if r: env[-r:] = np.linspace(1, 0, r)
        i0 = int(e["start"] * sr)
        seg = (w * env * 0.25).astype(np.float32)
        buf[i0:i0+len(seg)] += seg[:len(buf)-i0]
    peak = np.max(np.abs(buf)) or 1.0
    return (buf / peak * 0.9).astype(np.float32)



# ---------- Transposition (Rubber Band, timbre préservé) + habillage ----------
# Filtre d'habillage : léger chœur + réverb douce + aigus adoucis (rendu moins "IA")
POLISH = "chorus=0.6:0.9:50|60:0.35|0.25:0.5|0.4:2|2.5, aecho=0.8:0.85:45:0.2, treble=g=-2.5"


def transpose(y, sr, semis):
    """Transpose TA voix d'un intervalle constant (paroles + phrasé gardés),
    en préservant le timbre. Rubber Band (moteur R3 haute qualité) si dispo, sinon repli."""
    if abs(semis) < 0.1:
        return y.astype(np.float32)
    try:
        import pyrubberband as pyrb
        return pyrb.pitch_shift(y, sr, n_steps=semis,
                                rbargs={"-F": "", "--pitch-hq": ""}).astype(np.float32)
    except Exception:
        return librosa.effects.pitch_shift(y.astype(float), sr=sr, n_steps=semis).astype(np.float32)


# ---------- 6. Partition ----------
def export_score(parts, out_dir):
    try:
        from music21 import stream, note as m21note
    except Exception:
        return None
    sc = stream.Score()
    for name in PARTS:
        p = stream.Part(); p.partName = FR[name]
        for e in parts[name]:
            n = m21note.Note(); n.pitch.midi = e["midi"]
            n.quarterLength = max(0.25, round((e["end"] - e["start"]) * 2 * 4) / 4)
            p.append(n)
        sc.insert(0, p)
    midi_path = os.path.join(out_dir, "arrangement.mid")
    xml_path = os.path.join(out_dir, "arrangement.musicxml")
    try:
        sc.write("midi", fp=midi_path)
        sc.write("musicxml", fp=xml_path)
        return midi_path, xml_path
    except Exception:
        return None


# ---------- Pipeline ----------
def run_arrangement(input_path, out_dir, key_str=None, fmt="mp3", sung_part=None):
    import audioexport
    os.makedirs(out_dir, exist_ok=True)
    events, sr, y = track_melody(input_path)
    parts, key, his = build_parts(events, key_str, sung_part)
    just = justesse(events)
    total = max(e["end"] for e in events) + 0.3

    produced = {}
    for name in PARTS:
        if name == his:
            audio = y.astype(np.float32)                       # ta voix (ta partie)
        else:
            # décalage constant = intervalle moyen vers cette voix (rendu plus naturel)
            semis = float(np.median([parts[name][i]["midi"] - events[i]["midi"]
                                     for i in range(len(events))]))
            audio = transpose(y, sr, semis)                    # ta voix transposée, paroles gardées
        wav = os.path.join(out_dir, f"{name}.wav")
        sf.write(wav, audio, sr)
        final = audioexport.convert(wav, fmt, af=POLISH)       # habillage chœur/réverb
        if final != wav and os.path.exists(wav):
            os.remove(wav)
        produced[os.path.basename(final)] = final

    score = export_score(parts, out_dir)
    ff_missing = (fmt != "wav" and not audioexport.has_ffmpeg())
    return produced, key, score, ff_missing, his, just


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default="exports/arrangement")
    ap.add_argument("--key", default=None)
    ap.add_argument("--part", default="auto", choices=["auto"] + PARTS)
    ap.add_argument("--format", default="mp3", choices=["mp3", "wma", "wav"])
    args = ap.parse_args()
    if not os.path.exists(args.input):
        sys.exit(f"Fichier introuvable : {args.input}")
    produced, key, score, ff, his, just = run_arrangement(
        args.input, args.out, args.key, args.format, args.part)
    print(f"Tu chantes : {FR[his]} | Tonalité : {key} | Justesse : {just['avg']} cents ({just['verdict']})")
    for name, path in produced.items():
        tag = "  ← ta voix" if os.path.splitext(name)[0] == his else "  (son clair)"
        print(f"  {name:14s} -> {path}{tag}")
    if score:
        print(f"  partition -> {score[0]} + {score[1]}")


if __name__ == "__main__":
    main()
