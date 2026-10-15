"""One model, many ids: the canonical form two model ids are compared in.

On AWS several stages share Bedrock, which names one model several ways. Two
guards compare model ids: the harness judge's independence from the drafter
(AN1c) and the anonymisation attack's independence from the rewriter (AN8b).
Both compare canonical forms, so no wrapping of one model passes either guard.
The function moved here from ``harness.judge`` so the runner can use it
without importing the harness; ``harness.judge`` re-exports it.
"""

from __future__ import annotations

import re

#: Bedrock's wrapping around a model name: an optional geographic
#: inference-profile prefix (``eu.``, ``us-gov.``, ``global.``), then the
#: provider (``anthropic.``).  The provider segment holds no hyphen, so a
#: dotted model name such as ``llama-3.3-70b`` is never read as a prefix.
_BEDROCK_PREFIX = re.compile(r"^(?:[a-z]+(?:-[a-z]+)?\.)?[a-z0-9]+\.(?=[a-z])")
#: Qualifiers a provider appends to a model name, one per match.  They are
#: peeled until none is left, so ``-v1:0:200k`` loses ``:200k``, then
#: ``-v1:0``.
_TRAILING_QUALIFIERS = (
    re.compile(r"\[[^\]]*\]$"),  # a context alias: [1m]
    re.compile(r":\d+[km]$"),  # a Bedrock context window: :200k, :1m
    re.compile(r"-v\d+(?::\d+)?$"),  # a Bedrock version: -v1:0, -v2
    re.compile(r":\d+$"),  # a bare Bedrock revision: :0
    re.compile(r"[-@]\d{8}$"),  # a snapshot date: -20251001, @20251001
    re.compile(r"-latest$"),  # a moving alias
)


def canonical_model_id(model_id: str) -> str:
    """Return the model a model id names, without the provider's wrapping.

    On AWS the drafter and the assessor share Bedrock, which names one model
    several ways, and a string comparison would let any of them past the
    independence guard.  This keeps the last path segment (an ARN, or an
    ``anthropic/`` route prefix), strips the inference-profile and provider
    prefixes, then peels :data:`_TRAILING_QUALIFIERS` and lowercases the
    rest.  Two snapshots of one model therefore compare equal, which the
    guard wants.

    An opaque application-inference-profile id names no model, and no string
    rule can resolve it (ticket AN1c).
    """
    canonical = str(model_id).strip().lower().rsplit("/", 1)[-1]
    canonical = _BEDROCK_PREFIX.sub("", canonical, count=1)
    previous = None
    while canonical != previous:
        previous = canonical
        for qualifier in _TRAILING_QUALIFIERS:
            canonical = qualifier.sub("", canonical)
    return canonical
