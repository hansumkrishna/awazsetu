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

# Runtime packages this release ADDS. Normally the update pack carries no
# runtime at all -- that is the whole point of it being a quarter of a megabyte.
# This release is the exception: IndicTrans2 could not run in the packaged
# interpreter because IndicTransToolkit and its dependencies were never
# installed there, so every packaged copy fell back to NLLB. Shipping the app
# fix without these would leave that untouched. Roughly 20 MB compressed, which
# is still four hundred times smaller than re-downloading the package.
RUNTIME_ADDS = ("IndicTransToolkit", "indicnlp", "sacremoses", "joblib",
                "morfessor", "pandas", "pytz", "dateutil")
RUNTIME_SITE = os.path.join("runtime", "python", "Lib", "site-packages")
# Files the operator owns. Shipping them would silently reset a machine that has
# been configured -- model choices, target languages, interface language, and
# the glossary the handover calls "the one file you will actually edit". They go
# into updated-defaults/ instead, so a curious operator can diff them and nobody
# loses work by extracting an archive. config.load() merges DEFAULTS over
# whatever settings.json holds, so a file written before this release still
# picks up every new key without being replaced.
OPERATOR_OWNED = {os.path.join("app", "settings.json"),
                  os.path.join("app", "glossary.json")}
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
     app\\ scripts\\ docs\\ runtime\\ must land beside models\\.
  3. Double-click APPLY_UPDATE.bat and let it finish.
  4. It offers to start AwazSetu at the end.

Step 3 is not optional, and extracting alone is not enough. Extracting can add
and replace files but it can never delete one, and three things have to go:
compiled Python caches that can shadow the files you just replaced, documents
this release withdrew, and stale exports. It also corrects terminology in
subtitles generated before the glossary knew about it, and rebuilds only the
voiceovers whose words actually changed. No model is re-run.

By hand instead, if you prefer: delete every __pycache__ folder, delete
docs\\DELIVERY_PLAN.md, docs\\SUBMISSION.md and docs\\TASKS.md, then run
  runtime\\python\\python.exe scripts\\apply_glossary.py
  runtime\\python\\python.exe scripts\\redub_changed.py
  AwazSetu-Check.bat

Your processed videos and uploads are untouched: they live in app\\data\\, and
this pack does not contain that folder.

Your settings are untouched too. app\\settings.json and app\\glossary.json are
deliberately NOT in this pack, because they are yours - your model choices,
your language list, your terminology. The current defaults are included under
updated-defaults\\ if you want to compare them, but nothing overwrites your
copies. Any setting this release adds takes its default automatically.


WHAT CHANGED
------------

  IndicTrans2 now actually runs. This is the big one. The packaged copy of
  Python was missing the library that loads IndicTrans2, so every installed
  copy has been quietly falling back to NLLB - which is the engine the
  documentation warns mistranslates agricultural terms. Nothing reported it,
  because the fallback works, just worse. This pack installs the missing
  library, which is why it is about twenty megabytes rather than one.

  Existing subtitles and voiceovers are unaffected: they were produced with
  IndicTrans2 already. What changes is everything produced from now on - new
  uploads, and the translation of chat answers.

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
                rel = os.path.relpath(p, REPO)
                if rel in OPERATOR_OWNED:
                    continue
                files.append((p, rel))
    for n in LOOSE:
        p = os.path.join(REPO, n)
        if os.path.exists(p):
            files.append((p, n))

    for pkg in RUNTIME_ADDS:
        base = os.path.join(REPO, RUNTIME_SITE, pkg)
        if not os.path.isdir(base):
            print(f"  !! {pkg} missing from the runtime; IndicTrans2 will not run")
            continue
        for root, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for n in names:
                if n.endswith(".pyc"):
                    continue
                q = os.path.join(root, n)
                files.append((q, os.path.relpath(q, REPO)))
    # six is a single module, not a package
    six = os.path.join(REPO, RUNTIME_SITE, "six.py")
    if os.path.exists(six):
        files.append((six, os.path.relpath(six, REPO)))

    os.makedirs(DIST, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("APPLY_THIS_UPDATE.txt", READ_ME)
        # The one-click applier goes at the ROOT of the zip so it lands next
        # to AwazSetu.bat when the archive is extracted into an installation.
        # It is also shipped in scripts/ as an ordinary tracked file.
        bat = os.path.join(REPO, "scripts", "APPLY_UPDATE.bat")
        if os.path.exists(bat):
            z.write(bat, "APPLY_UPDATE.bat")
        for src, arc in sorted(files, key=lambda x: x[1]):
            z.write(src, arc)
        for rel in sorted(OPERATOR_OWNED):
            q = os.path.join(REPO, rel)
            if os.path.exists(q):
                z.write(q, "updated-defaults/" + os.path.basename(rel))

    print(f"{OUT}")
    print(f"  {len(files)} files, {os.path.getsize(OUT)/1e6:.2f} MB")
    names = {a for _s, a in files}
    for must in ("app/i18n.py", "app/langid.py", "app/paths.py", "app/chat.py"):
        win = must.replace("/", os.sep)
        print(f"  {'ok ' if win in names else 'MISSING'} {must}")
    print("UPDATE_DONE")


if __name__ == "__main__":
    main()
