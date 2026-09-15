# models/ — the weights (not in git)

This folder is git-ignored: it holds about **15 GB of binaries** that do not belong in a
repository. The code here is useless without them, so they are published separately.

## Download

**https://drive.google.com/drive/folders/1XU_praP4yQI96gfpGzHaK01Uthx6WYmc?usp=sharing**

That folder contains three alternatives — take **one**:

| Folder | Size | What it gives you |
|---|---|---|
| `1-run-it-here/` | 10.66 GB | A complete, ready-to-run AwazSetu. Nothing else needed — not even this repository. |
| `2-everything/` | 14.69 GB | The same, plus Whisper large-v3, the NLLB fallback engine and a rescue kit. |
| `3-for-developers/` | 14.37 GB | **This is the one that pairs with a git clone.** Models + embedded runtime + the processed library, and nothing else. |

Each arrives as ~1.9 GB parts with a `JOIN-*.bat` that rejoins them and a `.parts.txt`
carrying a SHA-256 for every part, so a bad download is caught before it costs an evening.

### To turn this clone into a working install

1. Download everything in **`3-for-developers/`**.
2. Run `JOIN-awazsetu-assets.bat`, then extract the zip it produces **into this repository**,
   so `models\`, `runtime\` and `app\data\work\` sit beside `app\` and `scripts\`.
3. Double-click `AwazSetu-Check.bat` — it should print READY.
4. Double-click `AwazSetu.bat`.

Nothing is installed at any point. No Python, no pip, no FFmpeg, no Ollama, no internet.

## What lands here

```
models/
  hf-cache/hub/    Whisper (5 sizes) · IndicTrans2 (3 directions) · MMS-TTS (4 voices)
  llm/             Qwen 2.5 3B + 1.5B, GGUF Q4_K_M — the chat assistant
  nllb-int8/       NLLB-200 CTranslate2 INT8 — the fallback translation engine
```

| Model | Source | On disk | Licence |
|---|---|---|---|
| faster-whisper `tiny`…`large-v3` | `Systran/faster-whisper-*` | 5.3 GB | MIT |
| IndicTrans2 distilled, 3 directions | `ai4bharat/indictrans2-*` | 3.3 GB | MIT |
| MMS-TTS hin / mar / eng / ory | `facebook/mms-tts-*` | 0.58 GB | CC-BY-NC 4.0 |
| Qwen 2.5 3B + 1.5B (GGUF) | Qwen | 2.7 GB | Apache 2.0 |
| NLLB-200 distilled INT8 | `JustFrederik/nllb-200-…-ct2-int8` | 0.62 GB | CC-BY-NC 4.0 |

Duplicate `pytorch_model.bin` weights are omitted from the published bundles — every model
ships an identical `model.safetensors`, which is what transformers loads. That saves 3.7 GB
and changes nothing.

> **Two of these are CC-BY-NC.** MMS-TTS and NLLB are non-commercial licences. Whisper and
> IndicTrans2 are MIT and Qwen is Apache 2.0. Worth knowing before anyone builds a
> commercial product on this.

## Rebuilding the bundles from a machine that already has the models

```bat
python scripts\package_assets.py --split 1900     REM models + runtime + library
python scripts\package.py both --zip --split=1900 REM the two ready-to-run packages
python scripts\stage_gdrive.py                    REM arrange them for upload
```

`scripts\download_models.py` fetches the weights from source instead, but needs internet
and a Hugging Face login for the gated IndicTrans2 checkpoints. The Drive bundle avoids
both.
