"""Liveness challenge pool (§6.3). The expected answer is stored server-side only."""

import random

OBJECTS = ["stove", "fridge", "sink", "gas cylinder"]


def make_challenge(rng: random.Random, objects: list[str] | None = None) -> dict:
    """`objects`: the restaurant's own list of things it has (e.g. no gas cylinder in view)."""
    n = rng.randint(1, 5)
    obj = rng.choice([o for o in (objects or []) if o in OBJECTS] or OBJECTS)
    noun = "finger" if n == 1 else "fingers"
    return {"n": n, "object": obj, "prompt": f"Hold up {n} {noun} in front of the {obj}"}


def matches(expected: dict, fingers_counted: int | None, near_object: str | None) -> bool:
    if fingers_counted != expected["n"]:
        return False
    near = (near_object or "").lower()
    want = expected["object"].lower()
    # "gas cylinder" may be reported as "cylinder" or "gas"
    return want in near or any(word in near for word in want.split())
