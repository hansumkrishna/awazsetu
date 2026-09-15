# AwazSetu — Deployment Runbook & Operations Guide

Audience: whoever installs, runs or supports AwazSetu at BAIF — including someone
who has never met the build team.

---

## 0. Demo-day setup (BAIF laptop, 10:00–12:00 window)

**Prerequisites on the target machine.** Verify these FIRST — each has a fallback.

| # | Requirement | Check | If missing |
|---|---|---|---|
| 1 | Python 3.10+ | `python --version` | Install from python.org, or run from the portable copy on the USB drive |
| 2 | FFmpeg on PATH | `ffmpeg -version` | `winget install Gyan.FFmpeg`, or copy `ffmpeg.exe` next to `app/` |
| 3 | Assistant backend | `AwazSetu-Check.bat` line `Chat LLM backend` | In-process llama.cpp. Nothing to install or start |
| 4 | Chat weights present | `models\llm\*.gguf` | Shipped in both packages. No pull, no network |
| 5 | `models/` folder present (~6.3 GB) | `dir models` | Copy from USB — **never** re-download at the venue |
| 6 | Python deps | `pip install -r requirements.txt` | Use the bundled wheels folder (offline install) |
| 7 | Pre-processed cache | `app/data/work/` has folders | Copy from USB. **This is the fallback plan** — the demo needs zero processing. |

> **Carry on a USB drive:** the whole repo *including* `models/` and `app/data/work/`,
> plus the Ollama installer and its model blobs (`%USERPROFILE%\.ollama\models`),
> plus a `wheels/` folder (`pip download -r requirements.txt -d wheels`).
> Internet is available at BAIF, but never depend on it during a 30-minute slot.

**Start it**
```bat
cd awazsetu
python app\run.py
```
Then open <http://127.0.0.1:5000>. Startup is a few seconds; models load lazily per stage.

**Smoke test (2 minutes, do this before the panel arrives)**
```bat
python scripts\test_e2e.py assets settings
```
Expect all PASS. Then open one video, switch subtitles mr/hi/en/or, play a voiceover, ask one
chat question. If all four work, the demo is safe.

---

## 1. First-time installation (from a clean machine)

```bash
# 1. dependencies — CPU torch keeps the footprint small
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 2. one-time model download (~6 GB into ./models/). Needs network ONCE.
python scripts/download_models.py

# 3. chat model
REM Nothing to pull. Both assistant models ship as GGUF in models\llm\.

# 4. run — offline from here on
python app/run.py
```

Elapsed on a typical connection: ~20–30 min, almost all of it model download.
Steps 1–3 are one-time; step 4 is the daily start command.

---

## 2. Configuration

All settings live in `app/settings.json`, edited through **/settings** in the browser.
The page is **select-only and offline** — it never downloads, it only switches between
what is already installed.

Every setting maps to an environment variable, so it can also be forced from the shell:

| Setting | Env var | Default | Notes |
|---|---|---|---|
| Video ASR model | `AWAZ_WHISPER` | `medium` | Benchmarked best quality/speed for Marathi |
| Mic STT model | `AWAZ_MIC_WHISPER` | `small` | Short clips; keeps latency down |
| Translation engine | `AWAZ_MT` / `AWAZ_CHAT_MT` | `nllb` | `indictrans2` is better but gated |
| Chat LLM | `AWAZ_LLM` | `qwen2.5:3b` | Falls back automatically |
| Chat fallback | `AWAZ_LLM_FALLBACK` | `qwen2.5:1.5b` | Used when RAM is tight |
| CPU threads | `AWAZ_CPU_THREADS` | `0` (auto) | Auto = half the logical cores |
| Device | `AWAZ_DEVICE` | `cpu` | `cuda` only with ≥4 GB free VRAM |
| Beam size | `AWAZ_BEAM` | `5` | 1 is faster, noticeably worse for Indic |
| Memory-saver | `AWAZ_VOICE_UNLOAD` | `true` | Unloads the LLM before mic STT |
| Offline lock | `AWAZ_OFFLINE` | `1` | Set `0` only to allow a re-download |

After changing a model, press **Re-process** on a video to re-run it with the new
settings. Existing videos keep their cached output until you do.

---

## 3. Operational readiness

**Logs.** The server prints to stdout. Redirect it to keep a record:
```bat
python app\run.py > logs\awazsetu.log 2>&1
```
Processing progress per video is written to `app/data/work/<id>/status.json`.
Chat/LLM failures are logged to stderr with *both* the primary and fallback reason.

**Rollback.** The app is stateless apart from two folders:
- `app/data/work/` — processed output. Delete one `<id>` folder to force a clean re-run.
- `app/settings.json` — delete it to return to defaults.

Code rollback is `git checkout <previous-commit>`; models and data are untouched
because both are git-ignored.

**Health check.** `/settings` shows a live status panel: free RAM, assistant backend and
which models it has, installed Whisper sizes, translation engines, MMS voices.

---

## 4. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "The local AI model could not be loaded — not enough free memory" | The 3B model could not be allocated | Close other apps, or apply the **Fast & low RAM** preset in the Model Garden |
| Chat answers come back in English when Hindi/Marathi was selected | The translation worker could not load (low RAM) | Free RAM, or lower the ASR/LLM size |
| "This video does not cover that" for a question you believe is answered | Groundedness guard fired — the fact is not in the transcript, or ASR garbled it | Check the transcript; re-process with a larger ASR model |
| Subtitles look like nonsense | ASR ran with the wrong model or wrong language | Confirm `asr_model=medium`; press Re-process. Language is auto-detected — check the log line "language auto-detected" |
| Processing is very slow | CPU-only, beam 5, and every voiceover is built up front | Expected. Processing is a one-time cost per video; playback is then instant. Pre-process before a demo |
| A voiceover button says "not generated" | That language was not selected when the video was processed | Add it in Settings → Target languages, then press **Re-process** |
| Assistant reports no backend | `models\llm\*.gguf` missing from the package | Re-extract the package; the GGUF files are ~2.8 GB and may have been skipped |
| Player shows no video | `video.mp4` missing in the work folder | Re-upload, or copy the source file in |

---

## 5. What runs where (architecture in one page)

```
video ──ffmpeg──> audio.wav
       └─ faster-whisper (INT8)  → transcript + per-segment confidence
             │  language AUTO-DETECTED, domain prompt, beam 5
             ├─ sanitiser: drop degenerate/wrong-script segments
             ├─ glossary: fix known Marathi/Hindi ASR mishears
             └─ IndicTrans2 distilled (subprocess) → hi / mr / en / or
                    ├─ WebVTT subtitle tracks  (player switches live)
                    ├─ MMS-TTS (subprocess)    → dub.<lang>.wav  [ALL languages, now]
                    └─ manifest.json ──> BM25 index ──> llama.cpp LLM ──> chat / voice
```

**Everything a viewer consumes is precomputed at save time** — transcript, all
translations, all subtitle tracks and **every voiceover** — behind a multi-step progress
bar. At playback nothing is synthesised. The only real-time work is the **chat and voice
assistant**, which must be live because the question is not known in advance.
Re-process rebuilds the whole set with the current settings.

Heavy models run in **short-lived subprocesses** so torch, CTranslate2 and CUDA never
share the server process, and memory is released between stages. Nothing is ever
co-resident: this is what keeps peak RAM inside a 16 GB machine.

**No network calls at runtime.** `HF_HUB_OFFLINE=1` is set by `run.py`, and every model
is loaded from the project's own `models/` folder.
