# BAIF Hackathon — what to submit, and how

**Deadline:** 15 Sept 2026, EoD.
**To:** anshul.sharma@hsbc.com · **cc:** sagar.muzumdar@hsbc.co.in
**Naming convention:** `BAIF_Hackathon_TeamName[team #]_DocumentationPack`

---

## Team 7 — Fluent Fusion

| Name | Role | Contact |
|---|---|---|
| Sivani Tumuluri | **Team lead** | sivani.tumuluri@noexternalmail.hsbc.com |
| Hansum Krishna | **Technical owner** — pipeline, models, packaging | hansum.krishna@hsbc.co.in |
| Lahari Gali | Team member | lahari.gali@hsbc.co.in |
| Uthsava Kumari | Team member | — |
| Sakshi Jain | Team member | — |

**The build and models, on Google Drive:**
https://drive.google.com/drive/folders/1XU_praP4yQI96gfpGzHaK01Uthx6WYmc?usp=sharing

To regenerate the pack at any time — every figure is re-read from the repository:

```bat
python scripts\build_docpack.py --team 7 --owners "Sivani Tumuluri <sivani.tumuluri@noexternalmail.hsbc.com> | Team lead; Hansum Krishna <hansum.krishna@hsbc.co.in> | Technical owner - pipeline, models, packaging; Lahari Gali <lahari.gali@hsbc.co.in> | Team member; Uthsava Kumari | Team member; Sakshi Jain | Team member" --pdf
```
---

## What to attach

| # | Item | Where | Note |
|---|---|---|---|
| 1 | **The Documentation Pack (PDF)** | `dist\BAIF_Hackathon_FluentFusion[7]_DocumentationPack.pdf` | The required deliverable. PDF is their stated preference. |
| 2 | **Git repository link** | https://github.com/hansumkrishna/awazsetu | Listed in their email as an acceptable supporting link. Push before sending. |
| 3 | **The LITE package** (optional) | `dist\awazsetu-lite.zip` (split into ~1.9 GB parts) | Too large to email. Share via a drive link if they want to run it themselves. `JOIN-awazsetu-lite.bat` rejoins the parts. |

A demo video is listed as an optional example of a supporting file. There isn't one;
the repo and the pack carry the evidence, and the demo was given in person on 3 Sept.

---

## Suggested covering note

> Dear Anshul,
>
> Please find attached the Documentation Pack for **Team 7 — Fluent Fusion**, covering the
> six areas requested: solution overview, architecture, tech stack, performance,
> testing evidence, deployment and handover.
>
> Two points worth drawing out:
>
> **It requires no installation.** The deliverable is a folder you extract and a file
> you double-click — no Python, no FFmpeg, no model downloads, no internet, not even
> on a freshly imaged Windows laptop. An embedded runtime and every model ship inside
> it. This was verified in a clean-room test with no system interpreter reachable.
>
> **Every figure in the pack is generated from the running system**, not typed in —
> segment counts, confidence scores, measured throughput, model footprints and the
> preflight output are all read from the repository at build time, and the pack can be
> regenerated to prove it.
>
> The source is at https://github.com/hansumkrishna/awazsetu. I am happy to walk
> through any section or run the system live.
>
> The build itself, if you would like to run it:
> https://drive.google.com/drive/folders/1XU_praP4yQI96gfpGzHaK01Uthx6WYmc?usp=sharing
>
> Kind regards,
> Sivani, Hansum, Lahari, Uthsava and Sakshi
> *Team 7 — Fluent Fusion*

---

## If they ask to run it themselves

Send the LITE parts plus `JOIN-awazsetu-lite.bat`, and these three lines:

1. Run `JOIN-awazsetu-lite.bat`, then extract the zip it produces.
2. Double-click `AwazSetu-Check.bat` — it should print READY.
3. Double-click `AwazSetu.bat`.

Nothing else. If step 2 reports a problem it names the component, so it is
diagnosable without us.

---

## Honest points to be ready for

These are in the pack already; it is better to raise them than to be caught by them.

- **Odia-source audio is approximate.** No open model transcribes Odia, so Odia speech
  is transcribed phonetically and translated. Odia as a *target* — from Marathi or
  Hindi — is a genuine translation and is the case BAIF actually has. Two of the
  fifteen items are Odia-source; demo from 401.2 or 401.3 instead.
- **Four languages, not twenty-two.** Bhashini is broader. The pack says where Bhashini
  is genuinely better and when to prefer it.
- **No speaker separation**, so multi-speaker interviews produce one transcript.
- **The assistant is a 3B model**, deliberately confined to the transcript. It refuses
  rather than guessing, which is the correct behaviour but will read as a limitation if
  someone expects a general chatbot.
