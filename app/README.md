# app/ — architecture & modules

Flask app + a small set of single-purpose modules. Heavy models run in **short-lived
subprocesses** (workers) so their native runtimes (torch, ctranslate2, CUDA) never have to
co-exist in the server process, and memory is released between stages.

## Modules
| File | Role |
|------|------|
| `run.py` | Launcher — resolves the `models/` folder, sets `HF_HOME` + offline mode, applies settings, then serves or processes a video. |
| `server.py` | Flask routes — player, upload, chat, voice, dub, export, search, settings, re-process. |
| `pipeline.py` | Orchestrates one video: extract → transcribe → translate → write subtitles + manifest. |
| `asr.py` | Audio extraction (FFmpeg) + transcription (faster-whisper, INT8). |
| `mt.py` | Translation engines behind one interface: NLLB (worker) and IndicTrans2 (worker). |
| `translate_worker.py` / `indictrans_worker.py` | Subprocess translators (NLLB CT2 int8 / IndicTrans2). |
| `chat.py` | Grounded RAG: BM25 retrieval + local LLM (Ollama). Reasons in English, translates the answer. |
| `voice_worker.py` | Subprocess STT (mic → text) + TTS (answer → speech). |
| `dub_worker.py` | Subprocess MMS-TTS voiceover, timestamp-aligned to the video. |
| `subs.py` | WebVTT / SRT writers. |
| `glossary.py` (+ `glossary.json`) | Domain post-correction (agri terms) applied before translation. |
| `config.py` | Operator settings store (`settings.json`) bridged to env vars + system status. |
| `templates/` | `index` (library + upload), `player` (video + subs + dub + chat/voice), `settings`. |

## Key design decisions
- **Staged loading.** ASR, MT, TTS and the chat LLM are never all resident at once — the
  pipeline frees the ASR model before MT; MT/TTS run as subprocesses; the LLM lives in
  Ollama. Peak RAM stays flat, which is what lets it run on an i5 / 16 GB.
- **INT8 everywhere.** faster-whisper INT8 and NLLB-200 CTranslate2 INT8 keep the footprint small.
- **NLLB is the ungated default.** It covers every hi/mr/en direction with no login. IndicTrans2
  is an optional, higher-quality Indic engine (gated — needs `huggingface-cli login`).
- **Chat answers are grounded** strictly in the transcript (no open-web), with a
  jump-to-timestamp. The LLM reasons in English (its strongest language) and the answer is
  translated to the requested language.
- **Voice = reuse.** The mic uses the same Whisper that transcribes videos; spoken answers use
  the same MMS-TTS that dubs. No new model family for voice.
- **Model paths are native.** CTranslate2's native library needs real files and OS-native
  absolute paths (not MSYS `/c/...`), so NLLB lives as plain files under `models/nllb-int8`.

## Troubleshooting
- **Chat/voice answers come back English-only for a hi/mr request** → the translation worker
  couldn't load (usually low free RAM). Close other apps, or reduce the ASR/LLM size in Settings.
- **"model not found"** → run `python scripts/download_models.py` (see the top-level README).
- **LLM won't load** → ensure Ollama is running (`ollama list`); the app auto-falls back from
  `qwen2.5:3b` to `qwen2.5:1.5b` when RAM is tight (configurable in Settings).
- **Marathi answers are weakest** — a small-LLM limitation; a larger/Indic LLM is the roadmap fix.
