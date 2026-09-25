# -*- coding: utf-8 -*-
"""Whisper transcription with faster-whisper (GPU when available).

    python tc.py transcribe videos/lesson03.mp4
    python tc.py transcribe videos/lesson03.mp4 --out D03_周期化训练 --language zh
    python tc.py transcribe lecture.m4a --device cpu --model large-v3-turbo

Output: transcripts/{stem}.json (segments with timestamps), transcripts/{stem}.txt (mm:ss  text)
and transcripts/{stem}.log (this console output). Audio is decoded by PyAV, so ffmpeg is not needed.

Decoding parameters are deliberately conservative — see the comments in transcribe():
the temperature fallback chain and condition_on_previous_text=False are what keep the model
from collapsing into a repeated sentence for the rest of the file.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

from tc_common import add_workspace_arg, find_workspace, media_duration, read_text, say, stem_of, write_text


# ------------------------------------------------------------ CUDA on Windows --
def preload_cuda_dlls():
    """pip's nvidia-cublas-cu12 / nvidia-cudnn-cu12 put their DLLs in site-packages/nvidia/*/bin,
    which is not on the search path. CTranslate2 loads them lazily, so add_dll_directory alone is
    not enough: the folders go on PATH and the DLLs are preloaded with ctypes. Returns the folders."""
    if sys.platform != "win32":
        return []
    import ctypes
    import site
    roots = []
    try:
        roots += site.getsitepackages()
    except Exception:  # noqa: BLE001
        pass
    try:
        roots.append(site.getusersitepackages())
    except Exception:  # noqa: BLE001
        pass
    roots.append(os.path.join(os.path.dirname(os.__file__), "site-packages"))
    dirs = []
    for r in roots:
        dirs += glob.glob(os.path.join(r, "nvidia", "*", "bin"))
    dirs = sorted(set(dirs))
    if not dirs:
        return []
    os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ.get("PATH", "")
    for d in dirs:
        try:
            os.add_dll_directory(d)
        except (OSError, AttributeError):
            pass
    for pat in ("cublas64_*.dll", "cublasLt64_*.dll", "cudnn64_*.dll", "cudnn_*64_*.dll"):
        for d in dirs:
            for f in sorted(glob.glob(os.path.join(d, pat))):
                try:
                    ctypes.WinDLL(f)
                except OSError:
                    pass
    return dirs


def pick_device(want: str) -> str:
    if want in ("cuda", "cpu"):
        if want == "cuda":
            preload_cuda_dlls()
        return want
    preload_cuda_dlls()
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"


def load_model(model_name: str, device: str):
    from faster_whisper import WhisperModel
    compute = "float16" if device == "cuda" else "int8"
    return WhisperModel(model_name, device=device, compute_type=compute)


# --------------------------------------------------------------------- vocab --
def load_vocab(path: Path, language: str) -> str:
    """vocab.txt: one term per line (comma-separated lines are fine too). Joined into one prompt."""
    if not path.exists():
        return ""
    terms = []
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        terms += [t.strip() for t in re.split(r"[,，;；]", line) if t.strip()]
    sep = "，" if language and language.startswith("zh") else ", "
    return sep.join(terms)


class Tee:
    def __init__(self, path: Path):
        self.f = open(path, "a", encoding="utf-8")
        self.out = sys.stdout

    def write(self, s):
        self.out.write(s)
        self.f.write(s)

    def flush(self):
        self.out.flush()
        self.f.flush()


# ---------------------------------------------------------------- transcribe --
def transcribe(model, source: Path, language: str | None, vocab: str):
    # Never pass temperature=0 alone: that disables the fallback chain and a repetition loop
    # then runs to the end of the file (seen once: 281 identical segments after minute 15).
    # condition_on_previous_text=False stops the model from feeding its own output back as context.
    return model.transcribe(
        str(source),
        language=language,
        beam_size=5,
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        condition_on_previous_text=False,
        compression_ratio_threshold=2.4,
        no_repeat_ngram_size=4,
        initial_prompt=vocab or None,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )


def loop_check(segments):
    """Two shapes of hallucination loop: identical neighbouring segments, and a phrase
    repeated 4+ times inside one segment. Returns (longest_run, example, inner_count, inner_example)."""
    run = best = 1
    best_txt = ""
    for a, b in zip(segments, segments[1:]):
        same = a["text"].strip() and a["text"].strip() == b["text"].strip()
        run = run + 1 if same else 1
        if run > best:
            best, best_txt = run, b["text"].strip()
    inner = [s for s in segments if re.search(r"(.{2,12}?)\1{3,}", s["text"])]
    return best, best_txt, len(inner), (inner[0]["text"].strip() if inner else "")


def main(argv):
    ap = argparse.ArgumentParser(prog="tc transcribe", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", help="video/audio file (path, or a name inside videos/)")
    ap.add_argument("--out", help="output stem (default: the file's own stem)")
    ap.add_argument("--model", help="override the model (large-v3, large-v3-turbo, medium, ...)")
    ap.add_argument("--device", choices=["auto", "cuda", "cpu"], help="override config device")
    ap.add_argument("--language", help="override config language (code or 'auto')")
    ap.add_argument("--no-vocab", action="store_true", help="do not pass vocab.txt as the initial prompt")
    ap.add_argument("--force", action="store_true", help="overwrite an existing transcript")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)

    ws = find_workspace(a.workspace)
    ws.ensure_dirs()
    src = ws.resolve_video(a.video)
    stem = a.out or stem_of(src)
    out_json = ws.transcripts / (stem + ".json")
    if out_json.exists() and not a.force:
        say("transcript exists: %s (use --force to redo)" % out_json)
        return 0
    log_path = ws.transcripts / (stem + ".log")
    if log_path.exists():
        log_path.unlink()
    sys.stdout = Tee(log_path)

    device = pick_device(a.device or ws.cfg["device"])
    model_name = a.model or (ws.cfg["whisper_model"] if device == "cuda" else ws.cfg["cpu_model"])
    if device == "cpu" and not a.model and ws.cfg["whisper_model"] != ws.cfg["cpu_model"]:
        say("⚠ no GPU: using %s on CPU (int8). Expect 1–2× the video length. Pass --model to override." % model_name)
    lang_cfg = a.language or ws.cfg["language"]
    language = None if (not lang_cfg or lang_cfg == "auto") else lang_cfg
    vocab = "" if a.no_vocab else load_vocab(ws.vocab_file, language or "")
    if vocab and len(vocab) > 700:
        say("⚠ vocab prompt is long (%d chars); Whisper keeps only the last ~224 tokens, keep the important terms at the end." % len(vocab))

    dur = media_duration(src) or 0.0
    say("source  %s" % src)
    say("audio   %.1f min | model %s | device %s | language %s | vocab %d chars" % (
        dur / 60, model_name, device, language or "auto", len(vocab)))

    t0 = time.time()
    try:
        model = load_model(model_name, device)
    except Exception as e:  # noqa: BLE001
        say("✗ could not load model: %s" % e)
        return 2
    say("model loaded in %.0f s" % (time.time() - t0))

    t1 = time.time()
    out = []
    try:
        segs, info = transcribe(model, src, language, vocab)
        for s in segs:
            out.append({"id": len(out), "start": round(s.start, 2), "end": round(s.end, 2), "text": s.text})
            if len(out) % 50 == 0:
                say("  %d segments / %.1f min…" % (len(out), s.end / 60))
    except Exception as e:  # noqa: BLE001
        say("✗ transcription failed: %s" % e)
        if device == "cuda" and any(k in str(e).lower() for k in ("cublas", "cudnn", "cuda")):
            say("  → Windows: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 ; or run with --device cpu")
        return 2
    el = time.time() - t1
    if not dur:
        dur = getattr(info, "duration", 0.0) or 0.0
    text = "".join(s["text"] for s in out)
    bad = text.count("�")
    best, best_txt, n_inner, inner_txt = loop_check(out)

    write_text(out_json, json.dumps({
        "text": text, "segments": out, "language": getattr(info, "language", language),
        "model": model_name, "device": device, "source": src.name, "duration": round(dur, 2),
    }, ensure_ascii=False, indent=1))
    lines = ["%02d:%02d  %s" % (int(s["start"]) // 60, int(s["start"]) % 60, s["text"].strip()) for s in out]
    write_text(out_json.with_suffix(".txt"), "\n".join(lines) + "\n")

    say("done %.0f s (%.1fx realtime) | segments %d | chars %d | U+FFFD %d" % (
        el, (dur / el) if el else 0, len(out), len(text), bad))
    say("loop check: longest run of identical segments %d | segments with inner repeats %d" % (best, n_inner))
    status = "ok"
    if best >= 5 or n_inner >= 3:
        status = "SUSPECT-LOOP"
        say("⚠ suspected hallucination loop (e.g. %r). Check the decoding parameters were not changed"
            " (temperature fallback chain must stay) and rerun; try --no-vocab if it persists." % (best_txt or inner_txt)[:40])
    if bad > 20:
        status = "BAD-DECODE" if status == "ok" else status
        say("⚠ %d replacement characters: the decode went wrong, rerun (a handful is normal)." % bad)
    if not out:
        status = "EMPTY"
        say("⚠ no segments: wrong language code, or the file has no speech track.")
    say("RESULT %s | %s" % (status, out_json))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
