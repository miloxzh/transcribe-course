# -*- coding: utf-8 -*-
"""Create a workspace: folders, config, vocabulary and terms files.

    python tc.py init ~/rehab-course --preset rehab-zh --course "肩关节康复课"
    python tc.py init ./my-course --preset generic-en --language en --note-language en --flavor markdown

Presets (vocabulary seeds for Whisper's initial prompt) live in references/presets/.
Existing files are never overwritten; re-running init only adds what is missing.
"""
import argparse
import json
from pathlib import Path

from tc_common import CONFIG_NAME, DEFAULTS, PRESET_DIR, die, load_workspace, read_text, say, write_text

HOWTO = {
    "zh": """# 这个文件夹怎么用

这是 transcribe-course 的工作区。把课程视频放进 `videos/`，然后在 Claude Code 里输入：

    /transcribe-course videos/文件名.mp4

流程会依次产出：`transcripts/`（转写）、`frames/`（候选画面与览图）、`notes/`（成稿）、`notes/attachments/`（贴进笔记的图）。

可以随手改的三个文件：
- `vocab.txt`：这门课的术语，每行一个，转写前喂给 Whisper（越靠后的词权重越大，保持精简）。
- `terms.tsv`：已知的听错写法 → 正确写法，一行一对，制表符分隔。成稿时自动替换并记进 frontmatter。
- `transcribe-course.json`：语言、模板语言、Obsidian 还是普通 Markdown、模型与设备等。

`log.md` 是每节课一行的进度记录。`templates/` 目录（可选）里同名模板会覆盖自带模板。
""",
    "en": """# How to use this folder

This is a transcribe-course workspace. Drop course videos into `videos/`, then in Claude Code run:

    /transcribe-course videos/<file>.mp4

The pipeline writes `transcripts/` (Whisper output), `frames/` (candidate frames + contact sheets),
`notes/` (finished notes) and `notes/attachments/` (frames embedded in notes).

Three files you are expected to edit:
- `vocab.txt`: course terminology, one term per line, fed to Whisper as its initial prompt
  (later lines carry more weight; keep it short).
- `terms.tsv`: known mis-hearings -> correct spelling, one pair per line, tab-separated.
  Applied automatically to notes and recorded in the frontmatter.
- `transcribe-course.json`: language, template language, Obsidian vs plain Markdown, model, device.

`log.md` keeps one line per lesson. An optional `templates/` folder overrides the built-in note templates.
""",
}


def list_presets():
    return sorted(p.stem for p in PRESET_DIR.glob("*.txt"))


def main(argv):
    ap = argparse.ArgumentParser(prog="tc init", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", default=".", help="workspace folder to create or complete (default: current)")
    ap.add_argument("--preset", default=None, help="vocabulary preset: %s" % ", ".join(list_presets()))
    ap.add_argument("--course", default="", help="short course name for tags and the log")
    ap.add_argument("--language", default=None, help="Whisper language code (zh, en, ja, ...) or auto")
    ap.add_argument("--note-language", default=None, choices=["zh", "en"], help="template set for the notes")
    ap.add_argument("--flavor", default=None, choices=["obsidian", "markdown"], help="embed/comment syntax")
    ap.add_argument("--model", default=None, help="Whisper model on GPU (default large-v3)")
    ap.add_argument("--ffmpeg", default=None, help="path to ffmpeg if it is not on PATH")
    ap.add_argument("--list-presets", action="store_true")
    a = ap.parse_args(argv)

    if a.list_presets:
        for p in list_presets():
            first = read_text(PRESET_DIR / (p + ".txt")).strip().split("\n")[0]
            say("  %-14s %s" % (p, first.lstrip("# ").strip()))
        return 0

    root = Path(a.folder).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    cfg_path = root / CONFIG_NAME

    if cfg_path.exists():
        cfg = json.loads(read_text(cfg_path) or "{}")
        say("config exists, keeping it: %s" % cfg_path)
    else:
        cfg = json.loads(json.dumps(DEFAULTS))
        cfg.pop("banned_words", None)          # None is not useful in a file; language default applies
        cfg.pop("declaration_alternatives", None)
        cfg["course"] = a.course
        preset = a.preset or "generic-zh"
        if preset.endswith("-en"):
            cfg["language"], cfg["note_language"] = "en", "en"
        if a.language:
            cfg["language"] = a.language
        if a.note_language:
            cfg["note_language"] = a.note_language
        if a.flavor:
            cfg["flavor"] = a.flavor
        if a.model:
            cfg["whisper_model"] = a.model
        if a.ffmpeg:
            cfg["ffmpeg"] = a.ffmpeg
        write_text(cfg_path, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
        say("wrote %s" % cfg_path)

    ws = load_workspace(root)
    ws.ensure_dirs()

    preset = a.preset or ("generic-en" if ws.cfg.get("language") == "en" else "generic-zh")
    src = PRESET_DIR / (preset + ".txt")
    if not src.exists():
        die("unknown preset %r; available: %s" % (preset, ", ".join(list_presets())))
    if not ws.vocab_file.exists():
        write_text(ws.vocab_file, read_text(src))
        say("wrote %s (preset %s)" % (ws.vocab_file, preset))
    if not ws.terms_file.exists():
        terms_src = PRESET_DIR / (preset + ".terms.tsv")
        header = ("# wrong<TAB>right — one pair per line. Only add pairs that cannot mean anything else in this course.\n"
                  "# Lines starting with # are ignored. Applied by `tc.py terms`, recorded in frontmatter term_fixes.\n")
        body = read_text(terms_src) if terms_src.exists() else ""
        write_text(ws.terms_file, header + body)
        say("wrote %s" % ws.terms_file)
    if not ws.log_file.exists():
        write_text(ws.log_file, "# transcribe-course log\n\n")
    howto = root / "HOWTO.md"
    if not howto.exists():
        write_text(howto, HOWTO.get(ws.note_language, HOWTO["en"]))

    say("")
    say("workspace ready: %s" % root)
    say("  videos/        put course videos here")
    say("  vocab.txt      %d lines of terminology (edit freely)" % len(read_text(ws.vocab_file).splitlines()))
    say("  terms.tsv      known mis-hearings (starts %s)" % ("with preset examples" if (PRESET_DIR / (preset + ".terms.tsv")).exists() else "empty"))
    say("next: python tc.py doctor   (checks packages, GPU and ffmpeg)")
    return 0
