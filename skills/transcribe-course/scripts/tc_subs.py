# -*- coding: utf-8 -*-
"""Burned-in subtitle strips around given times, to settle doubtful words.

    python tc.py subs videos/lesson03.mp4 00:08 13:42 20:33
    python tc.py subs videos/demo.mp4 1:02 --band 0.70,0.95 --span 6

For each time, frames from (t - before) to (t + span) every `step` seconds are cropped to the
subtitle band and stacked vertically with the time on the left, one image per time:
frames/{stem}/subs/subs_{mmss}.jpg. Read the image, compare with the transcript, decide.

Why this step exists: subtitles burned in by the editor were proofread by a human. When Whisper
heard "训组分配" the subtitle said "训练分配" — and the guess made from context ("训练量分配")
was wrong too. If a word can be checked, check it; do not guess.
"""
from __future__ import annotations

import argparse
import sys

from tc_common import add_workspace_arg, find_ffmpeg, find_font, find_workspace, fmt_stamp, parse_time, say, stem_of, video_info
from tc_frames import grab_frame


def main(argv):
    ap = argparse.ArgumentParser(prog="tc subs", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("times", nargs="+", help="mm:ss, mm:ss.s or seconds")
    ap.add_argument("--before", type=float, default=1.0, help="seconds before each time (default 1)")
    ap.add_argument("--span", type=float, default=5.0, help="seconds after each time (default 5)")
    ap.add_argument("--step", type=float, default=0.7, help="interval between strips (default 0.7)")
    ap.add_argument("--band", default="0.72,0.98", help="subtitle band as fractions of frame height, top,bottom (default 0.72,0.98; narrow it once you know where the subtitles sit)")
    ap.add_argument("--out", help="folder name under frames/ (default: video stem)")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)

    from PIL import Image, ImageDraw
    ws = find_workspace(a.workspace)
    video = ws.resolve_video(a.video)
    stem = a.out or stem_of(video)
    out = ws.frames / stem / "subs"
    out.mkdir(parents=True, exist_ok=True)
    info = video_info(video)
    w, h = info["width"], info["height"]
    y0, y1 = (float(x) for x in a.band.split(","))
    x0, x1 = int(w * 0.05), int(w * 0.95)
    ffmpeg = find_ffmpeg(ws.cfg)
    font = find_font(18)

    for ts in a.times:
        t0 = parse_time(ts)
        tiles, t = [], max(0.0, t0 - a.before)
        while t <= t0 + a.span + 1e-6:
            frame = grab_frame(video, t, ffmpeg)
            if frame is not None:
                band = frame[int(h * y0):int(h * y1), x0:x1]
                im = Image.fromarray(band[:, :, ::-1])
                lab = Image.new("RGB", (im.width + 110, im.height), (0, 0, 0))
                lab.paste(im, (110, 0))
                mm, ss = divmod(t, 60)
                ImageDraw.Draw(lab).text((6, max(0, im.height // 2 - 12)), "%02d:%04.1f" % (mm, ss), fill=(255, 255, 0), font=font)
                tiles.append(lab)
            t += a.step
        if not tiles:
            say("✗ %s: no frames" % ts)
            continue
        sheet = Image.new("RGB", (max(i.width for i in tiles), sum(i.height for i in tiles)))
        y = 0
        for im in tiles:
            sheet.paste(im, (0, y))
            y += im.height
        dst = out / ("subs_%s.jpg" % fmt_stamp(t0))
        sheet.save(dst, quality=90)
        say("%s → %s (%d strips)" % (ts, dst, len(tiles)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
