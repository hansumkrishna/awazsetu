"""Pre-process every demo video into app/data/work (cache = the scored fallback plan)."""
import os, sys, glob, time, json, traceback
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("AWAZ_NLLB_CT2_DIR", os.path.join(REPO, "models", "nllb-int8"))
os.environ.setdefault("AWAZ_WHISPER", "medium")
os.environ.setdefault("AWAZ_MT", "nllb")
sys.path.insert(0, os.path.join(REPO, "app"))
from pipeline import process_video

WORK = os.path.join(REPO, "app", "data", "work")
os.makedirs(WORK, exist_ok=True)
vids = sorted(glob.glob(os.path.join(REPO, "test_videos", "Videos", "*", "*.mp4")))
print(f"{len(vids)} videos | whisper={os.environ['AWAZ_WHISPER']} "
      f"device={os.environ.get('AWAZ_DEVICE','auto')}", flush=True)
results = []
for i, v in enumerate(vids, 1):
    name = os.path.basename(v)
    print(f"\n=========== [{i}/{len(vids)}] {name} ===========", flush=True)
    t0 = time.time()
    try:
        m = process_video(v, WORK, log=lambda s: print("   " + str(s), flush=True))
        dt = time.time() - t0
        results.append({"video": name, "id": m["id"], "ok": True, "secs": round(dt, 1),
                        "src": m["src_lang"], "langs": m["langs"],
                        "segs": len(m["segments"]), "conf": m.get("asr_confidence")})
        print(f"   DONE in {dt:.0f}s  src={m['src_lang']} segs={len(m['segments'])}", flush=True)
    except Exception as e:
        traceback.print_exc()
        results.append({"video": name, "ok": False, "error": str(e)})
    with open(os.path.join(REPO, "notes", "batch_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
print("\nBATCH_COMPLETE", flush=True)
