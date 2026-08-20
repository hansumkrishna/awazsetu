# models/ — downloaded weights (NOT in git)

Everything here is fetched once by `python scripts/download_models.py` and then used
**offline**. Nothing in this folder is committed (it's git-ignored) — it's large and
machine-independent. Total ≈ 4–5 GB.

```
models/
  nllb-int8/          NLLB-200 distilled, CTranslate2 INT8  (~620 MB) — the default translator
  hf-cache/           Hugging Face cache (HF_HOME points here) — whisper, MMS-TTS, IndicTrans2
```

| What | Source | Size | Gated? |
|------|--------|------|--------|
| faster-whisper `small` + `medium` | `Systran/faster-whisper-*` | ~1.5 GB | no |
| NLLB-200 distilled INT8 (CT2) | `JustFrederik/nllb-200-distilled-600M-ct2-int8` | ~620 MB | no |
| NLLB tokenizer | `facebook/nllb-200-distilled-600M` | ~1 GB | no |
| MMS-TTS voices (hin/mar/eng) | `facebook/mms-tts-*` | ~0.5 GB | no |
| qwen2.5 `3b` + `1.5b` | Ollama (separate app) | ~3 GB | no |
| IndicTrans2 distilled *(optional)* | `ai4bharat/indictrans2-*` | ~2 GB | **yes** — `huggingface-cli login` |

The Ollama models live in Ollama's own store, not here. Install Ollama from
https://ollama.com, then the downloader runs `ollama pull` for you.

**IndicTrans2 is optional** — NLLB covers every Hindi/Marathi/English direction with no
login. Add `--indictrans2` to the downloader (after `huggingface-cli login` + accepting the
model terms) only if you want the higher-quality Indic engine.
