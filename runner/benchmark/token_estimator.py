"""
Token estimation from character counts.

Uses model-specific character-to-token ratios.  Estimates are
approximate (+-15-25%) and sufficient for cost comparison and trend
analysis, not for exact billing reconciliation.
"""

from __future__ import annotations

CHAR_TO_TOKEN_RATIOS: dict[str, float] = {
    # Claude models
    "claude-sonnet-4-6": 3.5,
    "claude-opus-4-6": 3.5,
    "claude-haiku-4-5": 3.5,
    # OpenAI-compatible models (for future projection)
    "gpt-4o": 3.8,
    "gpt-4o-mini": 3.8,
    # Open-weight models (for future projection)
    "llama-3.1-70b": 3.6,
    "llama-3.1-405b": 3.6,
    "deepseek-v3": 3.4,
    # Default fallback
    "_default": 3.5,
}


def estimate_tokens(char_count: int, model: str) -> int:
    """Estimate token count from character count and model.

    Returns at least 1 for any positive char_count.
    Returns 0 for zero or negative char_count.
    """
    if not isinstance(char_count, (int, float)) or char_count <= 0:
        return 0
    ratio = CHAR_TO_TOKEN_RATIOS.get(model, CHAR_TO_TOKEN_RATIOS["_default"])
    if ratio <= 0:
        return 0
    return max(1, int(char_count / ratio))
