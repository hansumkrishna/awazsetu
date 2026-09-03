# AwazSetu — Audit Findings & Phased Task Plan
Started 2026-09-03 07:50 IST · Demo 12:00 IST · Setup window 10:00–12:00

Status key: `[x]` done · `[~]` in progress · `[ ]` pending · `[>]` deferred beyond session

---

## PHASE 0 — P0 correctness (demo-killers) — **DONE**

| # | Finding | Evidence | Fix | St |
|---|---|---|---|---|
| 0.1 | **Every video transcribed as Hindi.** `run.py:90` called `process_video()` without `src_lang`, which defaulted to `"hi"`. All 8 test videos are Marathi. Decoding Marathi with a Hindi-forced decoder yields fluent-looking Devanagari nonsense. | Auto-detect now reports `mr p=0.99` | `src_lang=None` → `detect_language()` first. Never assume. | [x] |
| 0.2 | **Whisper drift/invention.** `condition_on_previous_text` defaulted ON, so one mishearing contaminated all later segments. | शेळी→शेडि cascade | `condition_on_previous_text=False` | [x] |
| 0.3 | **No domain priming.** Decoder had no reason to prefer शेळीपालन over phonetic non-words. | — | `initial_prompt` per language from `glossary.json` | [x] |
| 0.4 | **Prompt echo loop.** First `initial_prompt` was a comma word-list; Whisper regurgitated it — "प्रशिक्षण करें" ×13. | Observed in medium/GPU bench | Rewrote prompts as natural sentences + added token-based `_dedupe()` | [x] |
| 0.5 | **Greedy decoding.** `beam_size=1` is materially worse for Indic. | — | `beam_size=5` (configurable) | [x] |
| 0.6 | **Hallucination, no refusal path.** Goat-rearing video answered as "modeling career in India", confidently, in 2 languages. | `bug llm 2.jpeg` | `NOT_IN_TRANSCRIPT` sentinel + explicit "transcript may contain ASR errors → refuse" rule; refusal shows closest lines | [x] |
| 0.7 | **`[LLM त्रुटिः ]`** — error text was machine-**translated** like an answer, and carried an empty message. | `bug llm.jpeg` | Pre-written per-language UI strings, never MT'd; `_describe()` handles empty `str(e)`; both primary+fallback reasons reported and logged | [x] |
| 0.8 | **Every answer cited 0:04/0:35/0:43.** `_retrieve()` did `[i for i in order if scores[i]>0] or order` — with zero matches it returned the first 3 segments as "citations". | Both answers in `bug llm 2.jpeg` | `_retrieve()` returns `(hits, best_score)`; citations suppressed when `best == 0` | [x] |
| 0.9 | **Settings could not switch the chat model.** `chat.py` read `AWAZ_LLM` at *import* time, so a saved change needed a restart. | Code read | `_model()` / `_fallback()` read env per call | [x] |
| 0.10 | **`langs` setting was inert** — saved but never passed to the pipeline. | Code read | `run.py` passes `targets=` from settings | [x] |
| 0.11 | Untranslated bracket strings in `server.py` (`[chat engine not ready: …]`, "couldn't hear anything") | Code read | Localised hi/mr/en strings | [x] |
| 0.12 | Hardcoded `"ollama"` binary in `server.py` voice path | Code read | uses `config.ollama_exe()` | [x] |
| 0.13 | ASR quality was invisible — garbage passed downstream silently | — | per-segment `avg_logprob` + `transcript_confidence()`; manifest carries it; chat appends a caveat when unusable | [x] |


### Phase 0b — further defects found during verification (all fixed)

| # | Finding | Evidence | Fix | St |
|---|---|---|---|---|
| 0.14 | **Degenerate character loop survived everything.** Segment [0:30] of 401.1 was `ব` x60 (Bengali), scored `lp=-0.07` (high confidence), and NLLB then invented fluent English from it: *"I have not seen any of you, but I have seen you..."* | manifest of 401.1 | New `sanitize_segments()`: collapses character-level loops, rejects wrong-script segments, drops low-diversity garbage. Runs before translation and is logged, not silent. | [x] |
| 0.15 | Token-level `_dedupe` could not see loops with **no whitespace** | as above | Added `_collapse_chars()` | [x] |
| 0.16 | **MMS-TTS Marathi produced 0.1s of silence** — `mms-tts-mar` ships `phonemize=True`, so the tokenizer demanded the `phonemizer` package + espeak-ng binary; it failed silently and fell back to empty audio | voice round-trip test: mr = 6,444 bytes vs hi = 65,580 | Verified the mar vocabulary is **60 Devanagari tokens** (not IPA) — the model takes Devanagari directly, exactly like mms-tts-hin. `_load_tts()` forces `phonemize=False` when phonemizer is absent. **Marathi voice now works with no new system dependency.** 204,332 bytes. | [x] |
| 0.17 | **No text chunking for TTS** — VITS degrades/fails on long segments | code review | `split_for_tts()` splits on danda/sentence/comma with a hard wrap; `synth_text()` concatenates | [x] |
| 0.18 | `MMS[lang]` raised `KeyError` for an unknown language | code review | `.get(lang, en)` | [x] |
| 0.19 | Mic STT lacked the anti-garbage settings used by the video path | code review | `condition_on_previous_text=False`, domain prompt, beam 3, dedupe + garbage guard | [x] |
| 0.20 | **`nllb_dir()` pointed at `app/models/`** instead of the repo-level `models/` — the Settings panel reported NLLB missing whenever `run.py` had not set the env var | `translate_engines()` returned `nllb: False` | `models_dir()` resolves the repo root; HF cache falls back correctly too | [x] |
| 0.21 | Generic MT rendered "goat rearing" as the Hindi loan **बकरीपालन** in Marathi (native: शेळीपालन) | chat output | `target_fixes` in glossary + `correct_target()` applied to subtitles, dubs **and** chat answers — the terminology-control the rubric asks about | [x] |
| 0.22 | Settings page listed models but gave **no guidance** on which suits which language | user requirement | `MODEL_GUIDE` in config.py + a per-language ratings table and live hints on the Settings page | [x] |

### Verified working (evidence)

| Journey | Result |
|---|---|
| Language auto-detection | **mr, p=0.95–0.99** on all 8 videos (was hard-coded `hi`) |
| Chat on-topic (en) | *"goat rearing, including health services, field management, and sustainable farming practices"* — **hallucination fixed** |
| Chat on-topic (hi) | बकरी पालन ... स्वास्थ्य सेवाएं, क्षेत्र प्रबंधन — correct |
| Chat on-topic (mr) | शेळीपालन ... आरोग्य सेवा, शेती व्यवस्थापन — correct |
| Chat citations | varied timestamps (5s/85s/193s) — no longer stuck at 0:04/0:35/0:43 |
| Chat refusal | off-topic → *"This video does not cover that"*, `grounded:false` |
| Dub (hi) | 344.6s audio for a 342.9s video — aligned; 3m6s on CPU |
| Voice TTS+STT | en / hi / mr all round-trip; Marathi fixed |
| Settings API | POST persists to settings.json **and** applies live in-process |
| Settings status | 5 Whisper sizes, 3 MMS voices, NLLB ✓, guide exposed |

## PHASE 1 — Models & offline guarantee — **DONE**
- [x] All weights local in `models/` (13 GB): whisper tiny/base/small/medium/large-v3,
      MMS-TTS hin/mar/eng, NLLB-200 CT2 INT8, **IndicTrans2 all three directions**
- [x] Benchmarked on real Marathi video -> **medium** chosen (RTF 0.42 GPU; large-v3 CUDA-OOMs on 4 GB)
- [x] IndicTrans2 unlocked with the HF token after licence acceptance
- [x] **Measured IndicTrans2 vs NLLB on real content: kept NLLB.** IT2 was only marginally
      better and 2.3x slower (25s vs 11s); ASR quality, not MT, is the bottleneck.
      IT2 remains selectable in Settings.
- [x] Model availability detected from weights on disk, not a token file (a failed gated
      download leaves a 17 KB stub that used to report as installed)
- [x] `scripts/download_models.py` updated to reproduce this exact model set

## PHASE 2 — Batch pre-processing (the scored "fallback plan") — **DONE**
- [x] All 8 BAIF videos processed -> `app/data/work/` (Marathi detected p=0.95-1.00)
- [x] Repair pass applied sanitiser + 100-entry Marathi glossary + terminology enforcement
- [x] **393 segments, 0 degenerate remaining**; 0 untranslated across hi/mr/en
- [x] Dubs pre-generated for the demo videos (instant playback = the fallback)

## PHASE 3 — End-to-end verification — **DONE (62/62)**
- [x] Subtitles hi/mr/en on all 9 videos (45 asset checks)
- [x] Text chat grounded + specific in all 3 languages
- [x] Refusal on out-of-scope in all 3 languages
- [x] Voice TTS + STT round trip in all 3 languages (Marathi fixed)
- [x] Settings switching verified to actually apply
- [x] Dub generation (344.6s audio for a 342.9s video - aligned)
- [x] Exports SRT x3 + transcript; search; status
- [x] Evidence written to `notes/TEST_EVIDENCE.md`

## PHASE 4 — Target hardware (i5 / 16 GB / bare Windows) — **PARTIAL**
- [x] `cpu_threads=0` (auto) so it adapts to the target CPU instead of this 16-thread box
- [x] `device=cpu` default; GPU only used here to pre-process
- [x] Memory-saver: LLM unloaded before mic STT; 3B -> 1.5B auto-fallback
- [x] **Offline installer kit** (`offline_kit/`): Python 3.10, Ollama, FFmpeg, 337 MB of
      wheels, Ollama model blobs, plus `INSTALL_OFFLINE.md` for a bare machine
- [ ] Startup preflight warning on low RAM / missing model / Ollama down
- [ ] Measured CPU-only timing on an i5-class machine (only GPU numbers are measured;
      CPU is estimated at 2-3x realtime from the `small` CPU benchmark)

## PHASE 5 — Rubric documentation — **DONE**
- [x] `notes/TEST_EVIDENCE.md` - 62 cases, pass/fail, defects traced to fixes
- [x] `notes/RUNBOOK.md` - deployment, config, rollback, logging, troubleshooting
- [x] `notes/HANDOVER.md` - user guide, technical doc, 4-session training plan, limitations
- [x] `notes/USP_VS_BHASHINI.md` - like-for-like, quantified, honest limitations
- [x] `notes/DEMO_SCRIPT.md` - 18-minute run-of-show with a fallback for every step
- [x] `offline_kit/INSTALL_OFFLINE.md` - bare-Windows offline install

## DEFERRED (beyond this session)
- [>] Document translation (docx/pptx) - rubric names "file formats"; cut for reliability
- [>] Sarvam-1 / stronger Indic LLM for Marathi answer quality
- [>] Isochronic dubbing (length-matched lip alignment)
- [>] Fine-tune / LoRA on BAIF agri corpora
- [>] PyInstaller single-exe packaging

---

## Benchmarks (measured, not estimated)
90 s Marathi slice from *401.2 Housing of Goat*:

| Model | Device | Decode | RTF | Quality |
|---|---|---|---|---|
| small | CPU (6 temps, 4 thr) | 204.6 s | 2.27 | Garbled - unusable |
| medium | GPU | 39.0 s | 0.43 | Prompt-echo loop (pre-fix) |
| medium | GPU (fixed) | 38.2 s | 0.42 | **Meaningful Marathi - chosen** |
| large-v3 | GPU | - | - | CUDA OOM (4 GB card) |

Full pipeline per video (GPU): 165-406 s depending on length.
Translation mr->hi+en: NLLB 11 s vs IndicTrans2 25 s for 6 segments.
Language detection: Marathi at p=0.95-1.00 on all 8 videos.
