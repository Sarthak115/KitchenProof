#!/usr/bin/env python3
"""(Re)seed Firestore with the fictional demo data.

  GOOGLE_CLOUD_PROJECT=my-proj python scripts/seed_firestore.py
(or call POST /api/demo/reset on the deployed API with the X-Admin-Secret header)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("DATASTORE", "firestore")

from app.demo.seed import seed  # noqa: E402
from app.firestore import get_store  # noqa: E402

if __name__ == "__main__":
    print(seed(get_store()))
