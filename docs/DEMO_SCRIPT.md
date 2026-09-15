# AwazSetu — 30-minute demo run-of-show

Structure follows BAIF's suggested shape: **2 min intro · 18 min demo · 5 min Q&A · 5 min buffer.**

> **Golden rule: everything on screen runs from cache.** All 15 items are pre-processed —
> transcript, four subtitle tracks and four voiceovers are already on disk. Nothing in the
> scored path needs live inference except the assistant, which has an automatic fallback.
> **Never start a processing job while the panel is watching.**

---

## Before they arrive (setup window)

1. Copy the package folder onto the laptop, or extract the zip. If it arrived as parts,
   run `JOIN-awazsetu-lite.bat` first.
2. Double-click **`AwazSetu-Check.bat`**. Confirm it prints `READY`. It verifies the
   runtime, FFmpeg, every model, the assistant (by generating a real answer), the library
   and the memory budget — and names anything that is wrong.
3. Double-click **`AwazSetu.bat`**. A browser opens at <http://127.0.0.1:5000>.
4. **Warm the assistant once** — ask any question so the model is resident. This removes
   the cold-load pause from the live demo.
5. Pre-open tabs: the library, one player page, and `/garden`.
6. Close other applications. The assistant wants ~3 GB free.
7. **Turn off Wi-Fi — then say so.** It is the strongest proof of the offline claim.

There is nothing to install. No Python, no pip, no FFmpeg, no Ollama, no PATH changes.
If someone asks what the setup was, the honest answer is "extract a folder and
double-click one file", and that is worth saying out loud.

---

## 1. Intro + problem statement (2 min)

> "BAIF produces field training content in Marathi. A farmer in another district speaks
> Hindi. A programme officer needs English. An audience in Odisha needs Odia. Today that
> means someone re-recording or re-typing every video.
>
> AwazSetu takes any video **or audio file** and makes it understandable in Hindi,
> Marathi, English and Odia — subtitles, a full spoken voiceover in each language, and an
> assistant you can *talk to* about the content. Everything runs on this laptop.
> **The Wi-Fi is off. Nothing leaves this machine.**"

Say the hardware line early: *i5, 16 GB, no GPU — the machine BAIF already has.*

---

## 2. Demo — core flow first (18 min)

### a. The library (1 min)
Open the library. Fifteen items, video and audio, each showing its languages. Point out
that every one is **already processed** — this is what the farmer-facing machine looks
like on day one, not an empty app.

### b. Switchable subtitles (3 min)
Open **401.2 Housing of Goat** (Marathi source).
Play 20 seconds. Switch the subtitle language मराठी → हिंदी → English → ଓଡ଼ିଆ **while it
plays**. Emphasise: this is instant because it is a file read. No model is loading.

### c. Voiceover (3 min)
Switch the audio track to the **Hindi** voiceover, then **Odia**. Let each play for 15
seconds.

> "This is a Marathi video speaking Odia. No one re-recorded it. And note what that
> required: Odia speech recognition does not exist in any open model we can ship — so we
> transcribe the Marathi, translate it, and give Odia a voice. Odia is an output language
> here, and we are explicit about that rather than pretending otherwise."

### d. Ask the video a question (4 min)
Type a question in Marathi. Show the answer **with timestamped citations**, and click one
to jump to that moment in the video.

Then ask something the video does **not** cover — a share price, say. It refuses, in the
user's language, and shows the closest lines it found.

> "A confident wrong answer is worse than no answer. The model is required to answer only
> from the transcript and to say so when the fact is not there."

### e. Voice chat — the literacy unlock (4 min)
Tap the microphone. Ask out loud, in Marathi. Hear the answer spoken back.

> "This is the journey that matters. A farmer who cannot read or type can still ask a
> question and get an answer. Everything else we have shown is a convenience; this is
> access."

### f. Model Garden (3 min)
Open **/garden**.

- It has **detected this machine** — memory, cores, tier — and recommends a preset.
- The matrix answers *which model, for which language, on this hardware*, and names the
  runner-up for every choice.
- Every ASR row is a dash for Odia. Say why: no model can do it, and the tool says so
  rather than offering a choice that would fail.
- Apply a preset in one click. Note that a preset needing an absent model is **disabled**,
  not silently saved.

If time is short, cut this to 90 seconds and show only the matrix and one preset.

---

## 3. Panel Q&A (5 min)

Likely questions and the honest answers:

| Question | Answer |
|---|---|
| "Is this really offline?" | The Wi-Fi is off. `HF_HUB_OFFLINE=1` is set before any model loads, so a download is not merely avoided but impossible. Nothing binds beyond `127.0.0.1`. |
| "How does it compare to Bhashini?" | Bhashini is broader — 22 languages, full-precision, maintained centrally. We run the same IndicTrans2 family distilled to fit 16 GB. Use Bhashini for breadth and volume online; use this when the material is sensitive, the venue is offline, and the audience needs to listen. |
| "How long does a new video take?" | Roughly half the video's length per pass, once, at ingest. Playback is instant because nothing is generated live. |
| "What does it cost to run?" | Nothing. No API, no per-minute charge. Reprocessing the whole library is free. |
| "Can we add a language?" | One entry in `app/langs.py`, if an ASR model, a translation direction and a voice exist for it. For several Indian languages the voice does not exist offline yet. |
| "What is it worst at?" | Odia-source audio — we transcribe it phonetically, which is approximate. Multi-speaker interviews, because there is no speaker separation. And a 3B assistant is a 3B assistant: it is deliberately confined to the transcript. |
| "What happens if it breaks mid-demo?" | Everything on screen is precomputed, so playback cannot break. Only the assistant needs a model, and it falls back to a smaller one automatically. |

---

## 4. Buffer (5 min)

If there is time, in order of value:

1. **Add a file live** — drag in a short clip and let the weighted progress bar run. Only
   do this if you have five clear minutes; it is the one part that is not instant.
2. **Export** — download an `.srt`, or the `.mkv` bundle with every subtitle track and
   voiceover muxed in, and open it in VLC to show the content leaves cleanly.
3. **Search across the library** — find a phrase and jump straight to that moment in
   whichever video contains it.

---

## If something goes wrong

| Symptom | Do this |
|---|---|
| Assistant will not load | Apply the **Fast & low RAM** preset in the Model Garden. It switches to the smaller model immediately, no restart. |
| A page will not load | The console window shows the error. Close it and double-click `AwazSetu.bat` again; nothing is lost. |
| Anything unexplained | Run `AwazSetu-Check.bat` in front of them. Diagnosing openly reads better than improvising. |

**Do not** start a reprocess, change models mid-flow, or open a video that is still
processing. Nothing in the run-of-show above requires any of those.
