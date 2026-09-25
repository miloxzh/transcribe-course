# -*- coding: utf-8 -*-
"""transcribe-course command line: one entry point, one sub-command per pipeline step.

    python tc.py <command> [options]

Commands
  doctor      check Python packages, GPU, ffmpeg, fonts, workspace
  init        create a workspace folder (config, vocab, terms, folders)
  transcribe  Whisper transcription -> transcripts/{stem}.json + .txt (+ .log)
  frames      candidate frames (slide changes + live cuts) -> frames/{stem}/ + contact sheets
  grab        full-resolution frame(s) at given times -> frames/{stem}/
  subs        burned-in subtitle strips around given times, for resolving doubtful words
  rename      rename a video and every artifact derived from it
  attach      copy a chosen frame into notes/attachments with the naming convention
  verify      mechanical checks on one note (template headings, frontmatter, timestamps, embeds)
  check       verify + transcript coverage + random spot checks  (the gate)
  strip       remove leftover timestamps from a note body
  terms       apply the workspace terms.tsv (known mis-hearings) to a note
  log         append a line to the workspace log.md

Run `python tc.py <command> --help` for that command's options.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

COMMANDS = {
    "doctor": ("tc_doctor", "main"),
    "init": ("tc_init", "main"),
    "transcribe": ("tc_transcribe", "main"),
    "frames": ("tc_frames", "main"),
    "grab": ("tc_frames", "grab_main"),
    "subs": ("tc_subs", "main"),
    "rename": ("tc_rename", "main"),
    "attach": ("tc_attach", "main"),
    "verify": ("tc_verify", "main"),
    "check": ("tc_check", "main"),
    "strip": ("tc_strip", "main"),
    "terms": ("tc_terms", "main"),
    "log": ("tc_log", "main"),
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    from tc_common import setup_stdout
    setup_stdout()
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd not in COMMANDS:
        print("unknown command: %s\n" % cmd)
        print(__doc__)
        return 2
    mod_name, fn_name = COMMANDS[cmd]
    mod = importlib.import_module(mod_name)
    rc = getattr(mod, fn_name)(argv[1:])
    return int(rc or 0)


if __name__ == "__main__":
    sys.exit(main())
