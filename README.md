# AwazSetu

**Understand any video — in your language, out loud — even if you can't read or type. Fully offline.**

An offline desktop app that transcribes, translates and dubs audio / video / text across
**Hindi · Marathi · English**, with switchable subtitles, on-demand voiceover, and a
**chat & voice** assistant: ask the video a question (by typing *or speaking*) and hear a
grounded answer in your language. Everything runs **on-device** on a modest laptop
(target: Intel i5 / 16 GB RAM) with **zero network calls at runtime**.

Built for BAIF · Tech for Good.

---

## What it does
- **Transcribe** speech (faster-whisper, INT8).
- **Translate** across hi/mr/en (NLLB-200 INT8 by default; IndicTrans2 optional).
- **Switchable subtitles** — flip languages live in the player.
- **Dub on demand** — hear the video spoken in another language (MMS-TTS).
- **Chat with the video** — grounded retrieval + a local LLM (qwen2.5 via Ollama).
- **Voice chat** — tap the mic, ask out loud, hear the answer. The literacy unlock.
- **Searchable library** — SQLite/local cache; the same source is never processed twice.

## Requirements
| | |
|---|---|
| Python | 3.10+ |
| FFmpeg | on `PATH` ([gyan.dev](https://www.gyan.dev/ffmpeg/builds/) / `winget install Gyan.FFmpeg`) |
| Ollama | [ollama.com](https://ollama.com) — for the chat LLM |
| Disk | ~5 GB for models |
| RAM | 16 GB recommended (8 GB works with the smaller LLM) |

No GPU required — everything is CPU + INT8.

## Install
```bash
# 1. dependencies (CPU torch keeps it light)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 2. download all models ONCE (needs internet; ~4–5 GB into ./models/)
python scripts/download_models.py
#   add --indictrans2 only if you've run `huggingface-cli login` and want the gated engine

# 3. run — fully offline from here on
python app/run.py           # -> http://127.0.0.1:5000
```
Open the URL, drop in a video, switch subtitle/voiceover languages, and chat or speak to it.

Process a video from the command line instead of the UI:
```bash
python app/run.py "path/to/video.mp4"
```

## Offline guarantee
After `download_models.py`, the app sets `HF_HUB_OFFLINE=1` and loads every model from the
project's own `models/` folder — **no network access at runtime**. To force a re-download
(e.g. to add a model), run with `AWAZ_OFFLINE=0`.

## Settings (operator page)
The end-user flow is zero-config. Operators get `/settings` to switch models (ASR, mic STT,
translation engine, chat LLM), pick target languages, tune performance (threads, device,
beam, memory-saver) and chat/voice behaviour, and see a live status panel (RAM, installed
models, offline state). It's **select-only** — it never downloads; it switches among what
`download_models.py` installed. Changing a model applies to new processing; use a video's
**Re-process** button to re-run it.

## Project layout
```
app/                  application code (Flask server, pipeline, workers, templates)
models/               downloaded weights — NOT in git (see models/README.md)
scripts/              download_models.py (one-time model fetch)
generate_deck.py      rebuilds the pitch deck (optional; needs python-pptx)
requirements.txt
```

## Configuration (env vars)
`AWAZ_MODELS_DIR` · `AWAZ_OFFLINE` (0 to allow downloads) · `AWAZ_MT` (nllb|indictrans2) ·
`AWAZ_WHISPER` / `AWAZ_MIC_WHISPER` · `AWAZ_LLM` / `AWAZ_LLM_FALLBACK` · `AWAZ_CPU_THREADS` ·
`AWAZ_DEVICE` (cpu|cuda) — most are also exposed on the Settings page.

## Notes
- **Marathi** answers are the weakest leg (small-LLM limitation); Hindi/English are solid.
  A larger/Indic LLM (e.g. Sarvam-1) is the roadmap fix.
- **IndicTrans2** gives higher Indic translation quality but is a gated model — NLLB is the
  self-sufficient, login-free default.

## License
Open-source components retain their own licenses. Provided as-is for the BAIF hackathon.
