"""Stage a drag-and-drop folder for Google Drive.

    python scripts/stage_gdrive.py

Builds dist/gdrive/ using HARD LINKS for the multi-gigabyte parts, so the staged
folder costs no extra disk — the same blocks appear under two names on the same
volume. Google Drive uploads the file content, so the links are invisible to it.
Small files are copied normally.
"""
from __future__ import annotations
import os
import shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")
OUT = os.path.join(DIST, "gdrive")

HOW_TO_RUN = """AwazSetu - how to run it
========================

Offline Hindi / Marathi / English / Odia video and audio translation, dubbing,
subtitles, and an assistant you can type to or speak to.

There is NOTHING to install. No Python, no FFmpeg, no Ollama, no model downloads,
no internet - not even on a freshly imaged Windows laptop.


WHICH DOWNLOAD DO I WANT?
-------------------------

  1-run-it-here/        <-- START HERE if you just want to use it.
                            10.6 GB, 6 parts. Everything needed, nothing else.

  2-everything/             15.8 GB, 8 parts. The same thing plus every spare
                            model (Whisper large-v3, the NLLB fallback engine)
                            and a rescue kit. For long-term custody.

  3-for-developers/         15.4 GB, 8 parts. Models and runtime only, to pair
                            with a git clone of the source. Ignore this unless
                            you intend to change the code.

Pick ONE. They are alternatives, not a sequence.


HOW TO RUN IT
-------------

  1. Download every part in the folder you chose, plus the .bat and the .txt.
     Keep them all together in one folder.

  2. Double-click  JOIN-....bat
     It rejoins the parts into a single .zip. Takes a couple of minutes.

  3. Extract that .zip. You will get a folder.

  4. Inside it, double-click  AwazSetu-Check.bat
     This verifies everything and prints READY. It changes nothing. If something
     is wrong it names exactly what, so you do not have to guess.

  5. Double-click  AwazSetu.bat
     A browser opens at http://127.0.0.1:5000.

  That is the whole procedure.


WHAT YOU CAN DO
---------------

  * Play any of the 15 pre-processed videos and audio files. Switch subtitles
    between Marathi, Hindi, English and Odia while it plays.
  * Switch the spoken voiceover to any of those four languages.
  * Ask the video a question by typing, in any of the four languages. You get an
    answer with timestamps you can click to jump to.
  * Tap the microphone and ask out loud. You hear the answer spoken back.
  * Drop in your own video or audio file and it processes on the machine.
  * Open the Model Garden to see which model suits your hardware and language.

Everything you see is already computed, so playback is instant. Only the
assistant runs live.


TURN THE WI-FI OFF
------------------

Nothing changes. That is the point.


IF SOMETHING GOES WRONG
-----------------------

  Run AwazSetu-Check.bat. It names the failing component.

  "not enough free memory" when asking a question
      Close other applications, or open the Model Garden and apply the
      "Fast & low RAM" preset.

  The library page is empty
      The app\\data\\work folder did not extract. Re-extract the zip.

  A part downloaded badly
      Each folder has a .parts.txt listing a SHA-256 for every part. Check the
      suspect one and re-download just that part.


REQUIREMENTS
------------

  Windows 10 or 11, 64-bit. 16 GB RAM. About 25 GB free disk while extracting.
  No administrator rights. No network.

  Nothing is written outside the folder - no registry entries, no services,
  no user-profile data. To uninstall, delete the folder.


KNOWN LIMITATION worth stating up front
---------------------------------------

  Two of the fifteen items were recorded in Odia. No open model can transcribe
  Odia speech, so those two are transcribed phonetically and are approximate.
  Odia produced FROM Marathi or Hindi - which is the normal case - is a genuine
  translation and is accurate. For a demonstration, use "401.2 Housing of Goat"
  or "401.3".
"""

GROUPS = {
    "1-run-it-here": ("awazsetu-lite.zip.", "JOIN-awazsetu-lite.bat",
                      "awazsetu-lite.zip.parts.txt"),
    "2-everything": ("awazsetu-full.zip.", "JOIN-awazsetu-full.bat",
                     "awazsetu-full.zip.parts.txt"),
    "3-for-developers": ("awazsetu-assets.zip.", "JOIN-awazsetu-assets.bat",
                         "awazsetu-assets.zip.parts.txt"),
}


def place(src, dst):
    """Hard-link when possible (free), copy when not."""
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
        return "link"
    except Exception:
        shutil.copy2(src, dst)
        return "copy"


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    with open(os.path.join(OUT, "HOW_TO_RUN.txt"), "w", encoding="utf-8") as f:
        f.write(HOW_TO_RUN)

    for name in os.listdir(DIST):
        if name.endswith(".pdf") and "DocumentationPack" in name:
            place(os.path.join(DIST, name), os.path.join(OUT, name))

    total = 0
    for folder, (prefix, joinbat, partstxt) in GROUPS.items():
        d = os.path.join(OUT, folder)
        os.makedirs(d, exist_ok=True)
        n = 0
        for name in sorted(os.listdir(DIST)):
            if name.startswith(prefix) and name[-3:].isdigit():
                place(os.path.join(DIST, name), os.path.join(d, name))
                total += os.path.getsize(os.path.join(DIST, name))
                n += 1
        for extra in (joinbat, partstxt):
            p = os.path.join(DIST, extra)
            if os.path.exists(p):
                place(p, os.path.join(d, extra))
        print(f"  {folder:20} {n} part(s)")

    print(f"\nstaged -> {OUT}")
    print(f"upload size: {total/1e9:.2f} GB (hard-linked, so no extra disk used)")


if __name__ == "__main__":
    main()
