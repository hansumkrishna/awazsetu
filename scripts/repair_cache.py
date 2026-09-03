"""Re-apply the sanitiser + glossary to already-processed videos.

The ASR transcript is cached in `transcript.raw.json`, so this re-runs everything
*after* transcription (sanitise -> glossary -> translate -> subtitles -> manifest)
without paying for ASR again. Use it after changing glossary.json or the sanitiser.

    python scripts/repair_cache.py
"""
import os
import sys
import glob
import json
import time
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("AWAZ_NLLB_CT2_DIR", os.path.join(REPO, "models", "nllb-int8"))
os.environ.setdefault("AWAZ_MT", "nllb")
os.environ["CUDA_VISIBLE_DEVICES"] = ""      # repair is CPU-only; no ASR is run
sys.path.insert(0, os.path.join(REPO, "app"))

from pipeline import process_video

WORK = os.path.join(REPO, "app", "data", "work")


def main():
    dirs = sorted(d for d in glob.glob(os.path.join(WORK, "*"))
                  if os.path.exists(os.path.join(d, "transcript.raw.json")))
    print(f"{len(dirs)} cached video(s) to repair", flush=True)
    out = []
    for i, d in enumerate(dirs, 1):
        vid = os.path.basename(d)
        video = os.path.join(d, "video.mp4")
        if not os.path.exists(video):
            print(f"[{i}/{len(dirs)}] {vid}: no video.mp4, skipping", flush=True)
            continue
        before, prev_name = 0, None
        mp = os.path.join(d, "manifest.json")
        if os.path.exists(mp):
            try:
                _m = json.load(open(mp, encoding="utf-8"))
                before = len(_m.get("segments", []))
                prev_name = _m.get("video")   # keep the library title across a repair
            except Exception:
                pass
        # Drop derived artefacts so they are rebuilt; KEEP transcript.raw.json.
        for fn in os.listdir(d):
            if fn.startswith(("subs.", "dub.", "bundle")) or fn == "manifest.json":
                try:
                    os.remove(os.path.join(d, fn))
                except Exception:
                    pass
        t0 = time.time()
        try:
            m = process_video(video, WORK, log=lambda s: print("    " + str(s), flush=True))
            # process_video sees work/<id>/video.mp4, so restore the real title
            if prev_name and prev_name != "video.mp4" and m.get("video") != prev_name:
                m["video"] = prev_name
                json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            after = len(m["segments"])
            print(f"[{i}/{len(dirs)}] {vid}: {before} -> {after} segments "
                  f"in {time.time()-t0:.0f}s", flush=True)
            out.append({"id": vid, "video": m.get("video"), "before": before,
                        "after": after, "dropped": before - after, "ok": True})
        except Exception as e:
            traceback.print_exc()
            out.append({"id": vid, "ok": False, "error": str(e)})
    with open(os.path.join(REPO, "notes", "repair_results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nREPAIR_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
