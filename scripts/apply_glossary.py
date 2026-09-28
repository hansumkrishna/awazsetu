"""Apply the glossary's target_fixes to the library that is already on disk.

    python scripts/apply_glossary.py --dry-run     # show what would change
    python scripts/apply_glossary.py               # apply, and rewrite subtitles

The glossary corrects terminology in translations, and until now it was applied
only to text produced live -- chat answers. The stored library predates it, so a
term the glossary knows to be wrong could still be sitting in a subtitle track
the viewer reads. Re-processing all fifteen items to fix a word takes hours and
re-runs models that were fine. This rewrites just the affected strings.

What it touches: `t.<lang>` in each manifest, and the WebVTT track for any
language whose text changed. Timings, transcripts, voiceovers and media are
untouched -- so a voiceover keeps saying the old word until that item is
re-processed. That is called out per item rather than hidden, because a subtitle
and a voiceover disagreeing is worse than either being wrong.
"""
from __future__ import annotations
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "app"))


def main() -> None:
    dry = "--dry-run" in sys.argv
    import paths
    from glossary import correct_target
    from subs import write_vtt

    total_items = total_segs = total_vtt = 0
    for vid, folder in paths.list_work():
        mp = os.path.join(folder, "manifest.json")
        with open(mp, encoding="utf-8") as f:
            m = json.load(f)
        changed_langs: set[str] = set()
        n = 0
        for seg in m["segments"]:
            t = seg.get("t") or {}
            for lang, txt in list(t.items()):
                if not txt:
                    continue
                fixed = correct_target(txt, lang)
                if fixed != txt:
                    t[lang] = fixed
                    changed_langs.add(lang)
                    n += 1
        if not n:
            continue
        total_items += 1
        total_segs += n
        name = (m.get("video") or vid)[:34]
        print(f"  {name:36} {n:3} segment(s) in {sorted(changed_langs)}", flush=True)
        if dry:
            continue
        with open(mp, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False)
        for lang in sorted(changed_langs):
            vtt = (m.get("vtts") or {}).get(lang) or f"subs.{lang}.vtt"
            p = os.path.join(folder, vtt)
            if os.path.exists(p):
                write_vtt(m["segments"], p, lang)
                total_vtt += 1
        dubs = [L for L in changed_langs
                if os.path.exists(os.path.join(folder, f"dub.{L}.wav"))]
        if dubs:
            print(f"  {'':36} voiceover still says the old word for "
                  f"{sorted(dubs)} until this item is re-processed", flush=True)

    verb = "would change" if dry else "changed"
    print(f"\n{verb} {total_segs} segment(s) across {total_items} item(s)"
          + ("" if dry else f"; rewrote {total_vtt} subtitle track(s)"))
    print("GLOSSARY_APPLIED")


if __name__ == "__main__":
    main()
