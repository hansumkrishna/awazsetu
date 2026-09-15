# AwazSetu

**Understand any video — in your language, out loud — even if you can't read or type.
Fully offline, with nothing to install.**

An offline desktop application that transcribes, translates, subtitles and dubs video and
audio across **Hindi · Marathi · English · Odia**, and lets you *ask the video questions*
by typing or by speaking, getting a grounded answer in your own language.

Everything runs on-device on a modest laptop (target: Intel i5 11th gen / Ryzen 5,
16 GB RAM, no GPU) with **zero network calls at runtime** — the process cannot reach a
network even if one is present.

Built for BAIF · Tech for Good.

---

## Run it

**Download:** https://drive.google.com/drive/folders/1XU_praP4yQI96gfpGzHaK01Uthx6WYmc?usp=sharing

Take `1-run-it-here/`, run the `JOIN-*.bat`, extract the zip, then **double-click
`AwazSetu.bat`**. To pair the models with *this* repository instead, take
`3-for-developers/` — see `models/README.md`.

That is the entire procedure. There is no Python to install, no `pip`, no FFmpeg, no
Ollama, no PATH to edit, no administrator rights and no internet — even on a freshly
imaged Windows machine. An embedded Python 3.10 and FFmpeg live in `runtime/`, and every
model ships in `models/`. Nothing is written outside the folder; deleting the folder
uninstalls it completely.

Before a demo, double-click **`AwazSetu-Check.bat`**. It verifies the runtime, FFmpeg,
every model, the assistant (by actually generating an answer), the library and the memory
budget, then prints READY or names exactly what is wrong.

## What it does

| | |
|---|---|
| **Transcribe** | faster-whisper INT8, with VAD, language detection and a confidence score |
| **Translate** | IndicTrans2 (AI4Bharat) — `hi↔mr` and `hi↔or` go direct, with no English pivot |
| **Subtitles** | four switchable tracks, flipped live in the player |
| **Voiceover** | a full spoken track per language (MMS-TTS), fitted to the original timings |
| **Ask the video** | BM25 retrieval + a local LLM that answers *only* from the transcript, and refuses when the fact is absent |
| **Voice chat** | tap the mic, ask out loud, hear the answer — the literacy unlock |
| **Model Garden** | every model scored per language and per task against *your* machine, with one-click presets |

**Everything a viewer consumes is computed once, at ingest, behind a progress bar** — the
transcript, all four subtitle tracks and all four full-length voiceovers are on disk before
the item appears in the library. Playback loads no model at all. Only the chat and voice
assistant run in real time.

## Languages

| | Transcribe | Translate | Subtitles | Voiceover | Chat |
|---|---|---|---|---|---|
| Hindi `hi` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Marathi `mr` | ✅ | ✅ | ✅ | ✅ | ✅ |
| English `en` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Odia `or` | — | ✅ | ✅ | ✅ | ✅ |

Odia is a **target** language: no open ASR model can transcribe Odia speech, so Odia is
produced by translating Hindi or Marathi audio. That is the common BAIF case — a Marathi
field video for an Odia audience.

## Packages

| Build | Contents |
|---|---|
| **LITE** | Embedded runtime, FFmpeg, Whisper medium + small, IndicTrans2 (three directions), four voices, both assistant models, and the complete processed library |
| **FULL** | LITE plus Whisper large-v3, tiny/base, the NLLB fallback engine, and a rescue kit of pinned wheels |

```bat
python scripts\package.py both --zip --split 1900
```

Archives over 1.9 GB are split into parts with SHA-256 checksums and a `JOIN-*.bat` that
rejoins them, so a bad transfer is caught before the demo rather than during it.

## Developing

```bat
python -m pip install -r requirements-pinned.txt
python app\run.py                 REM serve at http://127.0.0.1:5000
python app\run.py <media-file>    REM process one file
python scripts\doctor.py          REM preflight
python scripts\test_e2e.py        REM the acceptance suite
python scripts\reprocess_all.py   REM rebuild the library at full quality
python scripts\build_docpack.py --pdf
```

`requirements-pinned.txt` holds the exact versions the bundled runtime ships. They are
pinned, not resolved: a floating resolve drifts to numpy 2.x, which is an ABI break for
CTranslate2 and torch builds compiled against 1.x.

## Architecture

```
media ─▶ FFmpeg 16 kHz ─▶ faster-whisper ─▶ sanitiser + glossary ─▶ IndicTrans2
                                                                        │
                            work/<sha256>/ ◀── MMS-TTS ×4 ◀── WebVTT ×4 ┘
                                   │
                 Flask 127.0.0.1 ──┴── player · BM25 + llama.cpp assistant
```

Work folders are keyed by SHA-256 of the source, so re-adding the same file is idempotent
and URLs stay stable. Every heavy model runs in its own subprocess, so a native crash
degrades one feature rather than the application.

## Documentation

`docs/` holds the runbook, handover and training plan, test evidence, the delivery plan and
the comparison against Bhashini. The BAIF submission pack is generated from the live system
by `scripts/build_docpack.py` — every figure in it is read from the repository, not typed in.
