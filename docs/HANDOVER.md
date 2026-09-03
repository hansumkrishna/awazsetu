# AwazSetu — Handover & Training Pack

Everything BAIF needs to **use, support and extend** AwazSetu without the build team present.

---

## Part A — User guide (field / programme staff)

### What it does
You give it a video. It listens, writes down what was said, translates it into
**Hindi, Marathi and English**, and lets you **read subtitles, hear a voiceover, or
just ask it questions** — by typing or by speaking. Everything happens on the laptop;
nothing is sent to the internet.

### The five things you can do

**1. Add a video**
Open <http://127.0.0.1:5000>, click **Upload**, pick the file. A progress bar shows
transcribing → translating → done. The same video is never processed twice.

**2. Watch with subtitles in your language**
Click the video. Under the player, choose **हिंदी / मराठी / English**.
The subtitles change instantly — the video does not reload.

**3. Hear it in another language (dub)**
Choose a language under **"Hear it in another language"**. It plays immediately — every
voiceover is built when the video is saved, not while you are watching. Press **Off** to
return to the original audio.

**4. Ask the video a question (typing)**
In **Ask this video**, pick the answer language, type your question, press **Ask**.
You get a short answer plus **timestamp buttons** — click one to jump to that moment.
If the video does not actually cover your question, it will say so rather than guess.

**5. Ask by speaking (no typing, no reading)**
Press the **🎙 microphone** button, speak your question, press it again to stop.
It transcribes what you said, answers, and **speaks the answer aloud** in your
language. This is designed for users who cannot read or type.

### What to expect
- **Answers come only from the video.** Ask about something else and it will say
  "this video does not cover that" and show the closest lines. That is correct behaviour.
- **Speed.** Saving a video takes a while the first time — it transcribes, translates,
  builds all the subtitles and records every voiceover, showing each step on a progress
  bar. After that, watching, switching language and playing a voiceover are all instant.
  Only the assistant's answers are worked out live.
- **Accuracy.** Clear studio narration transcribes well. Noisy field audio, heavy
  dialect or several people talking at once will produce mistakes — check the
  subtitles before relying on a fact.

---

## Part B — Technical documentation (whoever supports it)

### Ownership & support model
| Area | Owner | Notes |
|---|---|---|
| Running the app day-to-day | BAIF operator | `python app\run.py`; no admin rights needed |
| Settings / model choice | BAIF technical focal point | `/settings`, select-only, cannot break the install |
| Adding videos | Any user | Upload in the browser |
| Model updates | Technical focal point | Deliberate: re-run `scripts/download_models.py` with `AWAZ_OFFLINE=0` |
| Code changes | Any Python developer | ~1,600 lines, single Flask app, no framework beyond Flask |

### Code map
| File | Responsibility |
|---|---|
| `app/run.py` | Launcher: resolves `models/`, sets offline env, applies settings |
| `app/server.py` | Flask routes — player, upload, chat, voice, dub, export, search, settings |
| `app/pipeline.py` | One video end to end: extract → detect language → ASR → sanitise → glossary → translate → subtitles |
| `app/asr.py` | Whisper wrapper + **language detection, repetition guard, garbage sanitiser, confidence scoring** |
| `app/mt.py`, `translate_worker.py`, `indictrans_worker.py` | Translation engines (subprocess-isolated) |
| `app/chat.py` | Grounded RAG: BM25 + Ollama, **refusal guard**, per-language UI strings |
| `app/voice_worker.py` | Mic STT + spoken answers |
| `app/dub_worker.py` | MMS-TTS voiceover, timestamp-aligned, chunked |
| `app/config.py` | Settings store, env bridge, system status, **per-language model guidance** |
| `app/glossary.json` | **The main tuning surface** — see below |

### The one file you will actually edit: `app/glossary.json`
Three sections, all plain text — no code, no retraining:

1. **`asr_prompts`** — a natural sentence per language listing domain vocabulary.
   Whisper reads this before transcribing, which makes it far likelier to produce
   शेळीपालन instead of a phonetically similar non-word.
   *Write a fluent sentence, never a comma-separated word list* — a list gets echoed
   back into the transcript.
2. **`source_fixes`** — literal find-and-replace applied to the transcript per language.
   When you spot a recurring mis-hearing, add it here: `"शेडि": "शेळी"`.
3. **`terms`** — en/hi/mr term table, injected into the chat prompt so the model uses
   BAIF's vocabulary.

After editing, press **Re-process** on a video to apply it.

### Extending it
- **A new language:** add it to `langs` in Settings, add an `asr_prompts` entry, and
  confirm an MMS-TTS voice exists for it. Whisper and NLLB already cover many more.
- **Better Indic translation:** `huggingface-cli login`, accept the IndicTrans2 terms,
  then set the engine to `indictrans2` in Settings.
- **Better Marathi answers:** swap the chat LLM for a stronger Indic model (e.g. Sarvam-1)
  in Ollama; it appears in the Settings dropdown automatically.
- **A new domain** (dairy, horticulture): replace the `asr_prompts` sentence and the
  `terms` table. No retraining required.

### Verifying a change
```bat
python scripts\test_e2e.py
```
Runs every journey in every language and writes `notes/TEST_EVIDENCE.md` with a
pass/fail matrix. Run it after any model or glossary change.

---

## Part C — Training plan for BAIF

| Session | Audience | Duration | Content |
|---|---|---|---|
| 1. Using AwazSetu | Field & programme staff | 45 min | Part A hands-on: upload a video, switch subtitles, play a dub, ask a typed question, ask a spoken question. Each participant does all five on their own. |
| 2. Getting good results | Content owners | 45 min | What makes audio transcribe well; reading the confidence warning; when to trust an answer; how to spot and report a bad transcript. |
| 3. Tuning the glossary | Technical focal point | 60 min | Live edit of `glossary.json` — add a mis-hearing correction, re-process, see it fixed. This is the single highest-leverage skill to transfer. |
| 4. Operations | Technical focal point + IT | 60 min | Install from scratch, Settings page, model switching, reading logs, the troubleshooting table, running the test suite, rollback. |

**Success criterion for handover:** the BAIF technical focal point can, unaided,
install the app on a fresh laptop, process a new video, fix a recurring
mis-transcription via the glossary, and run the test suite to prove nothing broke.

---

## Part D — Known limitations (stated honestly)

| Limitation | Impact | Mitigation / roadmap |
|---|---|---|
| Marathi ASR on noisy field audio is imperfect | Some subtitle lines will be wrong | Glossary corrections; confidence warning shown; a larger model is a Settings change |
| Chat LLM is 3B (fits 16 GB) | Reasoning is shallow vs a cloud model; Marathi phrasing is the weakest | Answers are grounded and refuse when unsure; Sarvam-1 is the roadmap fix |
| Dub is timestamp-aligned, not lip-synced | Voiceover does not match mouth movement | Acceptable for training content; isochronic fitting already limits drift |
| Three languages tuned (hi/mr/en) | Other Indian languages untested | Whisper + NLLB cover far more; each needs a tune-and-test cycle |
| Processing is CPU-bound (~2–3× realtime on an i5) | A 10-min video takes ~20–30 min first time | Pre-process in advance; the cache makes playback instant |
| No document (docx/pptx) translation yet | Text files must go through another tool | Deliberately deferred; the pipeline is text-agnostic and could accept it |
