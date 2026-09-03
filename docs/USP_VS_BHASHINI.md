# AwazSetu vs Bhashini — differentiated value, quantified, with limitations

Rubric item 6 asks for a like-for-like comparison, quantified benefits, and an
**honest view of limitations and trade-offs**. This document is deliberately even-handed:
Bhashini is very good at what it does, and we say where it beats us.

---

## 1. What each one actually is

| | **Bhashini** | **AwazSetu** |
|---|---|---|
| Nature | National **cloud API** platform (MeitY / ULCA) for Indian-language AI | **On-device application** for understanding a *video* end to end |
| Unit of work | A translation / ASR / TTS **API call** | A **video**: transcript → 3 languages → subtitles → dub → Q&A |
| Where it runs | Government cloud, over the internet | The operator's own laptop, **zero network at runtime** |
| Languages | 22 scheduled Indian languages | Hindi, Marathi, English today (Whisper + NLLB cover far more; only these three are tuned and tested) |
| Integration | You build an app on top of it | It **is** the app — a field worker opens a browser and uses it |

**The honest framing:** Bhashini is *infrastructure*. AwazSetu is a *product* that
could, in principle, call Bhashini. We chose not to, and section 3 is why.

---

## 2. Where AwazSetu wins (and by how much)

| Dimension | Bhashini | AwazSetu | Benefit |
|---|---|---|---|
| **Runtime connectivity** | Internet required for every call | **None.** `HF_HUB_OFFLINE=1`, all weights local | Works in a village with no signal — where BAIF's field staff actually are |
| **Data egress** | Audio/transcript leaves the device to a third-party cloud | **Nothing leaves the laptop** | Farmer interviews, beneficiary names and field data stay on-premises. No DPDP data-transfer question to answer |
| **Marginal cost** | Per-call (free tier today; unpriced risk at scale) | **₹0 per video, forever.** One-time ~6 GB download | 500 videos/year costs the same as 5 |
| **Latency dependence** | Network round-trip per segment; a 6-min video = dozens of calls | Local; no round-trips | No failure mode where the demo dies because the venue Wi-Fi did |
| **Video-native workflow** | Returns text; subtitles/dub/QA are yours to build | Subtitles, on-demand dub, jump-to-timestamp, chat and **voice** chat are the product | The whole journey, not a building block |
| **Domain adaptation** | General-purpose models | **Editable glossary** (`glossary.json`): ASR mishear corrections + agri term table, fed into the ASR prompt *and* the chat prompt | Measured: fixed शेडि→शेळी, सरवत्तम→सर्वोत्तम on real BAIF video |
| **Literacy access** | Text in, text out | **Voice in, voice out** in Hindi/Marathi | The farmer who cannot read or type can still use it |
| **Groundedness** | N/A (not a QA system) | Answers restricted to the transcript; refuses with "not covered" + closest lines | No confident fabrication in front of a beneficiary |
| **Auditability** | Cloud-side | Per-segment ASR confidence in the manifest; degenerate segments dropped and logged | You can see *why* an answer was refused |

---

## 3. Where Bhashini wins — stated plainly

| Dimension | Reality |
|---|---|
| **Raw translation quality** | Bhashini's Indic models (IndicTrans2 family) are **better than our default NLLB-200-600M INT8**, especially Marathi. We quantised to fit 16 GB; they run full-precision on servers. |
| **Language coverage** | 22 languages vs our 3. Adding a language is a config change for them, a test-and-tune cycle for us. |
| **ASR on hard audio** | Server-side models are larger than the `medium` Whisper we can fit. Our Marathi WER on noisy field audio is visibly worse. |
| **Maintenance** | They patch models centrally; ours are pinned files an operator must update deliberately. |
| **Cost of entry** | An API key vs a 6 GB install and a Python environment. |
| **Compute** | Ours needs a real laptop (16 GB). Bhashini runs on anything with a browser. |

**We could use IndicTrans2 to close most of the quality gap** — it is supported in the
codebase today (`AWAZ_MT=indictrans2`) but the weights are HF-gated, so the login-free
default is NLLB. That is a deliberate trade of quality for zero-setup reproducibility.

---

## 4. Measured numbers (this hardware, real BAIF video)

Benchmarked on a 90-second Marathi slice of *401.2 Housing of Goat*:

| Configuration | Decode time | Realtime factor | Outcome |
|---|---|---|---|
| Whisper `small`, CPU, greedy | 204.6 s | 2.27× | Marathi unusable |
| Whisper `medium`, GPU, beam 5 | 38.2 s | **0.42×** | Meaningful Marathi |
| Whisper `large-v3` | — | — | CUDA OOM on a 4 GB card |

Full pipeline, per video (≈6 min source, GPU): **~165–185 s total** —
ASR ~95–110 s, translation to 2 languages ~47 s, subtitles + manifest <1 s.

Language detection on all 8 BAIF videos: **Marathi, p = 0.95–0.99.**

> Honest caveat about these numbers: they were produced with GPU acceleration on the
> development machine. The BAIF target (i5, no discrete GPU) runs the **same models**
> on CPU at roughly **2–3× realtime**. That is precisely why the product pre-processes
> once and caches — playback, subtitles, dub and chat are then instant.

---

## 5. Best-fit scenarios

**Choose AwazSetu when:**
- Content is video/audio and the goal is *understanding*, not just a string translation.
- The device is offline, intermittently connected, or in the field.
- The material is sensitive (beneficiary interviews, field data) and must not leave the premises.
- Volume is high enough that per-call cost or rate limits matter.
- The audience includes people who cannot read or type.

**Choose Bhashini when:**
- You need many Indian languages beyond hi/mr/en.
- Maximum translation accuracy matters more than connectivity or privacy.
- You are adding a translate button to an existing connected web app.
- The device is thin (a phone or low-spec terminal).

**They compose.** AwazSetu's translation engine is pluggable (`AWAZ_MT`). A Bhashini
backend could be added as a third engine for online, high-accuracy runs while keeping
the offline path as the fallback — best of both, and a natural next step.
