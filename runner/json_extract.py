"""
Shared JSON-object extraction from an LLM response (house helper).

An LLM asked for a JSON object may return it bare, inside a ```json code fence,
or wrapped in prose.  Two callers need to recover the object without guessing:

  * the semantic-predicate dispatcher (:mod:`runner.semantic_dispatch`), and
  * the out-of-band harness judge (``harness/judge.py``).

Both previously carried a byte-identical three-step extractor; this module
consolidates them into one public function — the same de-duplication the
``atomic_write`` helper performs for the canonical writer.  It is a pure
string/JSON transform: no I/O, no network, no domain reasoning, and it never
repairs — an unparseable response yields ``None`` and the caller decides what a
missing object means (both callers treat it as a failure, never a fabricated
result).
"""

from __future__ import annotations

import json
import re
from typing import Optional

__all__ = ["extract_first_json_object"]

#: Matches a ```json … ``` (or bare ``` … ```) fenced object, non-greedy.
_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
#: Matches the first ``{ … }`` span anywhere in the text, greedy.
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_first_json_object(text: str) -> Optional[dict]:
    """Return the first JSON *object* in *text*, or ``None`` if there is none.

    Tries, in order: (1) parse the whole (stripped) string — but only accept a
    top-level ``dict``, never a nested object pulled out of a top-level array;
    (2) a fenced ``{...}`` block; (3) the first ``{...}`` span anywhere.  A
    ``None`` or empty input yields ``None``.  Never raises on malformed input and
    never repairs it.
    """
    stripped = (text or "").strip()
    if not stripped:
        return None

    # 1. Whole response is JSON.  A non-dict top level (e.g. a list) returns
    #    None rather than digging a dict out of it.
    try:
        data = json.loads(stripped)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    # 2. JSON inside a markdown code fence.
    fence = _FENCE_RE.search(stripped)
    if fence:
        try:
            data = json.loads(fence.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 3. Any JSON object embedded in surrounding prose.
    obj = _OBJECT_RE.search(stripped)
    if obj:
        try:
            data = json.loads(obj.group())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None
