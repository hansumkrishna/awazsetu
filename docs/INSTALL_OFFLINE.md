# AwazSetu — offline install on a bare Windows laptop

For a machine with **nothing installed and no internet**. Everything needed is on this drive.
Budget **20–30 minutes**. Do it during the setup window, not in front of the panel.

---

## What to copy onto the USB drive

```
AwazSetu\                       <- the whole repo folder
   app\                         (code)
   app\data\work\               <- PRE-PROCESSED VIDEOS. Do not skip: this is the demo.
   models\                      <- 13 GB of model weights (git-ignored, must be copied)
   scripts\  notes\  requirements.txt
   offline_kit\
      installers\python-3.10.11-amd64.exe
      installers\OllamaSetup.exe
      ffmpeg\ffmpeg.exe  ffprobe.exe
      wheels\                   <- every Python dependency, for offline pip
      ollama-models\            <- copy of %USERPROFILE%\.ollama\models (qwen2.5 3b + 1.5b)
```

> **Before leaving:** copy `%USERPROFILE%\.ollama\models` into `offline_kit\ollama-models`.
> Without it Ollama has no chat model and cannot download one at the venue.
> Total drive size ≈ **18 GB** (models alone are 13 GB). Use a **32 GB USB 3.0** drive —
> USB 2.0 will take well over an hour to copy.

---

## Step 1 — Python (3 min)

Run `offline_kit\installers\python-3.10.11-amd64.exe`

- **TICK "Add python.exe to PATH"** on the first screen. This is the step people miss.
- Choose "Install Now".

Verify in a **new** Command Prompt:
```bat
python --version
```
Expect `Python 3.10.11`.

## Step 2 — FFmpeg (1 min)

No installer needed — just make the two binaries reachable:
```bat
mkdir C:\ffmpeg
copy offline_kit\ffmpeg\ffmpeg.exe  C:\ffmpeg\
copy offline_kit\ffmpeg\ffprobe.exe C:\ffmpeg\
setx PATH "%PATH%;C:\ffmpeg"
```
Open a **new** Command Prompt and check:
```bat
ffmpeg -version
```

## Step 3 — Python packages, fully offline (5–8 min)

```bat
cd <drive>\AwazSetu
python -m pip install --no-index --find-links offline_kit\wheels -r requirements.txt
python -m pip install --no-index --find-links offline_kit\wheels torch
```
`--no-index` guarantees pip never tries the internet. If a package is reported missing,
it is missing from `wheels\` — re-run `pip download` on a connected machine.

## Step 4 — Ollama + the chat model (5 min)

1. Run `offline_kit\installers\OllamaSetup.exe` (default options).
2. Copy the pre-pulled models across — Ollama cannot download at the venue:
   ```bat
   xcopy /E /I /Y offline_kit\ollama-models %USERPROFILE%\.ollama\models
   ```
3. Start the server and confirm:
   ```bat
   ollama serve
   ```
   In a second Command Prompt:
   ```bat
   ollama list
   ```
   Expect `qwen2.5:3b` and `qwen2.5:1.5b`.

## Step 5 — Start AwazSetu (1 min)

```bat
cd <drive>\AwazSetu
python app\run.py
```
Open <http://127.0.0.1:5000>. The library should list the 8 BAIF videos immediately —
they are pre-processed, so nothing needs to run.

## Step 6 — Verify before the panel arrives (3 min)

```bat
python scripts\test_e2e.py assets settings
```
Expect every line `PASS`. Then, by hand:
1. Open **401.2 Housing of Goat**, switch subtitles मराठी → हिंदी → English.
2. Play the Hindi voiceover.
3. Ask one chat question and wait for the answer (this also warms the model, removing
   the ~10 s cold start from the live demo).

**Then turn Wi-Fi off** and leave it off. It is the cleanest proof of the offline claim.

---

## If something goes wrong

| Symptom | Fix |
|---|---|
| `python` not recognised | PATH tick was missed in Step 1. Re-run the installer → Modify → tick "Add to PATH", then open a NEW Command Prompt |
| `ffmpeg` not recognised | Open a NEW Command Prompt (PATH only applies to new windows) |
| pip tries to reach the internet | You omitted `--no-index`. Re-run the exact command in Step 3 |
| `ollama list` is empty | Step 4.2 was skipped or copied to the wrong path. It must be `%USERPROFILE%\.ollama\models` |
| Chat says "model could not be loaded — not enough free memory" | Close other apps; in **/settings** switch the chat LLM to `qwen2.5:1.5b` |
| Library page is empty | `app\data\work\` was not copied. Copy it — it holds all 8 processed videos |
| Anything else | See `notes\RUNBOOK.md` §4 |

---

## Nothing here touches the internet

Python, FFmpeg, Ollama, every Python wheel, all model weights and all processed videos come
from this drive. `run.py` sets `HF_HUB_OFFLINE=1`, so the app cannot reach out even if a
network is present. The only reason to be online at BAIF is if you skipped a copy step.
