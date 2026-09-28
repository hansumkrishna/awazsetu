"""Build the small update pack, for people who already have a full package.

    python scripts/build_update.py

Produces dist/awazsetu-update.zip -- a couple of hundred kilobytes.

Why this exists: the models and the embedded runtime are 12 of the package's
13 GB and they do not change when the application does. Re-uploading eleven
gigabytes to deliver a one-megabyte fix wastes a day of someone's bandwidth,
and on a field connection it may simply not finish.

Deliberately excludes `app/data/`. That is the user's library, their uploads and
their settings; an update that overwrote it would destroy exactly the work the
person cares about. Nothing else in the tree is user data.
"""
from __future__ import annotations
import os
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")
OUT = os.path.join(DIST, "awazsetu-update.zip")

TREES = ("app", "scripts", "docs")
LOOSE = ("README.md", "AwazSetu.bat", "AwazSetu-Check.bat", "requirements-pinned.txt")
# `data` is excluded here BY NAME rather than by path, unlike in package.py,
# because this pack copies only the three source trees above -- there is no
# torch/utils/data in scope to be caught by the same name.
SKIP_DIRS = {"__pycache__", ".git", ".locks", "data"}

READ_ME = """AwazSetu - update pack
======================

Only for people who ALREADY downloaded and extracted a full AwazSetu package.
If you have not, ignore this file and take 1-run-it-here instead.

There are no models in here. The models and the embedded Python did not change,
which is why this is a few hundred kilobytes rather than eleven gigabytes.


TO APPLY
--------
  1. Close AwazSetu if it is running.
  2. Extract this zip INTO your AwazSetu folder, replacing files when asked.
     app\\ scripts\\ docs\\ must land beside runtime\\ and models\\.
  3. Double-click AwazSetu-Check.bat  ->  READY
  4. Double-click AwazSetu.bat

Your processed videos, uploads and settings are untouched. They live in
app\\data\\, and this pack does not contain that folder.


WHAT CHANGED
------------

  The whole application is now in four languages, not just the subtitles.
  Every button, label and message exists in Hindi, Marathi, English and Odia,
  and the home page asks which one you want before anything else. It asks
  again each time you come back to it, because these laptops get shared - turn
  that off in Settings if yours does not.

  Asking a question in Hindi now answers in Hindi.
  Two separate faults caused this. The answer language was being taken from the
  video's own language while the highlighted button showed something else, so a
  Marathi video answered in Marathi with Hindi selected. And when a translation
  failed, the English text was shown as though it were the answer. The language
  of the answer is now checked before you see it - including telling Hindi from
  Marathi, which share an alphabet - and if it cannot be produced in the
  language you chose, it says so rather than quietly giving you another one.

  Speaking in Odia now says plainly that no speech model can recognise Odia,
  instead of transcribing noise and answering the noise. Typing still works,
  and the answer still comes back in Odia, written and spoken.

  Spoken questions in Hindi and Marathi are transcribed more accurately, and
  the microphone will no longer quietly fall back to a model that returns the
  wrong script for Devanagari.

  Settings no longer removes Odia from your language list when you press Save.

  The chat model list in Settings works again - you can switch to the smaller
  assistant on a machine that is short of memory.
"""


def main() -> None:
    files = []
    for top in TREES:
        for root, dirs, names in os.walk(os.path.join(REPO, top)):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for n in names:
                if n.endswith(".pyc"):
                    continue
                p = os.path.join(root, n)
                files.append((p, os.path.relpath(p, REPO)))
    for n in LOOSE:
        p = os.path.join(REPO, n)
        if os.path.exists(p):
            files.append((p, n))

    os.makedirs(DIST, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("APPLY_THIS_UPDATE.txt", READ_ME)
        for src, arc in sorted(files, key=lambda x: x[1]):
            z.write(src, arc)

    print(f"{OUT}")
    print(f"  {len(files)} files, {os.path.getsize(OUT)/1e6:.2f} MB")
    names = {a for _s, a in files}
    for must in ("app/i18n.py", "app/langid.py", "app/paths.py", "app/chat.py"):
        win = must.replace("/", os.sep)
        print(f"  {'ok ' if win in names else 'MISSING'} {must}")
    print("UPDATE_DONE")


if __name__ == "__main__":
    main()
