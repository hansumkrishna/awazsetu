# AwazSetu — Final Delivery Plan (15 Sep 2026)

**Hard deadline:** BAIF Documentation Pack, 15 Sep 2026 EoD.
**Team:** Fluent Fusion. **Submit to:** anshul.sharma@hsbc.com, cc sagar.muzumdar@hsbc.co.in.

Three tracks run concurrently. Track A is CPU/GPU-bound and unattended; Track B and C
are hands-on. The ordering below is by dependency, not by priority.

---

## Decisions taken (15 Sep)

| # | Decision | Rationale |
|---|---|---|
| D1 | Ship **everything tonight** in one shot | Operator choice; the pack is a hard deadline |
| D2 | **llama-cpp-python replaces Ollama**, Ollama kept as auto-detected fallback | The bundled Ollama blobs are already GGUF (magic `47 47 55 46`), so the same weights load in-process from a 7.1 MB wheel. Removes a 1.5 GB installer, an `xcopy` into `%USERPROFILE%`, and a second server process |
| D3 | **Both** packages are zero-install. LITE ≈ 6.5 GB, FULL ≈ 20 GB | "Directly executable" is the requirement; it cannot be met by only one build |
| D4 | **Full re-run at large-v3** for all 15 items | Every shipped manifest says `asr_model: small` — the weakest Indic model in the guide. Measured RTF 0.711 on the 4 GB GPU ⇒ ~52 min, not the 6 h first estimated on CPU |
| D5 | ASR/MT on GPU, TTS on CPU, run as two parallel phases | `dub_worker.py` pins `CUDA_VISIBLE_DEVICES=""`, so voiceovers never contend with whisper for VRAM |

---

## Track A — Content (unattended)

- [x] **A0** Establish real costs: large-v3 `int8_float16` on RTX 3050 Ti (4.3 GB) → loads 6.9 s, **RTF 0.711**
- [x] **A1** Fix `app/asr.py` CUDA compute type — `float16` OOMs large-v3 at 4 GB; `int8_float16` does not
- [x] **A2** Driver `scripts/reprocess_all.py`, driven from each item's own cached source so content hashes (and therefore work-folder ids and URLs) stay stable
- [ ] **A3** Phase 1 — re-ASR + IndicTrans2 + 4 languages + subtitles, all 15 items *(running)*
- [ ] **A4** Delete the 2 manifest-less junk folders *(folded into A3)*
- [ ] **A5** Phase 2 — rebuild all 60 voiceovers (15 × hi/mr/en/or) in parallel CPU workers
- [ ] **A6** Verify: every item has 4 subtitle tracks + 4 voiceovers + a coherent manifest

**Fixes 9 of 15 broken items:** 7 stuck on NLLB with no Odia, 5 with zero voiceovers,
1 (`6758e814`) with voiceovers but **no subtitles at all**, 2 junk folders.

## Track B — Zero-install runtime

- [x] **B0** Download `llama_cpp_python-0.3.35-win_amd64.whl` (7.1 MB) + `diskcache`
- [ ] **B1** Embedded Python 3.10 at `runtime/python/`, `site` enabled, all packages preinstalled
- [ ] **B2** **Pin a known-good wheel set.** The current kit is untested and version-skewed: it holds numpy **2.2.6** / torch **2.14.0** / transformers **4.45.2**, while the only proven-working combination is numpy **1.26.4** / torch **2.5.1** / transformers **4.44.2**. numpy 2.x is an ABI break for older CTranslate2/torch builds. *This is the single largest untested risk in the delivery.*
- [ ] **B3** Bundle `ffmpeg.exe`/`ffprobe.exe` in `runtime/bin/`; add `config.ffmpeg_exe()`; replace the 3 bare call sites (`asr.py:28`, `server.py:287`, `voice_worker.py:102`)
- [ ] **B4** `app/llm.py` — backend `llamacpp` (default, bundled GGUF) | `ollama` (auto-detected); refactor `chat.py` and `voice_worker.py` onto it
- [ ] **B5** `AwazSetu.bat` — sets `HF_HOME`, `PATH`, `AWAZ_*`, starts the server, opens the browser. One double-click, no prerequisites
- [ ] **B6** First-run preflight: verify interpreter, ffmpeg, models, GGUF, disk, RAM — report in the UI instead of crashing
- [ ] **B7** **Clean-room verification** — extract to a fresh folder with no system Python, no PATH entries, and run

## Track C — Model Garden

- [ ] **C1** Rebuild `MODEL_GUIDE`: add the **Odia column** (absent today), a **TTS section** (the 4 MMS voices are invisible today), all **4 MT direction models** (only 2 entries today), disk size, VRAM, measured speed, hardware-tier fit
- [ ] **C2** Correct the stale notes: NLLB is labelled `"DEFAULT"` (false since 3 Sep) and IndicTrans2 `"HF-gated — needs login"` (false, installed and default). large-v3 is labelled CUDA-OOM at 4 GB — **disproven today**
- [ ] **C3** Hardware detection: RAM, cores, GPU + VRAM, free disk → machine tier
- [ ] **C4** `/garden` page: model × language quality heatmap, footprint bars, "your machine" panel, installed-vs-available badges
- [ ] **C5** One-click presets — Max quality / Balanced / Fast & low-RAM / Demo-safe — writing through to `settings.json`
- [ ] **C6** Cross-link Settings ⇄ Garden; Garden explains *why* a model is recommended for *this* machine and *that* language

## Track D — Packaging

- [ ] **D1** Rewrite `scripts/package.py` for the zero-install layout
- [ ] **D2** Fix the contradiction at `package.py:122`: LITE is pinned to `"nllb"` + `["hi","mr","en"]`, contradicting both the app defaults and the manifests already inside that same package. `LITE_HUB` also omits IndicTrans2, so any reprocess inside LITE silently degrades
- [ ] **D3** Build LITE (~6.5 GB) and FULL (~20 GB) — FULL is >8 months stale (10:12, 3 Sep: pre-IndicTrans2, pre-Odia, pre-audio, pre-media-fix)
- [ ] **D4** Split archives into 2 GB parts + a self-joining `.bat` (GitHub releases cap at 2 GB/file)
- [ ] **D5** Clean-room verification of **both** packages

## Track E — Tests & evidence

- [ ] **E1** Extend `scripts/test_e2e.py`: Odia, audio-only sources, Garden, LLM backend, ffmpeg resolver, zero-install layout
- [ ] **E2** Expected-vs-actual test table for the pack (the rubric asks for exactly this)
- [ ] **E3** Benchmark table: RTF per ASR model, MT throughput, TTS speed, RAM/VRAM peaks, cold-start

## Track F — Submission

- [ ] **F1** Architecture diagram (components + data flow)
- [ ] **F2** Write the 7 required sections: Solution overview · Architecture + NFRs · Tech stack · Performance · Testing evidence · Deployment + rollback · Handover
- [ ] **F3** Render to PDF offline (weasyprint 66.0 is already installed)
- [ ] **F4** Name it `BAIF_Hackathon_FluentFusion[team #]_DocumentationPack.pdf`
- [ ] **F5** Refresh `RUNBOOK` / `HANDOVER` / `INSTALL_OFFLINE` / `README` — all still describe NLLB, 3 languages and on-demand dubs
- [ ] **F6** **Push the 6 unpushed commits.** `origin/main` is still at `d71071a`, so the "Git repo" link in the submission currently shows an empty-looking project
- [ ] **F7** Optional: demo video

---

## Open questions

1. **Team number** for the filename — the convention is `TeamName[team #]`.
2. **Owners/contacts** for the Handover section.
3. Does **EoD** mean midnight IST tonight?
4. Is a **demo video** wanted, or are the repo + pack sufficient?
