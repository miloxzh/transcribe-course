# -*- coding: utf-8 -*-
"""Environment check with fix hints.

    python tc.py doctor            # packages, GPU, ffmpeg, font, workspace
    python tc.py doctor --full     # also runs a real 3-second Whisper inference on the chosen device
                                   # (downloads the model on first use: large-v3 ≈ 3 GB, large-v3-turbo ≈ 1.6 GB)

Why --full exists: on Windows, CTranslate2 can construct a CUDA model and only fail when it
first encodes audio (missing cublas/cudnn DLLs). Only a real inference proves the GPU path.
"""
import argparse
import importlib
import os
import platform
import sys
from pathlib import Path

from tc_common import CONFIG_NAME, find_ffmpeg, find_font, find_workspace, say

PKGS = [
    ("faster_whisper", "faster-whisper", "pip install faster-whisper"),
    ("ctranslate2", "ctranslate2", "pip install ctranslate2   (installed with faster-whisper)"),
    ("av", "av (PyAV, decodes audio without ffmpeg)", "pip install av"),
    ("cv2", "opencv-python", "pip install opencv-python"),
    ("numpy", "numpy", "pip install numpy"),
    ("PIL", "Pillow", "pip install Pillow"),
]


def check_packages():
    ok = True
    for mod, label, fix in PKGS:
        try:
            m = importlib.import_module(mod)
            say("  ✓ %-42s %s" % (label, getattr(m, "__version__", "")))
        except Exception as e:  # noqa: BLE001
            ok = False
            say("  ✗ %-42s missing  → %s" % (label, fix))
    return ok


def check_gpu():
    from tc_transcribe import preload_cuda_dlls
    dirs = preload_cuda_dlls()
    try:
        import ctranslate2
        n = ctranslate2.get_cuda_device_count()
    except Exception as e:  # noqa: BLE001
        say("  ✗ ctranslate2 CUDA probe failed: %s" % e)
        return False
    if n > 0:
        say("  ✓ CUDA device(s): %d  (large-v3 float16 will be used)" % n)
        if sys.platform == "win32":
            if dirs:
                say("    cuBLAS/cuDNN DLL folders preloaded: %d" % len(dirs))
            else:
                say("    ⚠ no site-packages/nvidia/*/bin folders found. If transcription fails with"
                    " 'cublas64_12.dll is not found': pip install nvidia-cublas-cu12 nvidia-cudnn-cu12")
        return True
    say("  – no CUDA device visible to CTranslate2: CPU mode (int8, model %s)." % "large-v3-turbo")
    say("    A 20-minute lesson takes roughly 15–40 minutes on CPU instead of 1–2 minutes on a GPU.")
    if platform.machine().lower() in ("arm64", "aarch64") and sys.platform == "darwin":
        say("    Apple Silicon: faster-whisper runs on CPU only; that is expected.")
    else:
        say("    NVIDIA GPU present but not seen? pip install nvidia-cublas-cu12 nvidia-cudnn-cu12, then rerun.")
    return False


def check_model_cache():
    home = Path(os.environ.get("HF_HOME") or (Path.home() / ".cache" / "huggingface")) / "hub"
    found = sorted(p.name for p in home.glob("models--*faster-whisper*")) if home.exists() else []
    if found:
        say("  ✓ Whisper models already downloaded: %s" % ", ".join(n.replace("models--", "") for n in found))
    else:
        say("  – no faster-whisper model downloaded yet; the first transcription downloads it"
            " (large-v3 ≈ 3 GB, large-v3-turbo ≈ 1.6 GB) into %s" % home)


def check_ffmpeg(cfg):
    ff = find_ffmpeg(cfg)
    if ff:
        say("  ✓ ffmpeg: %s" % ff)
        return True
    say("  – ffmpeg not found (optional). Transcription, frames and subtitle strips work without it;")
    say("    it only speeds up sequential frame extraction for AV1/VP9 videos.")
    say("    Install: winget install Gyan.FFmpeg | brew install ffmpeg | apt install ffmpeg | pip install imageio-ffmpeg")
    return False


def check_font():
    f = find_font(16)
    name = getattr(f, "path", None) or type(f).__name__
    say("  ✓ label font: %s" % name)
    if "load_default" in name or name == "FreeTypeFont" and not getattr(f, "path", None):
        say("    (default font: non-Latin labels on contact sheets may show as boxes; timestamps are fine)")


def check_workspace(explicit):
    ws = find_workspace(explicit, required=False)
    if not ws:
        say("  – no workspace found from here (no %s). `python tc.py init <folder>` creates one." % CONFIG_NAME)
        return None
    say("  ✓ workspace: %s" % ws.root)
    say("    language=%s  note_language=%s  flavor=%s  model=%s  device=%s" % (
        ws.cfg["language"], ws.note_language, ws.flavor, ws.cfg["whisper_model"], ws.cfg["device"]))
    for label, p in (("videos", ws.videos), ("transcripts", ws.transcripts), ("frames", ws.frames),
                     ("notes", ws.notes), ("attachments", ws.attachments)):
        say("    %-12s %s %s" % (label, "✓" if p.is_dir() else "✗ missing", p))
    n = len(ws.templates_by_type())
    say("    templates: %d note type(s): %s" % (n, ", ".join(ws.templates_by_type().keys())))
    if not ws.vocab_file.exists():
        say("    ⚠ vocab file missing: %s" % ws.vocab_file)
    return ws


def full_inference(ws):
    """Real inference on a synthetic 3-second tone: proves DLLs, device and model download."""
    import numpy as np
    from tc_transcribe import load_model, pick_device
    device = pick_device((ws.cfg["device"] if ws else "auto"))
    model_name = (ws.cfg["whisper_model"] if ws else "large-v3") if device == "cuda" else (ws.cfg["cpu_model"] if ws else "large-v3-turbo")
    say("  loading %s on %s (first time downloads the model)…" % (model_name, device))
    try:
        model = load_model(model_name, device)
        sr = 16000
        t = np.arange(sr * 3) / sr
        audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        segs, info = model.transcribe(audio, beam_size=1, vad_filter=False)
        n = sum(1 for _ in segs)
        say("  ✓ inference ran on %s (%d segment(s) from a test tone — content is irrelevant)" % (device, n))
        return True
    except Exception as e:  # noqa: BLE001
        say("  ✗ inference failed: %s" % e)
        if "cublas" in str(e).lower() or "cudnn" in str(e).lower():
            say("    → pip install nvidia-cublas-cu12 nvidia-cudnn-cu12  (Windows CUDA runtime DLLs)")
        return False


def main(argv):
    ap = argparse.ArgumentParser(prog="tc doctor", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="run a real short inference (downloads the model if needed)")
    ap.add_argument("--workspace", default=None)
    a = ap.parse_args(argv)

    say("transcribe-course doctor")
    say("Python %s on %s %s" % (platform.python_version(), platform.system(), platform.machine()))
    if sys.version_info < (3, 9):
        say("  ✗ Python 3.9+ required")
    say("\n[packages]")
    pk = check_packages()
    say("\n[GPU]")
    gpu = check_gpu() if pk else False
    say("\n[models]")
    check_model_cache()
    say("\n[workspace]")
    ws = check_workspace(a.workspace)
    say("\n[ffmpeg]")
    check_ffmpeg(ws.cfg if ws else None)
    say("\n[fonts]")
    check_font()
    if a.full:
        say("\n[inference]")
        full_inference(ws)
    say("")
    say("summary: packages %s | GPU %s | ffmpeg %s" % (
        "ok" if pk else "MISSING", "yes" if gpu else "no (CPU)", "yes" if find_ffmpeg(ws.cfg if ws else None) else "no (optional)"))
    return 0 if pk else 1
