"""
AI Choir Parts — mode ARRANGEMENT (analyse + harmonie parallèle par transposition de la voix).

On garde TA voix (paroles + phrasé) et on la décale d'un intervalle diatonique régulier
qui suit ta mélodie (harmonie parallèle). Rendu fluide et intelligible.

Chaîne : 1) F0 note par note  2) justesse (cents)  3) pupitre chanté
         4) harmonie parallèle  5) transposition WORLD (formants préservés)  6) export.
"""

import argparse
import os
import sys

import numpy as np
import soundfile as sf
import librosa

PARTS = ["soprano", "alto", "tenor", "bass"]
RANK = {"soprano": 0, "alto": 1, "tenor": 2, "bass": 3}
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


# ---------- 3-4. Pupitre + harmonie parallèle ----------
def detect_part(events):
    med = float(np.median([e["midi"] for e in events]))
    return min(CENTERS, key=lambda p: abs(CENTERS[p] - med))


def _key_pcs(k):
    return {p.pitchClass for p in k.getScale().getPitches("C2", "C6")}


def diatonic_shift(m, pcs, steps):
    if steps == 0:
        return m
    direction = 1 if steps > 0 else -1
    count, cur = 0, m
    for _ in range(24):
        cur += direction
        if cur % 12 in pcs:
            count += 1
            if count == abs(steps):
                return cur
    return m + direction * 2 * abs(steps)


def build_parts(events, key_str=None, sung_part=None):
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
    pcs = _key_pcs(k)

    parts = {}
    for p in PARTS:
        if p == his:
            parts[p] = [{"midi": e["midi"], "start": e["start"], "end": e["end"]} for e in events]
        else:
            steps = (RANK[his] - RANK[p]) * 2
            parts[p] = [{"midi": diatonic_shift(e["midi"], pcs, steps),
                         "start": e["start"], "end": e["end"]} for e in events]
    return parts, str(k), his


# ---------- 5. Transposition WORLD (formants préservés) ----------
def _world_analyze(y, sr):
    import pyworld as pw
    y64 = np.ascontiguousarray(y.astype(np.float64))
    fp = 5.0
    f0, t = pw.harvest(y64, sr, f0_floor=65.0, f0_ceil=1100.0, frame_period=fp)
    sp = pw.cheaptrick(y64, f0, t, sr)
    ap = pw.d4c(y64, f0, t, sr)
    return f0, t, sp, ap, fp


def _world_resynth(f0, t, sp, ap, fp, sr, events, targets, base_midis):
    import pyworld as pw
    ratios = np.ones_like(f0)
    for e, tg, bm in zip(events, targets, base_midis):
        lo = int(np.searchsorted(t, e["start"]))
        hi = int(np.searchsorted(t, e["end"]))
        ratios[lo:hi] = 2.0 ** ((tg - bm) / 12.0)
    new_f0 = np.where(f0 > 0, f0 * ratios, 0.0)
    out = pw.synthesize(np.ascontiguousarray(new_f0), sp, ap, sr, fp)
    peak = np.max(np.abs(out)) or 1.0
    return (out / peak * 0.9).astype(np.float32)


def _fallback_resynth(y, sr, events, targets, base_midis):
    shift = float(np.median([tg - bm for tg, bm in zip(targets, base_midis)]))
    out = librosa.effects.pitch_shift(y.astype(float), sr=sr, n_steps=shift)
    peak = np.max(np.abs(out)) or 1.0
    return (out / peak * 0.9).astype(np.float32)


def _choir_mix(parts_audio):
    n = min(len(a) for a in parts_audio.values())
    mix = sum(a[:n] for a in parts_audio.values())
    peak = np.max(np.abs(mix)) or 1.0
    return (mix / peak * 0.9).astype(np.float32)


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
    base_midis = [e["midi"] for e in events]

    try:
        analysis = _world_analyze(y, sr)
    except Exception:
        analysis = None

    parts_audio = {}
    for name in PARTS:
        if name == his:
            parts_audio[name] = y.astype(np.float32)
        else:
            targets = [parts[name][i]["midi"] for i in range(len(events))]
            if analysis:
                parts_audio[name] = _world_resynth(*analysis, sr, events, targets, base_midis)
            else:
                parts_audio[name] = _fallback_resynth(y, sr, events, targets, base_midis)

    produced = {}
    for name in PARTS:
        wav = os.path.join(out_dir, f"{name}.wav")
        sf.write(wav, parts_audio[name], sr)
        final = audioexport.convert(wav, fmt)
        if final != wav and os.path.exists(wav):
            os.remove(wav)
        produced[os.path.basename(final)] = final

    # mix chœur complet (somme simple)
    mixwav = os.path.join(out_dir, "choeur_complet.wav")
    sf.write(mixwav, _choir_mix(parts_audio), sr)
    mixfinal = audioexport.convert(mixwav, fmt)
    if mixfinal != mixwav and os.path.exists(mixwav):
        os.remove(mixwav)
    produced[os.path.basename(mixfinal)] = mixfinal

    score = export_score(parts, out_dir)
    ff_missing = (fmt != "wav" and not audioexport.has_ffmpeg())
    return produced, key, score, ff_missing, his, just


def main():
    ap = argparse.ArgumentParser(description="AI Choir Parts — harmonie parallèle par transposition de ta voix")
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
    if ff:
        print("⚠ ffmpeg introuvable : export WAV.")
    print("\n=== Arrangement ===")
    print(f"  Tu chantes : {FR[his]}{'  (détecté)' if args.part=='auto' else ''}")
    print(f"  Tonalité : {key} | Justesse : {just['avg']} cents ({just['verdict']})")
    for name, path in produced.items():
        print(f"  {name:18s} -> {path}")
    if score:
        print(f"  partition          -> {score[0]}  +  {score[1]}")


if __name__ == "__main__":
    main()
