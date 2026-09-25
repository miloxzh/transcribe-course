# -*- coding: utf-8 -*-
"""The gate: mechanical verify + transcript coverage + random spot checks.

    python tc.py check transcripts/D03.json notes/D03_周期化训练.md
    python tc.py check transcripts/D03.json notes/D03_a.md notes/D03_b.md   # compare drafts side by side

Coverage answers "is everything the speaker said in the note?" without trusting word counts:
for every transcript segment of at least 8 characters (CJK) or 6 words (other languages), take
its 4-character shingles (or 3-word shingles) and look for any of them in the note body.
A verbatim note scores close to 100 %; a thematic summary scores far lower. Segments that miss
are listed so they can be put back into the right section.

Random spot checks print three transcript lines and the note section that covers those seconds,
for a human (or the calling agent) to judge verbatim vs paraphrased.

Exit code 1 when verify FAILs or coverage is below the workspace threshold (default 0.97).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

from tc_common import (add_workspace_arg, find_workspace, fmt_mmss, h3_stamps, is_cjk_text, norm_text, read_text, say,
                       split_frontmatter)
import tc_verify

WORD_RE = re.compile(r"[a-z0-9']+")


def coverage(segments, body):
    text_all = "".join(s["text"] for s in segments)
    cjk = is_cjk_text(text_all)
    hit, tot, misses = 0, 0, []
    if cjk:
        nb = norm_text(body)
        for s in segments:
            t = norm_text(s["text"])
            if len(t) < 8:
                continue
            tot += 1
            grams = {t[i:i + 4] for i in range(len(t) - 3)}
            if any(g in nb for g in grams):
                hit += 1
            else:
                misses.append(s)
    else:
        nb = " " + " ".join(WORD_RE.findall(body.lower())) + " "
        for s in segments:
            words = WORD_RE.findall(s["text"].lower())
            if len(words) < 6:
                continue
            tot += 1
            grams = {" %s " % " ".join(words[i:i + 3]) for i in range(len(words) - 2)}
            if any(g in nb for g in grams):
                hit += 1
            else:
                misses.append(s)
    return hit, tot, misses, cjk


def section_at(body: str, sec: int) -> str:
    stamps = h3_stamps(body)
    lines = body.split("\n")
    for i, (title, a, b, ln) in enumerate(stamps):
        if a <= sec <= b:
            end = stamps[i + 1][3] - 1 if i + 1 < len(stamps) else len(lines)
            return "\n".join(lines[ln - 1:end]).strip()
    return "(no stamped section covers %s)" % fmt_mmss(sec)


def main(argv):
    ap = argparse.ArgumentParser(prog="tc check", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript", help="transcripts/{stem}.json")
    ap.add_argument("notes", nargs="+", help="one or more note files")
    ap.add_argument("--threshold", type=float, default=None, help="coverage gate (default from config, 0.97)")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--misses", type=int, default=8, help="how many missed segments to list")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)
    ws = find_workspace(a.workspace)
    thr = a.threshold if a.threshold is not None else float(ws.cfg.get("coverage_threshold", 0.97))

    data = json.loads(read_text(a.transcript))
    segs = data["segments"]
    say("transcript: %d segments, %d chars (normalised)\n" % (len(segs), sum(len(norm_text(s["text"])) for s in segs)))

    gate_ok = True
    say("=" * 70)
    say("[verify]")
    bodies = {}
    for n in a.notes:
        p = Path(n)
        fails, warns, info = tc_verify.run(p, ws)
        say("%s | type %s | chars %s | sections %s | images %s" % (
            p.name, info.get("type", "?"), info.get("chars", "?"), info.get("sections", "?"), info.get("images", "?")))
        for f in fails:
            say("  FAIL " + f)
        for w in warns:
            say("  WARN " + w)
        say("  PASS" if not fails else "  → %d FAIL" % len(fails))
        if fails:
            gate_ok = False
        _, body = split_frontmatter(read_text(p))
        bodies[n] = body

    say("\n" + "=" * 70)
    say("[coverage] share of transcript segments whose shingles appear in the note")
    results = {}
    for n in a.notes:
        h, t, miss, cjk = coverage(segs, bodies[n])
        rate = h / max(t, 1)
        results[n] = rate
        say("  %-36s %4d/%4d = %5.1f%%  (%s shingles; body %d chars)" % (
            Path(n).name[:36], h, t, 100 * rate, "4-char" if cjk else "3-word", len(norm_text(bodies[n]))))
        if rate < thr:
            gate_ok = False
        for s in miss[:a.misses]:
            say("     miss %s  %s" % (fmt_mmss(s["start"]), s["text"].strip()[:70]))
        if len(miss) > a.misses:
            say("     … %d more" % (len(miss) - a.misses))

    say("\n" + "=" * 70)
    say("[spot checks] transcript line vs the note section covering that second")
    random.seed(8)
    cands = [s for s in segs if len(norm_text(s["text"])) >= 15 and 30 < s["start"] < (segs[-1]["start"] - 30 if segs else 0)]
    for s in random.sample(cands, min(a.samples, len(cands))):
        sec = int(s["start"])
        say("\n--- %s transcript: %s" % (fmt_mmss(sec), s["text"].strip()))
        for n in a.notes:
            txt = section_at(bodies[n], sec)
            say("  [%s]\n    %s" % (Path(n).name, txt[:420].replace("\n", "\n    ")))

    say("\n" + "=" * 70)
    worst = min(results.values()) if results else 0.0
    say("GATE %s | verify %s | coverage %.1f%% (threshold %.0f%%)" % (
        "PASS" if gate_ok else "FAIL", "ok" if all(not tc_verify.run(Path(n), ws)[0] for n in a.notes) else "FAIL", 100 * worst, 100 * thr))
    return 0 if gate_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
