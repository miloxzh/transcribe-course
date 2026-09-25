# -*- coding: utf-8 -*-
"""Candidate frames + contact sheets, so a reader can pick what belongs in the note.

    python tc.py frames videos/lesson03.mp4                 # auto method, default thresholds
    python tc.py frames videos/lesson03.mp4 --frac 0.005    # slides with tiny changes (dark theme, small text)
    python tc.py frames videos/demo.mp4 --overview 3        # also an every-3-seconds overview (demo videos)
    python tc.py grab videos/demo.mp4 75,126,489.5          # full-resolution frames at given seconds / mm:ss

Two detectors run on a one-frame-per-second sample and are merged:

  slide  — for lecture slides. The bottom 20 % (burned-in subtitles change every few seconds) is
           masked, then the fraction of pixels that changed since the previous second is measured.
           A page change = a spike above --frac followed by stillness (< --stable). For each page the
           LAST still second before the next change is kept: that is the page in its most complete
           state (bullet-by-bullet animations included).
  live   — for people on camera (exercise demos). Mean grey-level difference to the last kept frame
           above --thr, at least 2 s apart, taking the frame one second after the cut.
           Live candidates inside a still slide range are dropped (the slide already covers them).

Sampling method (--method):
  seek        one seek per second with OpenCV. Fast for H.264/HEVC.
  sequential  decode every frame in order. Required for AV1/VP9 (seeking re-decodes from a keyframe
              each time and can take 10+ minutes). Uses ffmpeg if available (optionally --hwaccel cuda),
              otherwise OpenCV. Chosen automatically when the codec is av01/vp09.

Output in frames/{stem}/: {stem}_{mmss}.jpg candidates at full resolution, _sheet_N.jpg contact
sheets (12 per sheet, labelled mm:ss + detector), _candidates.tsv, and _overview_N.jpg when --overview.
"""
from __future__ import annotations

import argparse
import io
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tc_common import (add_workspace_arg, die, find_ffmpeg, find_font, find_workspace, fmt_mmss, fmt_stamp,
                       imread_any, imwrite_jpg, parse_time, say, stem_of, video_info)

SEQUENTIAL_CODECS = {"av01", "vp09", "vp90", "vp08"}


# ------------------------------------------------------------------ sampling --
def _features(frame):
    """(masked 192x96 int16 for the slide detector, 96x54 float32 for the live detector, jpeg thumb bytes)"""
    import cv2
    import numpy as np
    h = frame.shape[0]
    g_top = cv2.cvtColor(frame[: int(h * 0.80)], cv2.COLOR_BGR2GRAY)
    m = cv2.resize(g_top, (192, 96), interpolation=cv2.INTER_AREA).astype(np.int16)
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    s = cv2.resize(g, (96, 54), interpolation=cv2.INTER_AREA).astype(np.float32)
    tw = 320
    th = max(1, int(frame.shape[0] * tw / max(frame.shape[1], 1)))
    thumb = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return m, s, (buf.tobytes() if ok else b"")


def sample_seek(video: Path, total_secs: int, progress):
    import cv2
    cap = cv2.VideoCapture(str(video))
    secs, M, S, T = [], [], [], []
    for t in range(0, total_secs + 1):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        m, s, th = _features(frame)
        secs.append(t); M.append(m); S.append(s); T.append(th)
        progress(t)
    cap.release()
    return secs, M, S, T


def sample_sequential_cv2(video: Path, fps: float, progress):
    import cv2
    cap = cv2.VideoCapture(str(video))
    step = max(1, int(round(fps)))
    secs, M, S, T = [], [], [], []
    idx = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if ok:
                t = idx // step
                m, s, th = _features(frame)
                secs.append(t); M.append(m); S.append(s); T.append(th)
                progress(t)
        idx += 1
    cap.release()
    return secs, M, S, T


def sample_sequential_ffmpeg(video: Path, ffmpeg: str, hwaccel: str, stem: str, fresh: bool, progress):
    tmp = Path(tempfile.gettempdir()) / "transcribe-course" / "fps1" / stem
    if fresh and tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    files = sorted(tmp.glob("*.jpg"))
    if not files:
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
        if hwaccel:
            cmd += ["-hwaccel", hwaccel]
        cmd += ["-i", str(video), "-vf", "fps=1,scale=640:-2", "-q:v", "3", str(tmp / "%06d.jpg")]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            if hwaccel:
                say("  ffmpeg with -hwaccel %s failed, retrying in software" % hwaccel)
                return sample_sequential_ffmpeg(video, ffmpeg, "", stem, True, progress)
            die("ffmpeg extraction failed: %s" % r.stderr.strip()[-400:])
        files = sorted(tmp.glob("*.jpg"))
    secs, M, S, T = [], [], [], []
    for f in files:                                   # file N corresponds to second N-1
        t = int(f.stem) - 1
        frame = imread_any(f)
        if frame is None:
            continue
        m, s, th = _features(frame)
        secs.append(t); M.append(m); S.append(s); T.append(th)
        progress(t)
    return secs, M, S, T


# ----------------------------------------------------------------- detection --
def detect(secs, M, S, frac_thr, stable_thr, live_thr):
    import numpy as np
    n = len(secs)
    frac = np.zeros(n)
    for k in range(1, n):
        frac[k] = float((np.abs(M[k] - M[k - 1]) > 30).mean())

    cuts = [k for k in range(1, n) if frac[k] > frac_thr and (k + 1 >= n or frac[k + 1] < stable_thr)]
    bounds = [0] + cuts + [n]
    slide, static_ranges = [], []
    for a, b in zip(bounds[:-1], bounds[1:]):
        inner = frac[a + 1:b]
        if len(inner) and float(np.median(inner)) >= stable_thr:
            continue                                  # keeps moving inside: a live segment
        j = b - 1
        while j > a and frac[j] >= stable_thr:        # back off fade-outs before the change
            j -= 1
        slide.append((secs[j], "slide", float(frac[b]) if b < n else 0.0))
        static_ranges.append((secs[a], secs[b - 1]))

    live, last_s, last_t = [], None, -10
    for k in range(n):
        t = secs[k]
        d = 999.0 if last_s is None else float(np.abs(S[k] - last_s).mean())
        if d > live_thr and t - last_t >= 2:
            kk = k + 1 if k + 1 < n else k
            live.append((secs[kk], "live", d))
            last_t, last_s = t, S[kk]
        elif last_s is None:
            last_s = S[k]

    def in_static(t):
        return any(a <= t <= b for a, b in static_ranges)

    live = [c for c in live if not in_static(c[0])]
    seen, kept = set(), []
    for c in sorted(slide + live):
        if c[0] in seen:
            continue
        seen.add(c[0])
        kept.append(c)
    return kept, len(cuts)


# ------------------------------------------------------------------ grabbing --
def grab_frame(video: Path, sec: float, ffmpeg: str | None):
    """Full-resolution BGR frame at `sec`. ffmpeg (accurate, fast) when available, else OpenCV seek."""
    import cv2
    import numpy as np
    if ffmpeg:
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", "%.3f" % sec, "-i", str(video),
               "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "2", "-"]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0 and r.stdout:
            img = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                return img
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


# -------------------------------------------------------------------- sheets --
def contact_sheets(out_dir: Path, named, prefix="_sheet", cols=3, rows=4, tw=480, th=290):
    from PIL import Image, ImageDraw
    font = find_font(14)
    per = cols * rows
    pages = math.ceil(len(named) / per) if named else 0
    for p in range(pages):
        batch = named[p * per:(p + 1) * per]
        sheet = Image.new("RGB", (cols * tw, rows * th), "white")
        d = ImageDraw.Draw(sheet)
        for q, (t, kind, name) in enumerate(batch):
            try:
                im = Image.open(out_dir / name)
            except Exception:  # noqa: BLE001
                continue
            im.thumbnail((tw - 8, th - 28))
            x, y = (q % cols) * tw, (q // cols) * th
            sheet.paste(im, (x + 4, y + 24))
            d.rectangle([x, y, x + tw, y + 22], fill="black")
            d.text((x + 6, y + 4), "%s  %s  %s" % (fmt_mmss(t), kind, name), fill="yellow", font=font)
        sheet.save(out_dir / ("%s_%d.jpg" % (prefix, p + 1)), quality=85)
    return pages


def overview_sheets(out_dir: Path, secs, thumbs, step: int, cols=5, rows=4):
    from PIL import Image, ImageDraw
    font = find_font(18)
    picks = [(t, b) for t, b in zip(secs, thumbs) if t % step == 0 and b]
    if not picks:
        return 0
    first = Image.open(io.BytesIO(picks[0][1]))
    tw, th = first.width, first.height + 24
    per = cols * rows
    pages = math.ceil(len(picks) / per)
    for p in range(pages):
        sheet = Image.new("RGB", (cols * tw, rows * th), "white")
        d = ImageDraw.Draw(sheet)
        for q, (t, b) in enumerate(picks[p * per:(p + 1) * per]):
            x, y = (q % cols) * tw, (q // cols) * th
            sheet.paste(Image.open(io.BytesIO(b)), (x, y + 24))
            d.rectangle([x, y, x + tw, y + 22], fill="black")
            d.text((x + 6, y + 2), fmt_mmss(t), fill="yellow", font=font)
        sheet.save(out_dir / ("_overview_%d.jpg" % (p + 1)), quality=85)
    return pages


# ---------------------------------------------------------------------- main --
def main(argv):
    ap = argparse.ArgumentParser(prog="tc frames", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", help="output name under frames/ (default: video stem)")
    ap.add_argument("--method", choices=["auto", "seek", "sequential"], default="auto")
    ap.add_argument("--frac", type=float, default=0.01, help="slide: changed-pixel fraction that counts as a page change (default 0.01)")
    ap.add_argument("--stable", type=float, default=0.003, help="slide: fraction below which the page counts as still (default 0.003)")
    ap.add_argument("--thr", type=float, default=14.0, help="live: mean grey difference for a cut (default 14)")
    ap.add_argument("--overview", type=int, default=0, help="also write overview sheets, one thumbnail every N seconds")
    ap.add_argument("--hwaccel", default=None, help="ffmpeg -hwaccel for sequential mode (e.g. cuda); default from config")
    ap.add_argument("--fresh", action="store_true", help="discard the cached 1-fps extraction")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)

    ws = find_workspace(a.workspace)
    video = ws.resolve_video(a.video)
    stem = a.out or stem_of(video)
    out_dir = ws.frames / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    info = video_info(video)
    total = int(info["duration"])
    ffmpeg = find_ffmpeg(ws.cfg)
    hwaccel = a.hwaccel if a.hwaccel is not None else (ws.cfg.get("hwaccel") or "")

    method = a.method
    if method == "auto":
        method = "sequential" if info["codec"] in SEQUENTIAL_CODECS else "seek"
    say("video  %s | %dx%d %.2f fps | %s | codec %s" % (video.name, info["width"], info["height"], info["fps"], fmt_mmss(total), info["codec"] or "?"))
    say("method %s%s" % (method, " (ffmpeg%s)" % (" -hwaccel " + hwaccel if hwaccel else "") if (method == "sequential" and ffmpeg) else ""))

    last = [-1]

    def progress(t):
        if t // 120 != last[0]:
            last[0] = t // 120
            say("  sampled to %s…" % fmt_mmss(t))

    if method == "seek":
        secs, M, S, T = sample_seek(video, total, progress)
    elif ffmpeg:
        secs, M, S, T = sample_sequential_ffmpeg(video, ffmpeg, hwaccel, stem, a.fresh, progress)
    else:
        secs, M, S, T = sample_sequential_cv2(video, info["fps"], progress)
    if not secs:
        die("no frames could be read from %s" % video)

    kept, n_cuts = detect(secs, M, S, a.frac, a.stable, a.thr)

    for f in os.listdir(out_dir):                      # clear the previous run's candidates and sheets
        if (f.startswith(stem + "_") and f.endswith(".jpg")) or f.startswith("_sheet_") or f.startswith("_overview_"):
            os.remove(out_dir / f)
    rows = ["sec\ttime\tkind\tvalue\tfile"]
    named = []
    for t, kind, val in kept:
        frame = grab_frame(video, t, ffmpeg)
        if frame is None:
            continue
        name = "%s_%s.jpg" % (stem, fmt_stamp(t))
        if imwrite_jpg(out_dir / name, frame):
            named.append((t, kind, name))
            rows.append("%d\t%s\t%s\t%.4f\t%s" % (t, fmt_mmss(t), kind, val, name))
    (out_dir / "_candidates.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    pages = contact_sheets(out_dir, named)
    n_slide = sum(1 for c in named if c[1] == "slide")
    say("candidates %d (slide %d / live %d) → %s" % (len(named), n_slide, len(named) - n_slide, out_dir))
    say("contact sheets %d; page changes detected %d" % (pages, n_cuts))
    if a.overview:
        say("overview sheets %d (every %d s)" % (overview_sheets(out_dir, secs, T, a.overview), a.overview))
    if total > 300 and len(named) < 3:
        say("⚠ %d minutes but only %d candidate(s): possible miss. Look at the sheets, then retry with --frac 0.005,"
            " or use --overview 3 for a demo video without slides." % (total // 60, len(named)))
    return 0


def grab_main(argv):
    ap = argparse.ArgumentParser(prog="tc grab", description="Save full-resolution frames at given times into frames/{stem}/.")
    ap.add_argument("video")
    ap.add_argument("times", help="comma-separated seconds or mm:ss (fractions allowed): 75,02:06,489.5")
    ap.add_argument("--out", help="folder name under frames/ (default: video stem)")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)
    ws = find_workspace(a.workspace)
    video = ws.resolve_video(a.video)
    stem = a.out or stem_of(video)
    out_dir = ws.frames / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg(ws.cfg)
    for tok in a.times.split(","):
        if not tok.strip():
            continue
        sec = parse_time(tok)
        frame = grab_frame(video, sec, ffmpeg)
        if frame is None:
            say("✗ no frame at %s" % tok)
            continue
        name = "%s_%s%s.jpg" % (stem, fmt_stamp(sec), ("_%d" % round((sec % 1) * 10)) if sec % 1 else "")
        imwrite_jpg(out_dir / name, frame)
        say("%s → %s" % (tok, out_dir / name))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
