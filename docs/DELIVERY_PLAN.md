# AwazSetu — Final Delivery Plan (15 Sep 2026)

**Hard deadline:** BAIF Documentation Pack, 15 Sep 2026 EoD.
**Team:** Fluent Fusion. **Submit to:** anshul.sharma@hsbc.com, cc sagar.muzumdar@hsbc.co.in.

---

## Decisions taken

| # | Decision | Rationale |
|---|---|---|
| D1 | Ship everything tonight, in one pass | Operator choice; the pack is a hard deadline |
| D2 | **llama-cpp-python replaces Ollama**, Ollama kept as an auto-detected fallback | The bundled Ollama blobs are already GGUF (magic `47 47 55 46`), so the same weights load in-process from a 7.1 MB wheel. Removes a 1.5 GB installer, an `xcopy` into `%USERPROFILE%`, and a second server process |
| D3 | **Both** packages are zero-install | "Directly executable" cannot be met by only one build |
| D4 | **Full re-run at large-v3** | Every shipped manifest said `asr_model: small`, the weakest Indic model in the guide |
| D5 | ASR on GPU, MT and TTS on CPU, as three phases | They want different hardware; interleaving left the GPU idle during the CPU-bound stages |
| D6 | Drop duplicate `pytorch_model.bin` weights from packages | Every HF repo ships an identical `model.safetensors`; transformers ignores the `.bin`. **3.73 GB saved**, verified to change nothing |
| D7 | Pin the wheel set instead of resolving it | The existing offline kit had drifted to numpy 2.2.6 / torch 2.14 / transformers 4.45 — a combination nobody had ever built from |

---

## Track A — Content

- [x] **A0** Establish real costs: large-v3 `int8_float16` on a 4 GB RTX 3050 Ti
- [x] **A1** Fix `app/asr.py` CUDA compute type — plain `float16` OOMs large-v3 at 4 GB
- [x] **A2** Driver `scripts/reprocess_all.py`, driven from each item's cached source so
      content hashes, work-folder ids and URLs stay stable
- [x] **A3** Restart-safe: a transcript is re-used when it already came from the target model
- [x] **A4** Delete the 2 manifest-less junk folders
- [ ] **A5** Phase 1 — re-ASR all items with large-v3 *(10 of 12 done, RTF 0.23–0.66)*
- [ ] **A6** Phase 2 — IndicTrans2 into 4 languages + subtitles, 3 items in parallel
- [ ] **A7** Phase 3 — rebuild all voiceovers (`scripts/build_dubs_par.py`)
- [ ] **A8** Verify: every item has 4 subtitle tracks + 4 voiceovers

## Track B — Zero-install runtime ✅

- [x] **B0** `llama_cpp_python-0.3.35-win_amd64.whl` (7.1 MB) + `diskcache`
- [x] **B1** Embedded Python 3.10.11 at `runtime/python/`, `site` enabled
- [x] **B2** Pinned wheel set (`requirements-pinned.txt`): torch 2.5.1+cpu, numpy 1.26.4,
      transformers 4.44.2, ctranslate2 4.8.0, faster-whisper 1.2.1
- [x] **B3** `runtime/bin/ffmpeg.exe` + `config.ffmpeg_exe()`; 3 bare call sites replaced
- [x] **B4** `app/llm.py` — backend `llamacpp` (default) | `ollama` (auto-detected)
- [x] **B5** `AwazSetu.bat` — one double-click, no prerequisites
- [x] **B6** `AwazSetu-Check.bat` → `scripts/doctor.py`, an 11-point preflight
- [x] **B7** **Clean-room verified** — 10/11 with no system Python and a stripped PATH

## Track C — Model Garden ✅

- [x] **C1** `app/garden.py` — 13 models, Odia column, TTS section, all 3 MT directions,
      disk + RAM footprints, measured speeds, hardware-tier fit
- [x] **C2** Corrected guidance that had gone false: NLLB labelled `DEFAULT`, IndicTrans2
      labelled "needs huggingface-cli login", large-v3 labelled CUDA-OOM at 4 GB
- [x] **C3** Hardware probe: RAM, cores, GPU + VRAM, free disk → tier
- [x] **C4** `/garden` — quality heatmap, footprint bars, "this machine" panel, install badges
- [x] **C5** Four one-click presets with RAM-budget bars; a preset that needs an absent
      model is disabled, not silently saved
- [x] **C6** Cross-linked from the library and Settings

## Track D — Packaging

- [x] **D1** `scripts/package.py` rewritten for the zero-install layout
- [x] **D2** Fixed the contradiction: LITE was pinned to `nllb` + `["hi","mr","en"]`,
      contradicting both the app defaults and the manifests inside that same package
- [x] **D3** Split archives with SHA-256 manifest + self-joining `.bat`
- [x] **D4** Freed 18 GB by removing the superseded 3 Sep FULL build
- [ ] **D5** Build LITE and FULL from the completed library
- [ ] **D6** Clean-room verification of both

## Track E — Tests & evidence

- [x] **E1** New `platform` suite: FFmpeg without PATH, embedded runtime, assistant
      *answers* (not merely loads), offline enforcement, Garden coverage, preset honesty
- [x] **E2** New `media` suite: audio-only sources, Odia subtitles and voiceovers,
      source-file integrity, no subtitle-less items
- [x] **E3** Test evidence moved to `docs/` (`notes/` is gitignored and never shipped)
- [ ] **E4** Full suite green once the content re-run completes

## Track F — Submission

- [x] **F1** Architecture diagram (hand-written SVG, crisp in print)
- [x] **F2** All 7 required sections written
- [x] **F3** `scripts/build_docpack.py` renders HTML + PDF offline via WeasyPrint —
      **every figure is read from the live repository, never typed in**
- [x] **F4** 12-page PDF produced
- [x] **F5** README and INSTALL_OFFLINE rewritten; 20 stale facts corrected across
      RUNBOOK, HANDOVER, USP_VS_BHASHINI
- [x] **F6** Pushed — `origin/main` was 6 commits behind, so the repo link in the
      submission would have shown an empty-looking project
- [ ] **F7** Regenerate the pack with final numbers; add team number and contacts

---

## Defects found and fixed during this work

| Where | Defect | Impact |
|---|---|---|
| `app/server.py` | `load_manifest` trusted the stored content hash instead of the folder | One library item rendered a player whose every URL pointed at a non-existent directory — no video, no subtitles, no chat, and no error |
| `app/asr.py` | CUDA compute type hardcoded to `float16` | large-v3 could not load on a 4 GB GPU at all |
| `scripts/reprocess_all.py` | A shared CUDA context across items | Exhausted the 4 GB card after two items, then failed **every** subsequent item with `invalid device ordinal` |
| `app/mt.py` | One subprocess per target language | `mr→hi` and `mr→or` both use the `indic-indic` checkpoint, so it was loaded twice per item; and `AWAZ_CPU_THREADS` unset fell back to 4 threads on a 16-thread machine |
| `scripts/package.py` | LITE settings contradicted the manifests in the same package | A reprocess inside LITE would silently degrade to NLLB and drop Odia |
| `offline_kit/wheels` | Never built from; drifted to numpy 2.x | The documented offline install would likely have failed on the day |
| `scripts/test_e2e.py` | Suites ran as a second module copy | A full run reported "0/0 passed" while recording 12 results |
| Whisper `small` | Silently truncating audio | Recovered speech rose from 73.7 to **81.6 minutes** once re-run with large-v3 |

## Investigated and found NOT to be defects

* **MMS-TTS weight-norm warning.** Loading any voice reports `weight_g`/`weight_v` unused
  and `parametrizations.weight.original0/1` newly initialised, which reads as random
  WaveNet weights. All 128 tensors were verified equal to the checkpoint and synthesis is
  bit-identical with and without a manual remap. The warning is cosmetic; a "fix" was
  written, measured to change nothing, and removed.

## Open questions

1. **Team number** for the filename (`TeamName[team #]`).
2. **Owners/contacts** for the Handover section.
