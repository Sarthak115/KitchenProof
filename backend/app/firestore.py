"""Tiny document store used by the API.

`FirestoreStore` talks to Cloud Firestore (production). `MemoryStore` keeps everything in a
dict and is used for local development without GCP and for tests. Both expose the same
minimal interface; collection paths may be nested ("audits/{id}/findings").
"""

from __future__ import annotations

import copy
import threading
import uuid
from typing import Any, Iterable

from .config import settings

Filter = tuple[str, str, Any]  # (field, "==", value)


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class Store:
    def get(self, path: str, doc_id: str) -> dict | None: ...
    def set(self, path: str, doc_id: str, data: dict) -> None: ...
    def update(self, path: str, doc_id: str, data: dict) -> None: ...
    def delete(self, path: str, doc_id: str) -> None: ...
    def query(self, path: str, filters: Iterable[Filter] = ()) -> list[dict]: ...

    def add(self, path: str, data: dict, prefix: str = "") -> str:
        doc_id = new_id(prefix)
        self.set(path, doc_id, data)
        return doc_id

    def wipe(self, paths: Iterable[str]) -> None:
        for path in paths:
            for doc in self.query(path):
                self.delete(path, doc["id"])


class MemoryStore(Store):
    def __init__(self) -> None:
        self._data: dict[str, dict[str, dict]] = {}
        self._lock = threading.RLock()

    def get(self, path, doc_id):
        with self._lock:
            doc = self._data.get(path, {}).get(doc_id)
            return {**copy.deepcopy(doc), "id": doc_id} if doc is not None else None

    def set(self, path, doc_id, data):
        with self._lock:
            self._data.setdefault(path, {})[doc_id] = copy.deepcopy(
                {k: v for k, v in data.items() if k != "id"}
            )

    def update(self, path, doc_id, data):
        with self._lock:
            doc = self._data.setdefault(path, {}).setdefault(doc_id, {})
            doc.update(copy.deepcopy({k: v for k, v in data.items() if k != "id"}))

    def delete(self, path, doc_id):
        with self._lock:
            self._data.get(path, {}).pop(doc_id, None)
            # drop subcollections too
            prefix = f"{path}/{doc_id}/"
            for key in [k for k in self._data if k.startswith(prefix)]:
                del self._data[key]

    def query(self, path, filters=()):
        filters = list(filters)
        with self._lock:
            out = []
            for doc_id, doc in self._data.get(path, {}).items():
                if all(_match(doc, f) for f in filters):
                    out.append({**copy.deepcopy(doc), "id": doc_id})
            return out


def _match(doc: dict, f: Filter) -> bool:
    field, op, value = f
    if op != "==":
        raise ValueError(f"unsupported op {op}")
    return doc.get(field) == value


class FirestoreStore(Store):
    def __init__(self) -> None:
        from google.cloud import firestore

        self._fs = firestore
        self._db = firestore.Client(project=settings.gcp_project)

    def _col(self, path):
        return self._db.collection(path)

    def get(self, path, doc_id):
        snap = self._col(path).document(doc_id).get()
        return {**_plain(snap.to_dict()), "id": snap.id} if snap.exists else None

    def set(self, path, doc_id, data):
        self._col(path).document(doc_id).set({k: v for k, v in data.items() if k != "id"})

    def update(self, path, doc_id, data):
        self._col(path).document(doc_id).set(
            {k: v for k, v in data.items() if k != "id"}, merge=True
        )

    def delete(self, path, doc_id):
        ref = self._col(path).document(doc_id)
        for sub in ref.collections():
            for snap in sub.stream():
                snap.reference.delete()
        ref.delete()

    def query(self, path, filters=()):
        from google.cloud.firestore_v1.base_query import FieldFilter

        q = self._col(path)
        for field, op, value in filters:
            q = q.where(filter=FieldFilter(field, op, value))
        return [{**_plain(s.to_dict()), "id": s.id} for s in q.stream()]


def _plain(value):
    """Convert Firestore DatetimeWithNanoseconds into plain aware datetimes."""
    from datetime import datetime

    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, datetime):
        return datetime.fromtimestamp(value.timestamp(), tz=value.tzinfo)
    return value


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = MemoryStore() if settings.datastore == "memory" else FirestoreStore()
    return _store


def set_store(store: Store) -> None:
    global _store
    _store = store
