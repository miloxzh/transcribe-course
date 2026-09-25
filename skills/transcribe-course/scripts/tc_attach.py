# -*- coding: utf-8 -*-
"""Copy a chosen frame into notes/attachments using the naming convention, print the embed.

    python tc.py attach D29_训练计划设计II 01:43 核心原则 --prefix D29
    python tc.py attach shoulder-demo 75 setup-angle
    python tc.py attach D29_训练计划设计II --list

Result: attachments/{prefix}_{mmss}_{description}.jpg, where prefix defaults to the stem.
The source is frames/{stem}/{stem}_{mmss}.jpg (a candidate or a `grab`); pass --from for any file.
The description is a few words with no spaces. The mmss in the file name is the only place a time
may appear outside the hidden section comments.
"""
from __future__ import annotations

import argparse
import shutil
import sys

from tc_common import BAD_NAME_CHARS, add_workspace_arg, die, find_workspace, fmt_stamp, parse_time, say


def main(argv):
    ap = argparse.ArgumentParser(prog="tc attach", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stem", help="frames/{stem} folder (the video stem)")
    ap.add_argument("time", nargs="?", help="mm:ss or seconds of the candidate frame")
    ap.add_argument("desc", nargs="?", help="short description, no spaces")
    ap.add_argument("--prefix", help="attachment prefix (default: stem)")
    ap.add_argument("--from", dest="src", help="explicit source image instead of frames/{stem}/{stem}_{mmss}.jpg")
    ap.add_argument("--list", action="store_true", help="list attachments that start with the prefix")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)
    ws = find_workspace(a.workspace)
    prefix = a.prefix or a.stem

    if a.list:
        for p in sorted(ws.attachments.glob(prefix + "_*")):
            say("  %s   %s" % (p.name, ws.embed(p.name)))
        return 0
    if not a.time or not a.desc:
        die("need <time> and <desc> (or --list)")
    if BAD_NAME_CHARS.search(a.desc) or " " in a.desc:
        die("description must be a short label without spaces or path characters")

    sec = parse_time(a.time)
    src = ws.root / a.src if a.src else ws.frames / a.stem / ("%s_%s.jpg" % (a.stem, fmt_stamp(sec)))
    if not src.exists():
        alt = sorted((ws.frames / a.stem).glob("%s_%s*.jpg" % (a.stem, fmt_stamp(sec))))
        if alt:
            src = alt[0]
        else:
            die("no frame %s. Run `tc.py grab <video> %s` first, or pass --from." % (src, a.time))
    ws.attachments.mkdir(parents=True, exist_ok=True)
    dst = ws.attachments / ("%s_%s_%s%s" % (prefix, fmt_stamp(sec), a.desc, src.suffix.lower()))
    if dst.exists():
        say("exists, kept: %s" % dst.name)
    else:
        shutil.copy2(src, dst)
        say("%s → %s" % (src.name, dst.name))
    say("embed: %s" % ws.embed(dst.name))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
