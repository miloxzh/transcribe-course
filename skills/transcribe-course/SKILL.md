---
name: transcribe-course
description: Turn a course video (a slide lecture, a recorded class, or an exercise / rehab technique demo) into a verbatim-level Markdown note with the important frames embedded — local Whisper transcription (GPU when available), slide and cut detection with contact sheets, frame picking, a writing subagent bound to a strict transcription spec, and a mechanical gate (template headings + transcript coverage ≥ 97 %). Use it whenever someone wants a video lesson, webinar, tutorial or training course turned into notes they can read instead of watching, asks for "lecture notes from this video", wants to transcribe a course into Obsidian, or runs /transcribe-course <video>. Not a summariser — it produces the full record.
argument-hint: "<video file> [--careful] [--type lecture|technique]"
allowed-tools: "Read Write Edit Bash Glob Grep Agent"
effort: medium
---

# Course video → verbatim-level note

You are the operator of a pipeline. Every step has a command; judgement is needed in exactly three
places: naming the video (step 2), picking frames (step 3) and the correction table (step 4).
Talk to the user in their language. Do not summarise the video yourself and do not edit the note's
content — the writing agent writes, the gate checks, you steer.

## Setup (once per session)

**Scripts.** They live in `${CLAUDE_SKILL_DIR}/scripts/`. Below, `TC` means
`python "${CLAUDE_SKILL_DIR}/scripts/tc.py"` — use the interpreter that has faster-whisper installed
(`python`, `python3`, or a venv). If the variable did not expand, find the script with Glob
`**/skills/transcribe-course/scripts/tc.py`.

**Workspace.** A workspace is any folder holding `transcribe-course.json` (videos/, transcripts/, frames/,
notes/). Commands find it from the current directory or `--workspace <folder>`; pass `--workspace`
explicitly if the video lives elsewhere. No workspace yet → ask the user where they want it, then:

```bash
TC init "<folder>" --preset rehab-zh --course "<course name>"    # presets: TC init --list-presets
TC doctor --full --workspace "<folder>"                          # packages, GPU, ffmpeg; --full runs a real inference
```
Tell the user the first transcription downloads the Whisper model (large-v3 ≈ 3 GB; large-v3-turbo ≈ 1.6 GB
on CPU-only machines). If `doctor` shows no GPU, warn that transcription takes about as long as the video.

**One lesson per session.** Transcribing is self-contained; a fresh session per video is cheapest and
avoids the failure mode where a very long session starts refusing tool calls for unrelated reasons.

**Budget to expect.** A 20-minute lecture: 1–3 min transcription on a GPU, a few minutes of frame work,
8–12 min and roughly 100k tokens for the writing agent, then the gate. Say so up front.

Argument: `$ARGUMENTS` is the video (path or a name inside `videos/`). `{stem}` is its file name without
extension — the current name in step 1, the proper name from step 2 onwards.

## 1. Transcribe (background)

```bash
TC transcribe "<video>" --workspace "<ws>"
```
Run it with `run_in_background: true` and wait for the completion notice. Output:
`transcripts/{stem}.json` (timed segments), `.txt` (`mm:ss  text`), `.log`. Then read the last four lines of the log:

- `RESULT ok` — go on. Single-digit `U+FFFD` counts are normal (the writer fills them from context).
- `RESULT SUSPECT-LOOP` — the same sentence repeated for a stretch. Rerun; if it persists, `--no-vocab`.
  Do not hand a looping transcript to the writer.
- `RESULT BAD-DECODE` (dozens of `�`) — rerun; check the language code in the config.
- `RESULT EMPTY` — wrong language, or no speech track.

Audio-only files (m4a, mp3, wav) work the same; the note's `modality` becomes `audio_only` and steps 3 and 6.5 are skipped.

## 2. Name the video (right after transcription, every time)

Downloads are called `v.f421220.mp4` or `main (3).mp4`; the note, attachments and log all key off the
stem, so fix the name now.

```bash
head -8 "<ws>/transcripts/{stem}.txt"      # opening line usually names the lesson number and topic
ls "<ws>/videos/"                           # match the naming already in use
TC rename "<current>.mp4" "<proper>.mp4" --workspace "<ws>"
```
- Lecture: `{code}_{title}` — code from the opening ("lesson 12", "Day 3" → `L12`, `D03`), title from the
  title slide or the opening sentence, no spaces (`D29_周期化训练`, `L03_shoulder-assessment`).
- Technique / single-exercise demo: the movement's name, spelled the way existing notes spell it.
- Unsure about the number or the name: **ask the user, do not guess.** Already proper: skip, but check
  the code against the title slide.
`rename` moves the transcript files and any frames folder with it and refuses to overwrite.

## 3. Frames → contact sheets → pick → attach → frame list

```bash
TC frames "<video>" --workspace "<ws>"                 # lectures: slide + cut detection
TC frames "<video>" --workspace "<ws>" --overview 3    # demo videos: add an every-3-seconds overview
```
Output in `frames/{stem}/`: candidates `{stem}_{mmss}.jpg`, `_sheet_N.jpg` (12 per sheet, labelled
`mm:ss detector file`), `_candidates.tsv`, optional `_overview_N.jpg`. AV1/VP9 videos switch to sequential
decoding automatically (the log line `method sequential` says so): one to three minutes with ffmpeg,
seconds on a rerun. When a person on camera trips the cut detector constantly, the log says the live
candidates were thinned; that is expected for demo videos.

**Look at every sheet with Read.** Small text unreadable on a sheet → open the candidate file. The criteria
and the frame-list format are in `${CLAUDE_SKILL_DIR}/references/frame-picking.md`; the short version:
**keep a frame if a reader would lose information without it** (tables, charts, numbered lists, plan and
protocol tables, annotated angles, equipment settings, wrong-vs-right comparisons); drop speaker-only frames,
title-only slides (copy the title into the prose), duplicates and mid-animation frames.

- Only one or two candidates on a long lecture ≠ "no slides". Look at the sheets, rerun with `--frac 0.005`.
- A moment you need is not among the candidates: `TC grab "<video>" mm:ss --workspace "<ws>"` (add 0.5 s
  for overlays that appear late).
- A demo video gives dozens of `live` candidates; pick from the overview sheets instead of the candidates.

Copy the chosen frames into the attachments folder with the naming convention (prefix = lecture code or
technique name, label = a few words, no spaces):
```bash
TC attach {stem} 01:43 core-principles --prefix D29 --workspace "<ws>"
```
Then write `frames/{stem}/framelist.md` with two tables — frames that go into the note (time, attachment
file, what is on it) and evidence-only frames (time, file, burned-in subtitle text, what is shown). The
writing agent opens every listed image itself; your table is the index. Copy the subtitles carefully:
they are the proofread spelling the writer uses to fix homophones.

## 4. Glance at the transcript, build the correction table

```bash
head -30 "<ws>/transcripts/{stem}.txt"
grep -n "RPE\|组\|次\|sets\|reps" "<ws>/transcripts/{stem}.txt" | head -20
```
List the homophone errors you can **prove** from the title slide, a frame you read or a burned-in subtitle
(`哈克深踨→哈克深蹲`, `杠材→杠杆`, `sarcomer→sarcomere`). Two or three lines are normal; zero is fine.
Anything you merely suspect stays off the table — the writer will mark it as doubtful and step 6.5 settles it.
Known stable mis-hearings for this course belong in the workspace `terms.tsv` (the gate applies it).

## 5. Delegate the writing

Pick the writer from the agent types available in this session:
- `transcribe-course:transcriber` (plugin install) or `transcriber` (manual install) — Sonnet, medium effort; the default.
- `transcribe-course:transcriber-careful` / `transcriber-careful` — Opus; use when the user passed `--careful`,
  or when a draft fails the gate twice or stays under the coverage threshold.
- Neither installed: `general-purpose` with `model: sonnet` (or `opus`), and put the text of
  `${CLAUDE_SKILL_DIR}/references/writer-prompt.md` at the top of the prompt. This fallback inherits the
  session's effort level; at high or max effort the same draft takes 3–5× longer and costs 3× the tokens
  (measured: 41 min vs 8 min on one lesson) because the model keeps re-reading and re-judging. Install the
  agents, or set the session to medium effort, before transcribing more than one video this way.

Decide the note type unless the user passed `--type`: slides plus speech, possibly ending in a summary and a
plan → `lecture`; one movement, drill or protocol demonstrated on camera (2–8 minutes) → `technique`.
Fill the brief in `${CLAUDE_SKILL_DIR}/references/agent-brief.md` — every `{…}`, absolute paths, the
correction table, the page structure you saw on the sheets, whether a plan/protocol is shown. Template:
`${CLAUDE_SKILL_DIR}/templates/<note_language>/lecture.md` or `technique.md`, unless the workspace has
its own `templates/` override for that type. Output file: `notes/{stem}_draft.md`.
Launch with `run_in_background: true`; the agent needs 5–12 minutes. Do not read or edit other notes meanwhile.

## 6. Gate

```bash
TC strip --write "<ws>/notes/{stem}_draft.md" --workspace "<ws>"      # timestamps out of the prose
TC terms --write "<ws>/notes/{stem}_draft.md" --workspace "<ws>"      # workspace terms.tsv
TC check "<ws>/transcripts/{stem}.json" "<ws>/notes/{stem}_draft.md" --workspace "<ws>"
```
`check` prints `GATE PASS` or `GATE FAIL` with reasons. Fix what it names, then run it again:

| Finding | What to do |
|---|---|
| banned word (「讲师」, "the instructor") | rewrite those sentences as objective statements |
| placeholder section title | read the section, give it a 4–14 character content title |
| H2 headings differ from template | restore the template's headings verbatim; move content, never delete it |
| timestamps left / time column | `strip --write` handles most; fix the rest by hand |
| embedded image not found | attach it (step 3) or fix the file name |
| coverage below threshold | read the listed misses; put each missing sentence into its section. Never paste raw transcript blocks. Twice under threshold → rerun step 5 with the careful writer |
| raw transcript dump marker | delete the dump, keep only corrected prose |

Then read the frontmatter `term_fixes` line yourself: a change that reads well but does not fit the
surrounding sentences is a new error — revert it to the original word plus a doubt marker.

## 6.5 Settle doubtful words with the burned-in subtitles

```bash
grep -n "转写存疑\|unclear, possibly" "<ws>/notes/{stem}_draft.md"     # find doubts; locate their mm:ss in the .txt
TC subs "<video>" 00:08 13:42 20:33 --workspace "<ws>"                   # one strip image per time
```
Read `frames/{stem}/subs/subs_{mmss}.jpg`. The subtitle was proofread by the editor and beats both Whisper
and your guess (a guess has been wrong while the subtitle showed a third word). Strip shows nothing →
`--band 0.60,0.99` or a different `--span`.
- Proven → write the subtitle's spelling, drop the marker, add `wrong→right×1 (subtitle)` to `term_fixes`,
  and fix the same word wherever else the note repeats it (numbers table, quotes, your frame list).
- Not settled (no subtitle there, subtitle hidden) → keep the marker for step 7.
Rerun `check` once after edits.

## 7. Wrap up

```bash
TC log "{stem}: transcribed <s>, candidates <n>, embedded <n>, coverage <x %>, writer <name>, <n> doubts settled by subtitles" --workspace "<ws>"
```
Report to the user, in this order:
1. Where the note is (`notes/{stem}_draft.md`) and the attachments; whether the gate passed.
2. **Every doubt still inline**: its mm:ss, the transcript lines around it (corrected words as corrected,
   the doubtful word in bold), and your best guess. The user replies with the real word; then edit the
   note, drop the marker, add the change to `term_fixes`. None left → say so.
3. Anything in `gaps` (contradictions, skipped stretches).

The note stays in `notes/`. Moving it into a vault, renaming it to its final name, adding aliases or links
is the user's own step — do not do it unless asked.

## What this skill never does

Summarise or reorganise the lesson by topic; "fix" what the course taught; fill a plan from outside the video;
delete or overwrite a video; touch notes other than the current draft; declare `verified: pass` on the writer's behalf.
