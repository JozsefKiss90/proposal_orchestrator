"""Tests for runner.benchmark.context — context variable management."""

from runner.benchmark.context import get_ledger, set_ledger
from runner.benchmark.ledger import BenchmarkLedger


class TestGetSetLedger:
    """Test get_ledger / set_ledger context variable."""

    def test_default_is_none(self):
        """get_ledger() returns None by default."""
        # Ensure clean state
        set_ledger(None)
        assert get_ledger() is None

    def test_set_and_get(self):
        """set_ledger() sets a ledger retrievable by get_ledger()."""
        ledger = BenchmarkLedger()
        try:
            set_ledger(ledger)
            assert get_ledger() is ledger
        finally:
            set_ledger(None)

    def test_clear(self):
        """set_ledger(None) clears the active ledger."""
        ledger = BenchmarkLedger()
        set_ledger(ledger)
        set_ledger(None)
        assert get_ledger() is None

    def test_replace(self):
        """set_ledger() replaces the previous ledger."""
        ledger1 = BenchmarkLedger()
        ledger2 = BenchmarkLedger()
        try:
            set_ledger(ledger1)
            assert get_ledger() is ledger1
            set_ledger(ledger2)
            assert get_ledger() is ledger2
        finally:
            set_ledger(None)
