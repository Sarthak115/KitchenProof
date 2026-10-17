import os

os.environ["DATASTORE"] = "memory"
os.environ["GEMINI_ENABLED"] = "false"
os.environ["DEMO_MODE"] = "true"
os.environ.pop("ADMIN_SECRET", None)

import pytest  # noqa: E402

from app.firestore import MemoryStore, set_store  # noqa: E402


@pytest.fixture()
def store():
    s = MemoryStore()
    set_store(s)
    return s
