#!/usr/bin/env python3
"""Phase 0 go/no-go: run the Auditor prompt + schema on a local video and print the JSON.

Usage (from the repo root):
  # AI Studio key (simplest):
  GEMINI_API_KEY=... python scripts/test_auditor.py frontend/public/demo/messy_kitchen.mp4
  # or Vertex AI with a gs:// video:
  GOOGLE_GENAI_USE_VERTEXAI=true GOOGLE_CLOUD_PROJECT=my-proj python scripts/test_auditor.py gs://bucket/demo-assets/messy_kitchen.mp4

Optional second argument: a timeline JSON (default: backend/app/demo/timelines/messy.json).
Pass: the messy video shows raw meat above cooked food (fridge_segregation=fail) and an open
dustbin (dustbins=fail); the clean video mostly passes; unclear checks come back not_verified.
"""

import json
import mimetypes
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import checks as C  # noqa: E402
from app import gemini  # noqa: E402
from app.agents import auditor  # noqa: E402
from app.config import settings  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    video = sys.argv[1]
    timeline_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "backend/app/demo/timelines/messy.json"
    tl = json.loads(timeline_path.read_text())
    if not gemini.available():
        sys.exit("Set GEMINI_API_KEY, or GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT")

    check_ids = [c["checkId"] for c in tl["checks"]]
    timeline = [{**c, "prompt": C.prompt_for(c["checkId"], "4521")} for c in tl["checks"]]
    live = tl["liveness"]
    liveness = {"prompt": f"Hold up {live['n']} fingers in front of the {live['object']}", "offsetSec": live["offsetSec"]}
    mime = tl.get("mime") or mimetypes.guess_type(video)[0] or "video/mp4"

    print(f"Model: {settings.gemini_model} (fallback {settings.gemini_fallback_model})", file=sys.stderr)
    t0 = time.time()
    part = gemini.video_part(video if video.startswith("gs://") else os.path.abspath(video), mime)
    result, model_id = auditor.run(part, check_ids, timeline, liveness, "4521")
    print(f"Done in {time.time() - t0:.1f}s on {model_id}", file=sys.stderr)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\nSummary:", file=sys.stderr)
    for f in result["findings"]:
        print(f"  {f['status']:<13} {f['checkId']:<20} {f['timestamp']}  conf {f['confidence']:.2f}  {f['reason']}", file=sys.stderr)
    lv = result["liveness"]
    print(f"  liveness: {lv['fingersCounted']} fingers near {lv['nearObject']} at {lv['timestamp']} (expected {live['n']} / {live['object']})", file=sys.stderr)


if __name__ == "__main__":
    main()
