# AwazSetu — Test Evidence

Run: 2026-09-15 15:43:33 · **8/8 passed**

| Suite | Case | Lang | Result | Time | Detail |
|---|---|---|---|---|---|
| platform | ffmpeg_resolves | - | PASS | 0.1 | bundled: ffmpeg version 7.1.1-essentials_build-www.gy |
| platform | embedded_runtime | - | PASS | 7.8 | 3.10.11 2.5.1+cpu |
| platform | llm_answers | - | PASS | 8.0 | backend=llamacpp model=qwen2.5:3b -> '12 goats.' |
| platform | offline_enforced | - | PASS |  | HF_HUB_OFFLINE=1 |
| platform | garden_catalog | - | PASS | 4.6 | 13 models, tasks=['asr', 'llm', 'mt', 'tts'], tier=workstation, presets=4 |
| platform | presets_honest | - | PASS | 0.3 | every preset's availability matches what is installed |
| platform | preset_apply_roundtrip | - | PASS | 0.6 | medium -> fast_low_ram=small -> balanced=medium; unknown preset returns 404 |
| platform | odia_not_a_source | or | PASS |  | langs.py records Odia as target-only; no ASR model claims to read it |
