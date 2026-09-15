# AwazSetu — Test Evidence

Run: 2026-09-15 15:37:15 · **9/12 passed**

| Suite | Case | Lang | Result | Time | Detail |
|---|---|---|---|---|---|
| platform | ffmpeg_resolves | - | PASS |  | bundled: ffmpeg version 7.1.1-essentials_build-www.gy |
| platform | embedded_runtime | - | PASS | 3.0 | 3.10.11 2.5.1+cpu |
| platform | llm_answers | - | PASS | 6.0 | backend=llamacpp model=qwen2.5:3b -> '12 goats.' |
| platform | offline_enforced | - | PASS |  | HF_HUB_OFFLINE=1 |
| platform | garden_catalog | - | PASS | 2.1 | 13 models, tasks=['asr', 'llm', 'mt', 'tts'], tier=workstation, presets=4 |
| platform | presets_honest | - | PASS | 0.1 | every preset's availability matches what is installed |
| platform | odia_not_a_source | or | PASS |  | langs.py records Odia as target-only; no ASR model claims to read it |
| media | audio_sources_processed | - | PASS |  | 4 audio item(s), 11 video item(s) |
| media | source_file_present | - | PASS |  | every manifest points at a real source container |
| media | odia_subtitles | or | FAIL |  | 7/8 items with an Odia target have an Odia track |
| media | odia_voiceover | or | FAIL |  | 7/8 items have an audible Odia voiceover |
| media | no_subtitleless_items | - | FAIL |  | items with no subtitles at all: ['6758e814'] |

## Open defects (3)
- **media/odia_subtitles** (or): 7/8 items with an Odia target have an Odia track
- **media/odia_voiceover** (or): 7/8 items have an audible Odia voiceover
- **media/no_subtitleless_items** (-): items with no subtitles at all: ['6758e814']
