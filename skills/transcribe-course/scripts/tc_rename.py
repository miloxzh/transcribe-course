# -*- coding: utf-8 -*-
"""Rename a video and everything derived from it (transcript, log, frames folder).

    python tc.py rename v.f421220.mp4 D29_训练计划设计II.mp4
    python tc.py rename "lesson 3.mp4" L03_shoulder-assessment.mp4

Downloaded files are often called v.f421220.mp4 or "main (3).mp4"; the note, its attachments and
the log all key off the stem, so the video gets its proper name right after transcription, once the
title page / opening line reveal what it is. Nothing is ever overwritten or deleted: an existing
target name aborts (it may be a duplicate download — ask the user).
"""
from __future__ import annotations

import argparse
import json
import sys

from tc_common import BAD_NAME_CHARS, add_workspace_arg, die, find_workspace, read_text, say, write_text


def main(argv):
    ap = argparse.ArgumentParser(prog="tc rename", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", help="current file name (inside videos/) or path")
    ap.add_argument("new", help="new file name (extension optional)")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)
    ws = find_workspace(a.workspace)

    src = ws.resolve_video(a.old)
    new = a.new
    if "." not in new or new.rsplit(".", 1)[1].lower() not in ("mp4", "mkv", "mov", "webm", "m4a", "mp3", "wav", "flv", "ts"):
        new += src.suffix
    if BAD_NAME_CHARS.search(new):
        die("new name contains characters Windows does not allow: %s" % new)
    if " " in new:
        say("⚠ new name contains spaces; embeds and links are more robust without them")
    dst = src.with_name(new)
    if dst.exists():
        die("target exists, not overwriting: %s (duplicate download? ask the user)" % dst)
    src.rename(dst)
    say("video       %s → %s" % (src.name, dst.name))

    o, n = src.stem, dst.stem
    moved = 0
    if ws.transcripts.is_dir():
        for f in sorted(ws.transcripts.iterdir()):
            if f.stem == o and f.suffix in (".json", ".txt", ".log"):
                target = f.with_name(n + f.suffix)
                if target.exists():
                    say("  ⚠ kept (target exists): %s" % target.name)
                    continue
                f.rename(target)
                moved += 1
                say("transcript  %s → %s" % (f.name, target.name))
                if target.suffix == ".json":
                    try:
                        d = json.loads(read_text(target))
                        if isinstance(d, dict) and d.get("source"):
                            d["source"] = dst.name
                            write_text(target, json.dumps(d, ensure_ascii=False, indent=1))
                    except Exception:  # noqa: BLE001
                        pass
    if not moved:
        say("  (no transcript named %s.* yet)" % o)

    fo, fn = ws.frames / o, ws.frames / n
    if fo.is_dir() and not fn.exists():
        fo.rename(fn)
        say("frames      %s/ → %s/  (candidate files inside keep the old prefix; rerun `frames` with the new name if you need them renamed)" % (o, n))
    say("done. From here on use stem = %s" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
