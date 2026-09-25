# transcribe-course

**Course videos → notes you can read instead of watching.**

A [Claude Code](https://claude.com/claude-code) skill, two subagents and a small Python toolkit that
together turn a lecture recording or an exercise demo into a verbatim-level Markdown note with the
important frames embedded:

1. **Transcribe locally** with faster-whisper (`large-v3` on an NVIDIA GPU, 10–20× realtime; CPU fallback).
2. **Pull the slides out of the video** — a change detector finds page turns and cuts, builds contact sheets,
   and Claude picks the frames a reader would miss.
3. **Write the note** — a subagent bound to a strict transcription spec: speaking order, nothing summarised,
   slide text copied into the prose, corrections logged, doubts marked instead of guessed.
4. **Gate it** — template headings, frontmatter, no timestamps in the prose, every image present, and
   **≥ 97 % of transcript segments findable in the note**. Fail → fix → check again.
5. **Settle doubtful words from the burned-in subtitles**, then hand the remaining doubts to you.

It was built to transcribe a 30-lesson fitness course (slide lectures plus ~80 exercise videos) into an
Obsidian vault, and generalised for any lecture-or-demo course: sports rehab, physiotherapy, yoga or
Pilates teacher training, coaching certifications, university lectures. Chinese and English templates ship;
the note language follows the video.

[中文说明 →](README.zh-CN.md)

---

## What a note looks like

```markdown
---
type: lecture
lesson: 30
title: Programme design III — periodisation
source_file: D30_programme-design-III.mp4
video_length: "26:37"
whisper_model: large-v3
verified: pass
images: 10
term_fixes: "ERM→1RM×26, 减轻载期→减载×23, 训组分配→训练分配×1 (subtitle)"
gaps:
  - "25:49 the recap says 85–90 % 1RM, the slide at 19:59 says 85–95 %; both kept"
---

# D30 Programme design III

> This note is a verbatim transcription of the course material. Nothing has been checked, evaluated, or added.

## One-line summary
Linear and undulating periodisation, deloads, and how to cycle volume, intensity and exercise selection.

## Walkthrough

### Why periodise at all %%00:28–02:15%%
Without periodisation the first three months go well, then the weight stops moving, the muscle stops
growing, and fatigue, poor sleep and low motivation appear … (every sentence, in order)

The slide "Why periodisation" lists: 1. keep progressing — avoid plateaus; 2. manage fatigue — recovery
after high-load blocks; 3. peak on time; 4. psychological freshness.

![[D30_0215_why-periodise.jpg]]
…
```

A 26-minute lecture becomes roughly 13 000 characters of prose, 18 stamped sections, 10 embedded slides,
with every correction listed in `term_fixes` and every contradiction in `gaps`. The reader gets the
lesson; the auditor gets the trail.

## Why it is built this way

- **Transcriber, not analyst.** Language models love to "understand and restate". A note written that way
  is half the length and silently drops qualifiers, examples and numbers. The spec forbids it and the
  coverage gate catches it.
- **Coverage, not word count.** Word-count targets push the writer to pad. The gate instead checks that
  each transcript segment's 4-character (CJK) or 3-word shingles occur in the note.
- **Proof before correction.** Whisper mis-hears domain terms into homophones. A change goes into the
  prose only when a slide, a burned-in subtitle or the operator's table proves it, and it is logged in the
  frontmatter. Unproven → the original word stays with a doubt marker. (A guess made from context was
  wrong once while the subtitle showed a third word; that lesson became step 6.5.)
- **Medium effort is enough.** Transcription is a fidelity task, not a reasoning task. Measured on one
  19-minute lesson: Sonnet at medium effort — 93 k tokens, 8 min, 100 % coverage; Opus medium — 66 k, 5 min,
  100 %; Sonnet at max effort — 296 k tokens, 41 min, 97.3 %. Higher effort made the writer *more* inclined
  to paraphrase. The default writer is Sonnet-medium; Opus-medium is the fallback.
- **No timestamps in the prose.** Readers never need them. Each section title carries its time range in a
  hidden comment (`%%mm:ss–mm:ss%%` in Obsidian, `<!-- -->` in plain Markdown) so the gate and the second
  pass can still locate things.
- **One lesson per session.** Cheapest, and it sidesteps long-session failure modes.

## Requirements

| | |
|---|---|
| Claude Code | desktop app or CLI, with subagents (any plan that can run the `Agent` tool) |
| Python | 3.9+ with `faster-whisper`, `opencv-python`, `numpy`, `Pillow` (`pip install -r requirements.txt`) |
| GPU | NVIDIA with ≥ 6 GB VRAM strongly recommended (`large-v3` float16). CPU works with `large-v3-turbo` at ~1× realtime. Apple Silicon = CPU path. |
| ffmpeg | optional; speeds up AV1/VP9 videos and frame grabs |
| Disk | Whisper model 3 GB (downloaded on first use) + a few MB of frames per lesson |

## Install

**As a plugin (recommended):**
```bash
claude plugin marketplace add miloxzh/transcribe-course
claude plugin install transcribe-course@transcribe-course
```
(or `/plugin marketplace add …` and `/plugin install …` inside a session).

**Manually:** clone the repo, copy `skills/transcribe-course/` into `~/.claude/skills/` and `agents/*.md`
into `~/.claude/agents/` (or the project's `.claude/`), then restart Claude Code — agents load at session start.

**Other hosts that read the Agent Skills format (WorkBuddy, CodeBuddy, Codex, Cursor, …):** copy the
`skills/transcribe-course/` folder into that tool's skills directory (WorkBuddy: `~/.workbuddy/skills/`, or
import it through its "upload local skill" dialog; CodeBuddy CLI: `codebuddy plugin marketplace add
miloxzh/transcribe-course` then `codebuddy plugin install transcribe-course@transcribe-course`), restart the
tool, and ask for a transcription in plain words instead of the slash command. The `agents/` definitions are
optional there: when the host cannot spawn a subagent, the skill writes the note in the main session and runs
the same gate. `${CLAUDE_SKILL_DIR}` is a Claude Code variable; on other hosts the skill locates its own
`scripts/tc.py` by path.

**Python packages** (into the interpreter the tool will call as `python`):
```bash
pip install -r requirements.txt
```
On NVIDIA machines the file also pulls `nvidia-cublas-cu12` and `nvidia-cudnn-cu12`, the only CUDA pieces
faster-whisper needs — no CUDA toolkit install.

## First run

Open Claude Code in an empty folder and say, in your language:

> Set up a transcribe-course workspace here for a Chinese sports-rehab course, then run the doctor.

Claude runs the two commands below for you; or run them yourself
(`TC` = `python <path-to-skill>/scripts/tc.py`):
```bash
TC init . --preset rehab-zh --course "肩关节康复"     # presets: fitness-zh, rehab-zh, rehab-en, generic-zh, generic-en
TC doctor --full                                     # packages, GPU, ffmpeg, font; --full runs a real inference
```
`init` creates:
```
videos/            drop course videos here
transcripts/       Whisper output (.json with timings, .txt, .log)
frames/{stem}/     candidate frames, contact sheets, framelist.md, subtitle strips
notes/             the notes; notes/attachments/ holds the embedded frames
vocab.txt          course terms fed to Whisper as its initial prompt — edit it
terms.tsv          known mis-hearings → correct spelling, applied at the gate
transcribe-course.json   language, note language, Obsidian vs Markdown, model, device
```

## Use

Put a video into `videos/`, open Claude Code in the workspace folder, and:

```
/transcribe-course videos/lesson03.mp4
```
Add `--careful` to use the Opus writer from the start.

What happens, and what you will be asked:
1. Transcription runs in the background (1–3 min on a GPU for a 20-minute lecture).
2. Claude renames the video to its proper name from the title slide (`D03_topic.mp4`); it asks if unsure.
3. Contact sheets are built; Claude looks at them, picks the frames, writes `frames/{stem}/framelist.md`.
4. The writing agent produces `notes/{stem}_draft.md` (5–12 min, ~60–150 k tokens).
5. The gate runs; Claude fixes what it names and re-checks.
6. Doubtful words are checked against the burned-in subtitles; the ones that cannot be settled are listed
   for you with their context. You answer; Claude patches the note and logs the fix.

The note stays in `notes/`. Moving it into your vault, linking, aliases — that is your step, by design:
notes get hand-edited after intake, and an automatic sync once overwrote 41 edited notes.

## The toolkit

Everything the skill runs is a plain CLI you can use on its own (`python scripts/tc.py <command> --help`):

| Command | Does |
|---|---|
| `doctor [--full]` | checks packages, GPU, ffmpeg, fonts, workspace; `--full` runs a real short inference |
| `init <folder> [--preset …]` | creates a workspace, config, vocab and terms files |
| `transcribe <video>` | faster-whisper → `transcripts/{stem}.json/.txt/.log`, with hallucination-loop and `�` checks |
| `frames <video> [--overview N]` | slide/cut detection → candidates, contact sheets, `_candidates.tsv` |
| `grab <video> <times>` | full-resolution frames at given seconds / mm:ss |
| `subs <video> <times…>` | burned-in subtitle strips around given times |
| `rename <old> <new>` | renames the video and every derived file; never overwrites |
| `attach <stem> <time> <label>` | copies a frame into attachments with the naming convention, prints the embed |
| `verify <note>` | template headings, frontmatter, timestamps, embeds, banned words, dumps |
| `check <transcript.json> <note>` | verify + coverage + random spot checks → `GATE PASS/FAIL` |
| `strip [--write] <note>` | removes timestamps from the prose |
| `terms [--write] <note>` | applies `terms.tsv`, merges into `term_fixes` |
| `log "<line>"` | appends to the workspace `log.md` |

## Customising

| Where | What |
|---|---|
| `transcribe-course.json` | `language` (Whisper code or `auto`), `note_language` (`zh`/`en` template set), `flavor` (`obsidian`: `![[x]]` + `%%…%%`; `markdown`: `![](attachments/x)` + `<!-- -->`), `whisper_model`, `cpu_model`, `device`, `ffmpeg`, `hwaccel`, `coverage_threshold`, `banned_words`, `declaration_alternatives`, `dirs` |
| `vocab.txt` | terms for Whisper's initial prompt; the last ~224 tokens matter most, keep it short |
| `terms.tsv` | `wrong<TAB>right`, applied blindly — only pairs that cannot mean anything else |
| `templates/` (in the workspace) | drop a Markdown file with a `type:` in its frontmatter and `## ` headings; `verify` treats it as the contract for notes of that type. Copy and edit a built-in template, or add a new type (`assessment`, `case-study`, …) |
| `references/SPEC.md` | the writer's rulebook; change it if your notes need different conventions |

## Repository layout

```
.claude-plugin/            plugin.json, marketplace.json
agents/                    transcriber.md (Sonnet), transcriber-careful.md (Opus)
skills/transcribe-course/
  SKILL.md                 the operator runbook Claude follows
  scripts/                 tc.py + one module per command
  templates/zh, templates/en   lecture.md, technique.md
  references/              SPEC.md, agent-brief.md, frame-picking.md, writer-prompt.md, troubleshooting.md, presets/
examples/                  a synthetic English lesson (transcript + note) to try the gate on
```

Try the gate before transcribing anything:
```bash
python skills/transcribe-course/scripts/tc.py init /tmp/tc-demo --preset generic-en
python skills/transcribe-course/scripts/tc.py check examples/en/L02_shoulder-assessment.json examples/en/L02_shoulder-assessment.md --workspace /tmp/tc-demo
```

## Measured costs (RTX 4080, Claude Code, Sept 2026)

| | 26-min slide lecture | 3-min exercise demo |
|---|---|---|
| transcription (large-v3, GPU) | 159 s | 14 s |
| frame detection (seek) | ~3 min | 6 s |
| writer (Sonnet, medium) | 11 min, 143 k tokens | 3–5 min, 50–60 k tokens |
| coverage | 99.6 % | 100 % |

A 17-minute AV1 demo video (bilibili download, 1080×1920): sequential frame extraction 2 min 49 s with
ffmpeg in software, 58 s with `--hwaccel cuda`, 13 s on a rerun from the cached per-second dump.

Troubles → [references/troubleshooting.md](skills/transcribe-course/references/troubleshooting.md).

## Credits

Pipeline, spec and lessons learned: Milo Xu, while transcribing a fitness camp's lecture series. Built with Claude Code.
Speech recognition: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) / OpenAI Whisper large-v3.

MIT License.
