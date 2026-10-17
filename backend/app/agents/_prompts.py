from functools import cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


@cache
def load(name: str) -> str:
    return (PROMPT_DIR / f"{name}.txt").read_text(encoding="utf-8")


def fill(template: str, **values) -> str:
    # str.format would choke on literal braces; replace only known placeholders.
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template
