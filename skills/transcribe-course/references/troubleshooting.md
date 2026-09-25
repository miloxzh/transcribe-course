# Troubleshooting

Symptoms first, then the fix. Every entry here was hit at least once while transcribing a real course.

## Transcription

**`cublas64_12.dll is not found` / `cudnn` errors on Windows, sometimes only after "model loaded"**
CTranslate2 loads the CUDA libraries lazily, so constructing the model succeeds and the first encode fails.
`pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`, then `tc.py doctor --full`. The scripts preload those
DLLs from `site-packages/nvidia/*/bin`; if you installed them into a different interpreter, run the
scripts with that interpreter.

**The transcript repeats one sentence for minutes (`RESULT SUSPECT-LOOP`)**
Whisper fell into a repetition loop. The decoding call keeps the temperature fallback chain
(`[0.0, 0.2, … 1.0]`) and `condition_on_previous_text=False` precisely to escape this; if someone
"simplified" those parameters to `temperature=0`, the loop runs to the end of the file. Rerun; if it
persists on one file, try `--no-vocab` (a very long initial prompt can trigger it) or a shorter `vocab.txt`.

**Dozens of `�` characters (`RESULT BAD-DECODE`)**
Rerun. Check `language` in the config matches the speech (a wrong code produces garbage). A handful of
`�` in a 20-minute file is normal and the writer fills them from context.

**`RESULT EMPTY`**
Wrong language code, or the file has no audio stream (some downloads are video-only; the audio is a second file — merge them first).

**Model download is slow or fails**
The model comes from Hugging Face on first use (large-v3 ≈ 3 GB). Behind a slow route, set a mirror
before running: `HF_ENDPOINT=https://hf-mirror.com` (works in China). To keep the cache elsewhere: `HF_HOME=D:\hf-cache`.

**No GPU: it takes as long as the video**
Expected. The CPU path uses `large-v3-turbo` in int8 at roughly 1× realtime. Options: a machine with an
NVIDIA card (any 6 GB+ card runs large-v3 float16), a Mac with Apple Silicon (see next entry), or accept the
wait and start the transcription before doing something else.

**Apple Silicon Mac: slow, or "mlx" not used**
faster-whisper cannot use the Mac GPU. `pip install mlx-whisper` adds the MLX backend; `doctor` shows
"backend mlx" and `transcribe` picks it automatically (`backend: "auto"` in the config; force with
`--backend mlx` or `--backend faster-whisper`). The MLX model is downloaded from Hugging Face on first use
(`mlx_model` in the config, default `mlx-community/whisper-large-v3-mlx`; the turbo variant is
`mlx-community/whisper-large-v3-turbo`). mlx-whisper has no VAD filter, so a long silent stretch can
produce a stray sentence; the loop check still runs and the writer treats it like any other transcript.
Intel Macs stay on the CPU path.

**macOS: `doctor` prints "Class AVFFrameReceiver is implemented in both … av … and … cv2 …"**
PyAV and OpenCV each bundle their own ffmpeg libraries and macOS warns when both load into one process.
Only `doctor` imports both; `transcribe` uses PyAV alone and `frames`/`subs` use OpenCV alone, so the
warning has no effect on the pipeline. If a command ever crashes with it, replace the OpenCV wheel:
`pip uninstall opencv-python && pip install opencv-python-headless`.

**Vocabulary does not seem to help**
Whisper uses only the last ~224 tokens of the initial prompt. Put the most important terms at the end of
`vocab.txt` and delete groups your course never uses. The prompt biases spelling of what is heard; it
does not teach new words the model has never seen.

## Frames

**`frames` runs for ten minutes and produces nothing**
The video is AV1 or VP9 (common for bilibili and YouTube downloads); per-second seeking re-decodes from a
keyframe each time. The `auto` method detects `av01`/`vp09` and switches to sequential decoding; if the
codec string is empty or unusual, force it: `--method sequential`. Measured on a 17-minute 1080×1920 AV1
video: ffmpeg software decode 2 min 49 s, ffmpeg with `--hwaccel cuda` 58 s, and 13 s on a rerun because
the per-second dump is kept in the system temp folder (about 10 MB per minute of video; `--fresh` redoes
it). The OpenCV-only fallback works but is several times slower — install ffmpeg for AV1 courses.

**A 20-minute slide lecture yields one or two candidates**
Dark slide themes with small changing text fall under the default change threshold. Look at the contact
sheets first, then rerun with `--frac 0.005`. Do not conclude "no slides" from the candidate count.

**A demo video yields dozens of `live` candidates**
Normal — a person moving triggers the cut detector every few seconds. Above `--max-live` (default 120)
the minimum gap between live candidates is doubled until the count fits, so time coverage is kept and
density drops; the log says when that happened. For demo videos use `--overview 3` and pick from the
overview sheets (one thumbnail every 3 seconds); keep 2–6 frames that show settings, angles or
wrong-vs-right comparisons.

**Labels on the sheets show boxes instead of characters**
No CJK-capable font was found. The scripts try Microsoft YaHei, PingFang, Noto Sans CJK and WenQuanYi;
install one of them (Linux: `fonts-noto-cjk`). Timestamps still render.

**Frames or sheets are written but look black or empty**
OpenCV could not decode that stream. Install ffmpeg; the scripts then decode through it.

## Subtitles

**`subs` strips show the wrong part of the frame**
Subtitle position differs per editor. The default band is 72–98 % of the frame height; narrow it once
you know where they sit: `--band 0.85,0.97`. Vertical (portrait) videos often have subtitles higher up.

**The doubtful word is between two strips**
Reduce `--step 0.4` or widen `--span 8`.

## The gate

**`coverage` stuck below 97 %**
Read the listed misses. Each is a transcript segment whose 4-character (or 3-word) shingles do not
appear in the note — usually a sentence the writer paraphrased or dropped. Put the sentence back into its
section in corrected form. Pasting raw transcript blocks is not a fix (the gate rejects the markers, and
readers get noise). Two failed rounds → rerun the writer with `--careful`.

**`H2 headings differ from template`**
The writer renamed or dropped a heading. Restore the template's headings verbatim and move the content
under them; empty sections say "None." / "无。".

**`banned word`**
The note says "the instructor says" / 「讲师」. Rewrite as plain statements; the declaration on line one
already says everything is transcribed.

**`type … has no template`**
The note's `type:` value matches no template. Either use the template's value (`正课`/`动作`,
`lecture`/`technique`) or add a template with that `type:` to the workspace `templates/` folder.

**`embedded image not found`**
The embed's file name does not exist in `notes/attachments/`. Re-run `tc.py attach` or fix the name.

## Claude Code

**The `transcriber` agent is not offered**
Plugin installs namespace agents: look for `transcribe-course:transcriber`. Manual installs need
`agents/*.md` copied into `~/.claude/agents/` (or the project's `.claude/agents/`), and agents load at
session start — restart the session after copying. Without either, the skill falls back to
`general-purpose` with the writer prompt from `references/writer-prompt.md`.

**Mid-session, every tool call is refused**
Seen once in a very long session (thousands of turns): an unrelated safety check tripped and stayed
tripped. It has nothing to do with the skill or permissions. Start a new session — one lesson per session
is the intended way to run this anyway.

**`${CLAUDE_SKILL_DIR}` appears literally in commands**
Older versions did not expand it. Find the scripts with Glob (`**/skills/transcribe-course/scripts/tc.py`)
and use the absolute path.

## Files and sync

**The workspace lives in OneDrive / iCloud / Dropbox**
Fine. Candidate frames are a few MB per lesson; the per-second extraction used for AV1 videos is written to
the system temp folder, not the workspace. Delete `frames/{stem}/` after a note is accepted if space matters.

**Non-ASCII file names on Windows**
Handled: images are written through `imencode`/`tofile` and read through `imdecode`; OpenCV's own
`imwrite`/`imread` silently fail on such paths.
