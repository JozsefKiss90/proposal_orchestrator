"""Production-mode security enforcement tests (Phase 1).

Verifies that ``ORCHESTRATOR_PRODUCTION_MODE=true`` rejects non-production
backends, enforces production-suitable presets, and that development mode
preserves full backend flexibility.

Also verifies that semantic dispatch respects the configured backend.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from runner.transport.config import (
    PRODUCTION_BACKENDS,
    VALID_BACKENDS,
    is_production_mode,
    resolve_provider_config,
    resolve_provider_config_from_preset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

#: A Region value for tests that need AWS_REGION set. Deliberately not a real
#: Region: no test here fixes which Region production uses (R9e criterion 2).
_REGION = "zz-test-1"


def _env(**overrides: str) -> dict[str, str]:
    """Build a clean env dict with only the specified overrides."""
    # Start from a minimal env (no transport vars, no production mode).
    base: dict[str, str] = {}
    # Remove all ORCHESTRATOR_* and AWS_* keys from inheritance.
    for key in list(os.environ):
        if key.startswith("ORCHESTRATOR_") or key.startswith("AWS_"):
            pass  # excluded
        else:
            base[key] = os.environ[key]
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestProductionModeEnforcement
# ---------------------------------------------------------------------------


class TestProductionModeEnforcement:
    """Verify ORCHESTRATOR_PRODUCTION_MODE=true enforces backend restrictions."""

    def test_production_mode_rejects_claude_cli_default(self):
        """Default backend (claude_cli) is rejected in production mode."""
        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true")
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not production-suitable"):
                resolve_provider_config()

    def test_production_mode_rejects_claude_cli_explicit(self):
        """Explicitly setting claude_cli is rejected in production mode."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="claude_cli",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not production-suitable"):
                resolve_provider_config()

    def test_production_mode_rejects_together_ai(self):
        """together_ai backend is rejected in production mode."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="together_ai",
            ORCHESTRATOR_TRANSPORT_API_KEY="fake-key",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not production-suitable"):
                resolve_provider_config()

    def test_production_mode_rejects_ollama(self):
        """ollama backend is rejected in production mode."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="ollama",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not production-suitable"):
                resolve_provider_config()

    def test_production_mode_rejects_openai_compatible(self):
        """generic openai_compatible backend is rejected in production mode."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="openai_compatible",
            ORCHESTRATOR_TRANSPORT_ENDPOINT="https://example.com/v1",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not production-suitable"):
                resolve_provider_config()

    def test_production_mode_accepts_bedrock_converse(self):
        """bedrock_converse backend is accepted in production mode.

        R9 (point 15): AWS_REGION added; production mode now requires it.
        """
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
            AWS_REGION=_REGION,
        )
        with mock.patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()
            assert config.backend_name == "bedrock_converse"
            assert config.region == _REGION

    def test_production_mode_rejects_bedrock_mantle(self):
        """bedrock (mantle) backend is rejected in production mode (F6, R9).

        Replaces test_production_mode_accepts_bedrock_mantle: the mantle host
        has no VPC endpoint, so the backend left PRODUCTION_BACKENDS.
        """
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock",
            ORCHESTRATOR_TRANSPORT_API_KEY="fake-key",
            ORCHESTRATOR_TRANSPORT_MODEL="anthropic.claude-sonnet-4-20250514-v1:0",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not production-suitable"):
                resolve_provider_config()

    def test_production_mode_rejects_non_production_preset(self):
        """Non-production preset (OLLAMA_LOCAL) is rejected in production mode."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_PRESET="OLLAMA_LOCAL",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not production-suitable"):
                resolve_provider_config()

    def test_production_mode_rejects_claude_reference_preset(self):
        """CLAUDE_REFERENCE preset is rejected in production mode."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_PRESET="CLAUDE_REFERENCE",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not production-suitable"):
                resolve_provider_config()

    def test_production_mode_accepts_bedrock_converse_us_preset(self):
        """BEDROCK_CONVERSE_US preset is accepted in production mode.

        R9 (point 15): AWS_REGION added; production mode now requires it.
        """
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_PRESET="BEDROCK_CONVERSE_US",
            AWS_REGION=_REGION,
        )
        with mock.patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()
            assert config.backend_name == "bedrock_converse"
            assert config.preset_name == "BEDROCK_CONVERSE_US"
            assert config.region == _REGION

    def test_production_mode_rejects_bedrock_eu_production_preset(self):
        """BEDROCK_EU_PRODUCTION preset is rejected in production mode (F6, R9).

        Replaces test_production_mode_accepts_bedrock_eu_production_preset.
        """
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_PRESET="BEDROCK_EU_PRODUCTION",
            ORCHESTRATOR_TRANSPORT_API_KEY="fake-key",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not production-suitable"):
                resolve_provider_config()


class TestDevelopmentModePreservation:
    """Verify development mode (ORCHESTRATOR_PRODUCTION_MODE unset) is unchanged."""

    def test_development_mode_allows_claude_cli_default(self):
        """When production mode is unset, default claude_cli is allowed."""
        env = _env()  # no ORCHESTRATOR_PRODUCTION_MODE
        with mock.patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()
            assert config.backend_name == "claude_cli"

    def test_development_mode_allows_ollama(self):
        """When production mode is unset, ollama is allowed."""
        env = _env(ORCHESTRATOR_TRANSPORT_BACKEND="ollama")
        with mock.patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()
            assert config.backend_name == "ollama"

    def test_development_mode_allows_together_ai(self):
        """When production mode is unset, together_ai is allowed."""
        env = _env(
            ORCHESTRATOR_TRANSPORT_BACKEND="together_ai",
            ORCHESTRATOR_TRANSPORT_API_KEY="fake-key",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()
            assert config.backend_name == "together_ai"

    def test_production_mode_false_allows_all(self):
        """Explicit ORCHESTRATOR_PRODUCTION_MODE=false allows all backends."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="false",
            ORCHESTRATOR_TRANSPORT_BACKEND="claude_cli",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()
            assert config.backend_name == "claude_cli"

    def test_production_mode_empty_allows_all(self):
        """Empty ORCHESTRATOR_PRODUCTION_MODE allows all backends."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="",
            ORCHESTRATOR_TRANSPORT_BACKEND="claude_cli",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()
            assert config.backend_name == "claude_cli"


class TestIsProductionMode:
    """Verify is_production_mode() helper."""

    def test_true_when_set(self):
        with mock.patch.dict(os.environ, {"ORCHESTRATOR_PRODUCTION_MODE": "true"}):
            assert is_production_mode() is True

    def test_true_case_insensitive(self):
        with mock.patch.dict(os.environ, {"ORCHESTRATOR_PRODUCTION_MODE": "True"}):
            assert is_production_mode() is True

    def test_false_when_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_PRODUCTION_MODE"}
        with mock.patch.dict(os.environ, env, clear=True):
            assert is_production_mode() is False

    def test_false_when_false(self):
        with mock.patch.dict(os.environ, {"ORCHESTRATOR_PRODUCTION_MODE": "false"}):
            assert is_production_mode() is False

    def test_false_when_empty(self):
        with mock.patch.dict(os.environ, {"ORCHESTRATOR_PRODUCTION_MODE": ""}):
            assert is_production_mode() is False


class TestProductionBackendsConstant:
    """Verify PRODUCTION_BACKENDS is correctly defined."""

    def test_production_backends_subset_of_valid(self):
        assert PRODUCTION_BACKENDS.issubset(VALID_BACKENDS)

    def test_bedrock_converse_is_production(self):
        assert "bedrock_converse" in PRODUCTION_BACKENDS

    def test_bedrock_is_not_production(self):
        """F6 (R9): replaces test_bedrock_is_production."""
        assert "bedrock" not in PRODUCTION_BACKENDS

    def test_bedrock_converse_is_the_only_production_backend(self):
        assert PRODUCTION_BACKENDS == frozenset({"bedrock_converse"})

    def test_claude_cli_not_production(self):
        assert "claude_cli" not in PRODUCTION_BACKENDS

    def test_together_ai_not_production(self):
        assert "together_ai" not in PRODUCTION_BACKENDS

    def test_ollama_not_production(self):
        assert "ollama" not in PRODUCTION_BACKENDS

    def test_openai_compatible_not_production(self):
        assert "openai_compatible" not in PRODUCTION_BACKENDS


class TestSemanticDispatchBackendRouting:
    """Verify semantic dispatch respects configured backend."""

    def test_semantic_dispatch_uses_bedrock_when_configured(self):
        """When backend is bedrock_converse, semantic dispatch resolves it."""
        from runner.semantic_dispatch import (
            _resolve_semantic_backend,
            _semantic_provider_resolved,
        )
        import runner.semantic_dispatch as sd_module

        # Reset the cache
        sd_module._semantic_provider_cache = None
        sd_module._semantic_provider_resolved = False

        env = _env(
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        try:
            with mock.patch.dict(os.environ, env, clear=True):
                config = _resolve_semantic_backend()
                assert config.backend_name == "bedrock_converse"
        finally:
            # Reset cache to avoid polluting other tests
            sd_module._semantic_provider_cache = None
            sd_module._semantic_provider_resolved = False

    def test_semantic_dispatch_rejects_claude_cli_in_production(self):
        """In production mode, semantic dispatch rejects claude_cli."""
        import runner.semantic_dispatch as sd_module
        from runner.semantic_dispatch import _resolve_semantic_backend

        sd_module._semantic_provider_cache = None
        sd_module._semantic_provider_resolved = False

        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true")
        try:
            with mock.patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValueError, match="not production-suitable"):
                    _resolve_semantic_backend()
        finally:
            sd_module._semantic_provider_cache = None
            sd_module._semantic_provider_resolved = False

    def test_semantic_dispatch_defaults_to_claude_cli_in_dev(self):
        """In development mode, semantic dispatch defaults to claude_cli."""
        import runner.semantic_dispatch as sd_module

        sd_module._semantic_provider_cache = None
        sd_module._semantic_provider_resolved = False

        env = _env()
        try:
            with mock.patch.dict(os.environ, env, clear=True):
                config = sd_module._resolve_semantic_backend()
                assert config.backend_name == "claude_cli"
        finally:
            sd_module._semantic_provider_cache = None
            sd_module._semantic_provider_resolved = False


class TestFailClosedBehavior:
    """Verify fail-closed behavior: production mode with no backend configured."""

    def test_no_backend_no_preset_fails_in_production(self):
        """Production mode with no explicit backend selection fails closed."""
        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true")
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError):
                resolve_provider_config()

    def test_invalid_backend_fails(self):
        """Invalid backend name fails regardless of production mode."""
        env = _env(ORCHESTRATOR_TRANSPORT_BACKEND="nonexistent")
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="Invalid backend"):
                resolve_provider_config()


class TestStartupBackendLogging:
    """Verify __main__.py startup backend logging."""

    #: The run id the startup check below is given. ``main`` creates the run
    #: directory before the transport config fails, so the directory outlives
    #: the test unless it is removed.
    RUN_ID = "test-00000000-0000-0000-0000-000000000000"

    @pytest.fixture(autouse=True)
    def _no_leaked_run_record(self):
        """Remove the run directory the startup path creates, if it created it.

        Left behind, it changes what *other* modules measure. Three checks in
        ``tests/test_demo_change_scenarios.py`` and
        ``tests/test_preserve_run_manifests.py`` skip when ``.claude/runs`` is
        absent, as §9.2 runtime state is on a fresh checkout, and fail when a
        directory is there without the manifest they read. A later whole-suite
        run in the same tree then reports three failures this test caused,
        which is how the acceptance lane found it.

        Conditional on purpose: a directory that was already there is a
        developer's run state, not this test's debris, and removing it would
        trade one side effect for another.
        """
        import shutil

        from runner.paths import find_repo_root

        record = find_repo_root() / ".claude" / "runs" / self.RUN_ID
        existed = record.exists()
        yield
        if not existed and record.is_dir():
            shutil.rmtree(record, ignore_errors=True)

    def test_startup_returns_3_on_production_config_error(self):
        """DAG startup returns exit code 3 when production config fails."""
        from runner.__main__ import main

        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true")
        with mock.patch.dict(os.environ, env, clear=True):
            # Provide required args but let transport config fail
            exit_code = main(["--run-id", self.RUN_ID])
            assert exit_code == 3

    def test_startup_returns_3_when_production_has_no_aws_region(self, capsys):
        """R9 exit condition 1: the runner stops before any phase without AWS_REGION."""
        from runner.__main__ import main

        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            exit_code = main(["--run-id", self.RUN_ID])
        assert exit_code == 3
        out, err = capsys.readouterr()
        assert "AWS_REGION is not set" in out + err


# ---------------------------------------------------------------------------
# R9: production mode refuses to run without AWS_REGION (F4)
# ---------------------------------------------------------------------------


class TestProductionRequiresAwsRegion:
    """Exit condition 1 of ticket R9: a call can never silently go to a default Region.

    Decision record ``aws-redeployment-r9-runtime-config_2026-10-27``.
    """

    _CONVERSE = {
        "explicit backend": dict(
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        ),
        "preset": dict(ORCHESTRATOR_TRANSPORT_PRESET="BEDROCK_CONVERSE_US"),
    }

    @pytest.mark.parametrize("path", sorted(_CONVERSE))
    def test_missing_aws_region_is_refused_at_resolution(self, path):
        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true", **self._CONVERSE[path])
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="AWS_REGION is not set"):
                resolve_provider_config()

    @pytest.mark.parametrize("path", sorted(_CONVERSE))
    @pytest.mark.parametrize("value", ["", "   "])
    def test_empty_aws_region_is_refused(self, path, value):
        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true", AWS_REGION=value, **self._CONVERSE[path])
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="AWS_REGION is not set"):
                resolve_provider_config()

    @pytest.mark.parametrize("path", sorted(_CONVERSE))
    def test_aws_default_region_alone_is_refused(self, path):
        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true", AWS_DEFAULT_REGION=_REGION,
                   **self._CONVERSE[path])
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="AWS_DEFAULT_REGION alone does not count"):
                resolve_provider_config()

    @pytest.mark.parametrize("path", sorted(_CONVERSE))
    def test_aws_region_is_carried_into_the_config(self, path):
        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true", AWS_REGION=_REGION, **self._CONVERSE[path])
        with mock.patch.dict(os.environ, env, clear=True):
            assert resolve_provider_config().region == _REGION

    def _config(self, region=None):
        from runner.transport.capabilities import CAPABILITIES_REGISTRY
        from runner.transport.config import ProviderConfig

        return ProviderConfig(
            backend_name="bedrock_converse", base_url=None, api_key_set=False,
            model="us.anthropic.claude-sonnet-4-6",
            capabilities=CAPABILITIES_REGISTRY["bedrock_converse"], region=region,
        )

    @pytest.mark.parametrize("carried", [None, "zz-carried-2"])
    def test_missing_aws_region_is_refused_at_build(self, carried):
        """build_converse_backend refuses too, whatever the config carries."""
        from runner.transport.config import build_converse_backend

        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true")
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("runner.transport.bedrock_converse.BedrockConverseBackend") as backend:
            with pytest.raises(ValueError, match="AWS_REGION is not set"):
                build_converse_backend(self._config(carried))
            backend.assert_not_called()

    def test_build_passes_aws_region_to_the_backend(self):
        from runner.transport.config import build_converse_backend

        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true", AWS_REGION=_REGION)
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("runner.transport.bedrock_converse.BedrockConverseBackend") as backend:
            build_converse_backend(self._config("zz-carried-2"))
        assert backend.call_args.kwargs["region_name"] == _REGION

    def test_outside_production_build_falls_back_to_the_carried_region(self):
        from runner.transport.config import build_converse_backend

        env = _env()
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("runner.transport.bedrock_converse.BedrockConverseBackend") as backend:
            build_converse_backend(self._config("zz-carried-2"))
        assert backend.call_args.kwargs["region_name"] == "zz-carried-2"

    def test_the_backend_has_no_default_region(self):
        import inspect

        from runner.transport.bedrock_converse import BedrockConverseBackend

        parameter = inspect.signature(BedrockConverseBackend.__init__).parameters["region_name"]
        assert parameter.default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# R9: F6 holds on the preset path too
# ---------------------------------------------------------------------------


class TestF6OnBothPaths:
    """F6 is decided in code (decision record ``aws-redeployment-r9-runtime-config_2026-10-27``)."""

    def test_bedrock_eu_production_is_not_production_suitable(self):
        from runner.transport.config import BEDROCK_EU_PRODUCTION

        assert BEDROCK_EU_PRODUCTION.production_suitable is False
        assert any("F6" in note for note in BEDROCK_EU_PRODUCTION.notes)

    def test_a_preset_flagged_suitable_cannot_carry_a_non_production_backend(self):
        """The preset path checks PRODUCTION_BACKENDS, not only the flag."""
        import dataclasses

        from runner.transport import config as cfg

        rogue = dataclasses.replace(cfg.BEDROCK_EU_DEVELOPMENT, name="ZZ_ROGUE",
                                    production_suitable=True)
        env = _env(ORCHESTRATOR_PRODUCTION_MODE="true", ORCHESTRATOR_TRANSPORT_PRESET="ZZ_ROGUE",
                   ORCHESTRATOR_TRANSPORT_API_KEY="fake-key")
        with mock.patch.dict(cfg.PRESET_REGISTRY, {"ZZ_ROGUE": rogue}), \
                mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="backend 'bedrock' is not production-suitable"):
                resolve_provider_config()

    def test_every_production_suitable_preset_uses_a_production_backend(self):
        from runner.transport.config import PRESET_REGISTRY

        for preset in PRESET_REGISTRY.values():
            if preset.production_suitable:
                assert preset.backend_name in PRODUCTION_BACKENDS, preset.name
