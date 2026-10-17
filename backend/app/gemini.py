"""Thin wrapper around the Google Gen AI SDK (Gemini on Vertex AI, or AI Studio for local dev).

Video references:
  gs://bucket/path      -> passed by URI (Vertex AI reads it directly; avoids request-size limits)
  /local/path.mp4       -> uploaded via the Gemini Files API (AI Studio) or inlined (Vertex, small files)
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import time
from typing import Any

from .config import settings

log = logging.getLogger(__name__)

_client = None


class GeminiUnavailable(RuntimeError):
    pass


def available() -> bool:
    if not settings.gemini_enabled:
        return False
    return settings.use_vertex or bool(settings.gemini_api_key)


def client():
    global _client
    if _client is None:
        if not available():
            raise GeminiUnavailable("Gemini is not configured (set GOOGLE_GENAI_USE_VERTEXAI or GEMINI_API_KEY)")
        from google import genai

        if settings.use_vertex:
            _client = genai.Client(
                vertexai=True, project=settings.gcp_project, location=settings.gcp_location
            )
        else:
            _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def video_part(ref: str, mime_type: str):
    from google.genai import types

    if ref.startswith("gs://"):
        if not settings.use_vertex:
            raise GeminiUnavailable("gs:// videos need Vertex AI (GOOGLE_GENAI_USE_VERTEXAI=true)")
        return types.Part.from_uri(file_uri=ref, mime_type=mime_type)

    if not os.path.exists(ref):
        raise FileNotFoundError(ref)
    mime_type = mime_type or mimetypes.guess_type(ref)[0] or "video/mp4"
    if settings.use_vertex:
        with open(ref, "rb") as fh:
            return types.Part.from_bytes(data=fh.read(), mime_type=mime_type)

    # AI Studio: upload through the Files API and wait until it is processed
    c = client()
    uploaded = c.files.upload(file=ref, config={"mime_type": mime_type})
    deadline = time.time() + 180
    while getattr(uploaded.state, "name", str(uploaded.state)) == "PROCESSING":
        if time.time() > deadline:
            raise TimeoutError("Gemini file processing timed out")
        time.sleep(2)
        uploaded = c.files.get(name=uploaded.name)
    if getattr(uploaded.state, "name", str(uploaded.state)) == "FAILED":
        raise RuntimeError("Gemini could not process the video")
    return types.Part.from_uri(file_uri=uploaded.uri, mime_type=mime_type)


def generate_json(prompt: str, schema: Any, video=None, model: str | None = None) -> tuple[dict, str]:
    """Call Gemini with structured output. Returns (parsed JSON, model id used).

    Tries GEMINI_MODEL first, then GEMINI_FALLBACK_MODEL.
    """
    from google.genai import types

    contents: list = [video, prompt] if video is not None else [prompt]
    config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=schema,
    )
    models = [model or settings.gemini_model]
    if settings.gemini_fallback_model not in models:
        models.append(settings.gemini_fallback_model)

    last_err: Exception | None = None
    for model_id in models:
        try:
            resp = client().models.generate_content(model=model_id, contents=contents, config=config)
            return json.loads(resp.text), model_id
        except Exception as err:  # noqa: BLE001 - try the fallback model, then surface the error
            log.warning("Gemini call failed on %s: %s", model_id, err)
            last_err = err
    raise RuntimeError(f"Gemini failed: {last_err}") from last_err
