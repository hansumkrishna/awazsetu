# AwazSetu — 30-minute demo run-of-show
**3 Sept 2026 · 12:00–12:30 IST · Panel: Madhavi Patlori (in person), Deepika Sandeep (Zoom)**

Structure follows BAIF's suggested run-of-show: 2 min intro · 18 min demo · 5 min Q&A · 5 min buffer.

> **Golden rule: everything below runs from cache.** All 8 BAIF videos are pre-processed.
> Nothing in the scored path requires live model inference except chat, which has a
> fallback. Never start a long processing job while the panel is watching.

---

## Before they arrive (setup window, 10:00–12:00)

1. Copy the folder from USB (repo + `models/` + `app/data/work/`).
2. Start Ollama: `ollama serve` — confirm `ollama list` shows `qwen2.5:3b`.
3. `python app\run.py` → open <http://127.0.0.1:5000>.
4. Run the smoke test: `python scripts\test_e2e.py assets settings` → expect all PASS.
5. **Warm the chat model once** — ask any question so the LLM is resident. This removes
   the ~10s cold-load from the live demo.
6. Pre-open browser tabs: library, one player page, `/settings`.
7. Close every other application. Chat needs ~3–4 GB free.
8. **Turn off Wi-Fi** — then say so. It is the strongest possible proof of the offline claim.

---

## 1. Intro + problem statement (2 min)

> "BAIF produces training content in Marathi. A farmer in another district speaks Hindi.
> A programme officer needs it in English. Today that means a person re-recording or
> re-typing every video.
>
> AwazSetu takes any video and makes it understandable in Hindi, Marathi and English —
> subtitles, a spoken voiceover, and a assistant you can *talk to* about the content.
> Everything runs on this laptop. **The Wi-Fi is off.** Nothing leaves this machine."

Say the hardware line early: *i5, 16 GB, no GPU needed — the machine BAIF already has.*

---

## 2. Demo — core flow first (18 min)

### A. The core journey (6 min) — *this is the scored one, do it first*
1. Open the library — 8 BAIF goat-rearing videos already processed.
2. Open **401.2 Housing of Goat**. Play ~15 seconds with **Marathi** subtitles.
3. Switch subtitles to **हिंदी**, then **English** — *without reloading the video*.
   > "Same video, three languages, instantly. The farmer picks their language."
4. Under "Hear it in another language", choose **हिंदी** → the Hindi voiceover plays,
   aligned to the video.
   > "For someone who cannot read, we don't just subtitle it — we speak it."

### B. Ask the video a question (4 min)
5. In **Ask this video**, answer language **English**: *"What is this video about?"*
   → grounded answer + timestamp chips. **Click a chip** — the video jumps there.
   > "Every answer is anchored to the moment in the video it came from."
6. Same question, answer language **मराठी** → answer in Marathi.
7. **Show the honesty guard.** Ask something the video does not cover:
   *"What is the share price of Reliance today?"*
   → *"This video does not cover that."*
   > "This matters more than a clever answer. It only tells you what the video actually
   > said. It will not make something up in front of a farmer."

### C. Voice — the literacy unlock (3 min)
8. Press 🎙, ask aloud in Marathi: *"शेळ्यांना कोणता चारा द्यावा?"*
   → it transcribes, answers, and **speaks the answer back** in Marathi.
   > "No reading. No typing. This is the difference between a tool for us and a tool for them."

### D. Operator control (3 min)
9. Open **/settings**. Show the live status panel: free RAM, models installed, Ollama up,
   **offline: yes**.
10. Show the **"Which model for which language?"** table — per-language ratings, RAM cost,
    and honest notes ("small: Marathi output was garbled — avoid").
    > "BAIF isn't locked into our choices. Trade accuracy for speed on a slower laptop,
    > and the page tells you exactly what you're trading."
11. Switch the chat LLM in the dropdown → save → it applies immediately.

### E. Domain adaptation — the differentiator (2 min)
12. Open `app/glossary.json`. Show `source_fixes` and `terms`.
    > "The model mis-hears शेळी as शेडि. We don't retrain anything — BAIF adds one line
    > here and re-processes. Generic translation services cannot be corrected like this.
    > That is our answer to 'why not just use Bhashini'."

---

## 3. Q&A (5 min) — likely questions

| Question | Answer |
|---|---|
| **Why not Bhashini?** | Bhashini is excellent and better at raw translation. But it needs connectivity, sends data off-device, and returns text — not subtitles, dubs and grounded Q&A. We work offline in the field, at zero marginal cost, and can be tuned to BAIF's vocabulary. And they compose — Bhashini could be added as an online engine. |
| **How accurate is it?** | Clear narration is good. Noisy field audio makes mistakes — we show a confidence warning rather than hide it. See `notes/TEST_EVIDENCE.md` for the pass/fail matrix. |
| **How long does a video take?** | ~3 min for a 6-min video with a GPU; **2–3× realtime on a plain i5**. Which is why it processes once and caches — everything you saw was instant. |
| **What if it gets an answer wrong?** | It refuses rather than guesses when the transcript doesn't cover it, and every answer carries timestamps so you can verify in one click. |
| **Can BAIF run this without you?** | Yes — `notes/RUNBOOK.md` and `notes/HANDOVER.md` cover install, settings, glossary tuning, troubleshooting and a 4-session training plan. |
| **What are the limits?** | Marathi chat phrasing is the weakest leg (small on-device LLM); dub is timestamp-aligned not lip-synced; three languages tuned so far; no document translation yet. All listed in the handover. |

---

## 4. Fallback plan (what to do when something misbehaves)

| If this fails | Do this instead | Prep |
|---|---|---|
| Chat is slow / LLM won't load | Switch to `qwen2.5:1.5b` in Settings (one dropdown, ~5s) | Both models pre-pulled |
| Chat fails completely | Show the pre-captured Q&A screenshots and move to subtitles/dub | Screenshots in `notes/` |
| Voice/mic not permitted in browser | Use the typed chat; explain the voice loop with the recorded clip | Pre-recorded wav ready |
| Dub takes too long | Every dub is pre-generated and cached — it plays instantly | Pre-generate all before 12:00 |
| A video won't open | Switch to another of the 8 — all are processed | 8 videos cached |
| Laptop is memory-starved | Close everything; Settings → smaller ASR + 1.5b LLM | Rehearsed |
| Total app failure | Walk the architecture diagram in `notes/RUNBOOK.md` §5 and the test evidence | Printed/ready |

**Time discipline:** if you are at 12:18 and still in section B, skip C and D, and go
straight to the glossary point (E) — the differentiator matters more than completeness.
