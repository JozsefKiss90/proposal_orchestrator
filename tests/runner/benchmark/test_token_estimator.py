"""Tests for runner.benchmark.token_estimator — character-to-token estimation."""

from runner.benchmark.token_estimator import CHAR_TO_TOKEN_RATIOS, estimate_tokens


class TestEstimateTokens:
    """Test estimate_tokens() function."""

    def test_claude_model(self):
        """Known Claude model uses correct ratio."""
        result = estimate_tokens(3500, "claude-sonnet-4-6")
        # 3500 / 3.5 = 1000
        assert result == 1000

    def test_claude_opus(self):
        result = estimate_tokens(7000, "claude-opus-4-6")
        assert result == 2000

    def test_unknown_model_uses_default(self):
        """Unknown model falls back to _default ratio."""
        result = estimate_tokens(3500, "some-unknown-model")
        assert result == 1000  # 3500 / 3.5 = 1000

    def test_zero_chars(self):
        """Zero characters returns 0."""
        assert estimate_tokens(0, "claude-sonnet-4-6") == 0

    def test_negative_chars(self):
        """Negative characters returns 0."""
        assert estimate_tokens(-100, "claude-sonnet-4-6") == 0

    def test_small_positive(self):
        """Very small positive char count returns at least 1."""
        assert estimate_tokens(1, "claude-sonnet-4-6") == 1

    def test_float_chars(self):
        """Float char count is handled."""
        result = estimate_tokens(7.0, "claude-sonnet-4-6")
        assert result == 2  # 7.0 / 3.5 = 2.0

    def test_invalid_type_returns_zero(self):
        """Non-numeric input returns 0."""
        assert estimate_tokens("abc", "claude-sonnet-4-6") == 0  # type: ignore[arg-type]
        assert estimate_tokens(None, "claude-sonnet-4-6") == 0  # type: ignore[arg-type]

    def test_large_count(self):
        """Large character counts produce reasonable estimates."""
        result = estimate_tokens(100_000, "claude-sonnet-4-6")
        assert result == 28571  # 100000 / 3.5

    def test_gpt4o_ratio(self):
        """GPT-4o uses its own ratio."""
        result = estimate_tokens(3800, "gpt-4o")
        assert result == 1000  # 3800 / 3.8

    def test_default_ratio_exists(self):
        """_default key exists in CHAR_TO_TOKEN_RATIOS."""
        assert "_default" in CHAR_TO_TOKEN_RATIOS
        assert CHAR_TO_TOKEN_RATIOS["_default"] > 0
