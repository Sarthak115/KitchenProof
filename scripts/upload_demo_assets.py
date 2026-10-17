#!/usr/bin/env python3
"""Upload the sample videos so Gemini (gs://) and the browser (/demo/*.mp4) can use them.

  STORAGE_BUCKET=my-proj.firebasestorage.app python scripts/upload_demo_assets.py

Copies demo-assets/*.mp4 to gs://$STORAGE_BUCKET/demo-assets/ and to frontend/public/demo/.
"""

import os
import shutil
import sys
from pathlib import Path

from google.cloud import storage

ROOT = Path(__file__).resolve().parent.parent
FILES = ["messy_kitchen.mp4", "clean_kitchen.mp4", "too_perfect_kitchen.mp4"]


def main() -> None:
    bucket_name = os.getenv("STORAGE_BUCKET") or sys.exit("Set STORAGE_BUCKET")
    bucket = storage.Client().bucket(bucket_name)
    public_dir = ROOT / "frontend/public/demo"
    for name in FILES:
        src = ROOT / "demo-assets" / name
        if not src.exists():
            print(f"skip {name} (not found in demo-assets/)")
            continue
        bucket.blob(f"demo-assets/{name}").upload_from_filename(str(src), content_type="video/mp4")
        shutil.copy(src, public_dir / name)
        print(f"uploaded {name} -> gs://{bucket_name}/demo-assets/{name} and frontend/public/demo/")


if __name__ == "__main__":
    main()
