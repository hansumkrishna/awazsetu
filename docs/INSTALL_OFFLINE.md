# AwazSetu — installing on a bare Windows laptop

**There is no installation.** This document used to describe a six-step procedure —
Python installer, PATH edit, two `pip` runs, an Ollama installer and a blob copy. None of
that exists any more. It is kept because the old procedure is still the fallback if a
locked-down machine refuses to run the bundled interpreter.

---

## The procedure

1. Copy the package folder to the machine.
   If it arrived as split parts, run **`JOIN-awazsetu-lite.bat`** first and extract the
   resulting zip.
2. Double-click **`AwazSetu-Check.bat`**. Confirm it prints `READY`.
3. Double-click **`AwazSetu.bat`**. A browser opens at <http://127.0.0.1:5000>.

Budget **five minutes**, almost all of it copying files. Then turn Wi-Fi off and leave it
off — nothing changes, which is the cleanest way to prove the offline claim to an audience.

## Why nothing needs installing

| Normally required | Where it is now |
|---|---|
| Python 3.10 + “Add to PATH” | `runtime\python\` — an embedded interpreter with every package preinstalled |
| `pip install -r requirements.txt` | already installed inside that runtime, from a pinned wheel set |
| FFmpeg on `PATH` | `runtime\bin\ffmpeg.exe` — resolved from the package, never from `PATH` |
| Ollama installer + `ollama serve` + blob copy | gone. The assistant runs in-process via `llama-cpp-python`, loading `models\llm\*.gguf` |
| Model downloads | `models\` ships every weight; `HF_HUB_OFFLINE=1` makes a download impossible |

Nothing is written outside the package folder — no registry keys, no `%USERPROFILE%`
state, no services, no scheduled tasks. Uninstalling is deleting the folder.

## What the preflight checks

`AwazSetu-Check.bat` runs `scripts\doctor.py`, which verifies, in order:

1. the interpreter is the bundled one and is 3.10;
2. all thirteen Python packages import;
3. FFmpeg runs, and reports whether it is the bundled or a system copy;
4. which Whisper models are present, and whether the one in settings is among them;
5. which translation engines and IndicTrans2 directions are installed;
6. that a voice exists for every language;
7. which assistant backend will serve the next call;
8. that the assistant **actually answers** a grounded question — a model that loads but
   cannot answer is still broken;
9. that the library is present and how many items are complete;
10. that the recommended preset fits available memory;
11. that the offline flags are enforced.

It changes nothing and downloads nothing. A failure names its own fix.

---

## Fallback: rebuilding the environment by hand

Only needed if a machine's policy blocks the embedded interpreter. The FULL package
carries `rescue_kit\` for exactly this.

```bat
rem 1) Python 3.10 — TICK "Add python.exe to PATH" on the first screen
rescue_kit\installers\python-3.10.11-amd64.exe

rem 2) the same pinned environment, entirely offline
python -m pip install --no-index --find-links rescue_kit\wheels-pinned -r requirements-pinned.txt

rem 3) run against the system Python instead of the bundled one
set PYTHONIOENCODING=utf-8
python app\run.py
```

`--no-index` guarantees pip never reaches the internet. Use `requirements-pinned.txt`,
not `requirements.txt`: the pinned file holds the exact versions this project is known to
work with, and a floating resolve drifts to numpy 2.x, which is an ABI break for the
CTranslate2 and torch builds in use.

FFmpeg still does not need installing — the app resolves `runtime\bin\ffmpeg.exe` itself.

## If something goes wrong

| Symptom | Fix |
|---|---|
| `runtime\python\python.exe is missing` | The package was extracted partially. Re-extract, keeping the folder structure intact |
| Library page is empty | `app\data\work\` was not copied. It holds every processed item |
| “not enough free memory” in chat | Close other applications, or apply the **Fast & low RAM** preset in the Model Garden |
| Antivirus quarantines the runtime | Whitelist the folder, or use the `rescue_kit` fallback above |
| Anything else | Run `AwazSetu-Check.bat`; it names the failing component |
