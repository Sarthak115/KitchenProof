#!/usr/bin/env python3
"""Upload the sample videos so Gemini (gs://) and the browser (/demo/*.mp4) can use them.

  STORAGE_BUCKET=my-proj.firebasestorage.app python scripts/upload_demo_assets.py

Copies frontend/public/demo/*.mp4 (served by Firebase Hosting for playback) to
gs://$STORAGE_BUCKET/demo-assets/ so Gemini on Vertex AI can read them.
"""

import os
import sys
from pathlib import Path

from google.cloud import storage

ROOT = Path(__file__).resolve().parent.parent
FILES = ["messy_kitchen.mp4", "clean_kitchen.mp4"]  # too_perfect reuses clean_kitchen.mp4


def main() -> None:
    bucket_name = os.getenv("STORAGE_BUCKET") or sys.exit("Set STORAGE_BUCKET")
    bucket = storage.Client().bucket(bucket_name)
    for name in FILES:
        src = ROOT / "frontend/public/demo" / name
        if not src.exists():
            print(f"skip {name} (not found in frontend/public/demo/)")
            continue
        bucket.blob(f"demo-assets/{name}").upload_from_filename(str(src), content_type="video/mp4")
        print(f"uploaded {name} -> gs://{bucket_name}/demo-assets/{name}")


if __name__ == "__main__":
    main()
