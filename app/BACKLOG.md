# Roadmap

## Shipped
- Offline pipeline: FFmpeg → faster-whisper (INT8) → NLLB-200 (INT8) → WebVTT.
- Switchable subtitles (hi/mr/en) in an HTML5 player.
- Dub on demand (MMS-TTS), timestamp-aligned, cached.
- Chat with the video — grounded BM25 + local LLM (Ollama), answers in the chosen language.
- Voice chat — tap-to-talk STT + spoken answers, fully offline.
- Upload + progress, cross-video library search, SRT / transcript / MKV export.
- Operator Settings page (select-only, offline) + per-video re-process.
- Staged model loading + INT8 to fit an i5 / 16 GB.
- Self-sufficient offline packaging (models fetched once, then zero network).

## Next
- **Marathi answer quality** — the weakest leg. Swap the chat LLM to a stronger Indic model
  (e.g. Sarvam-1) or route more retrieval context.
- **IndicTrans2 by default** — higher-quality Indic translation once the gated weights are
  available (needs `huggingface-cli login`).
- **Isochronic dubbing** — tighter lip/length alignment for the voiceover.
- **Packaging** — single-file `.exe` (PyInstaller) bundling weights for a double-click install.
- **Domain adaptation** — LoRA fine-tune on agri corpora; glossary-hit + groundedness eval.
- **Any-language** — extend beyond hi/mr/en (Whisper + NLLB already cover far more).

## Nice to have
- Multi-turn voice sessions, voice-picking per language, richer chat sourcing UI.
- Automated tests for the pipeline, workers and endpoints.
- Optional GPU acceleration when VRAM is available.
