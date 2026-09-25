# Changelog

## 0.1.0 — 2026-09-26

First public version, extracted from a private pipeline that transcribed a 30-lesson fitness course
(slide lectures plus ~80 exercise videos) into Obsidian.

- Skill `/transcribe-course` with the seven-step runbook (transcribe → name → frames → correction table → writer agent → gate → subtitles → wrap-up)
- Agents `transcriber` (Sonnet, medium) and `transcriber-careful` (Opus, medium)
- `tc.py` toolkit: doctor, init, transcribe, frames, grab, subs, rename, attach, verify, check, strip, terms, log
- Chinese and English templates for `lecture` and `technique` notes; workspace template overrides
- Vocabulary presets: fitness-zh, rehab-zh, rehab-en, generic-zh, generic-en
- Transcription spec v3 (language-neutral), writer brief, frame-picking guide, troubleshooting
- Bundled English example to exercise the gate without a GPU
