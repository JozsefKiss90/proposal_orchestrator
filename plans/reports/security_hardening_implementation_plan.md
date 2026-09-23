# Security Hardening Implementation Plan

## Proposal Orchestrator — Phased Production-Readiness Roadmap

**Date:** 2026-05-28
**Baseline:** `security_compliance_brief.md` (2026-05-28 audit)
**Target:** Institutional deployment on AWS Bedrock Converse API
**Branch:** `benchmark_engine` (active development)
**Status:** Pre-production hardening — migration validation in progress

---

## 1. Executive Summary

This document converts the findings from `security_compliance_brief.md` into a phased implementation roadmap for hardening the Proposal Orchestrator to institutional production-readiness on AWS Bedrock Converse API.

The hardening program is structured in four phases executed sequentially, each starting immediately after the previous one completes:

| Phase | Name | Scope | Execution Model |
|-------|------|-------|-----------------|
| **Phase 0** | Immediate hygiene | `.gitignore`, credential rotation, zero-code-change safeguards | Immediate. Start now. |
| **Phase 1** | Transport lockdown | Production backend enforcement, semantic dispatch routing, fail-closed defaults | Starts immediately after Phase 0. |
| **Phase 2** | Infrastructure and compliance | CI/CD pipeline, pre-commit hooks, path tests (repository-side); AWS VPC, IAM, CloudTrail, GDPR DPA (externally-dependent) | Repository-side items start immediately after Phase 1. AWS/legal items are externally-dependent and execute in parallel whenever the responsible party is available. |
| **Phase 3** | Production hardening | Environment-scoped persistence policy, diagnostic sanitization, deployment host lockdown | Blocked on Phase 3 gate prerequisites (Section 3.2), not on Phase 2 completion. |

**Critical constraint:** The Bedrock migration, Phase 1-8 orchestration validation, and benchmark equivalence testing are ongoing. All hardening changes must preserve the current debugging, diagnostic, and benchmark observability infrastructure. Diagnostic persistence to disk (Section 12.2 of the compliance brief) is **temporarily accepted** for development and migration-validation purposes. Production hardening of persistence behavior is deferred to Phase 3.

**Approved production inference backend:** AWS Bedrock Converse API (`bedrock_converse`) via boto3 with IAM credentials. All other backends (`claude_cli`, `bedrock` mantle, `together_ai`, `ollama`, `openai_compatible`) are development/testing only and must be blocked in production mode.

---

## 2. Security Hardening Strategy

### 2.1 Guiding Principles

1. **Fail-closed over fail-open.** Production mode must refuse to operate when security invariants are not met. A clear error message is always preferable to silent degradation.

2. **Environment-scoped behavior.** Security controls must distinguish between development, staging, and production environments via the `ORCHESTRATOR_PRODUCTION_MODE` environment variable. Development retains full observability; production enforces data-egress prevention.

3. **Non-breaking layering.** Each hardening phase adds enforcement without removing capability. Development-mode behavior remains unchanged unless explicitly overridden. The migration validation workflow must not be interrupted.

4. **Defense in depth.** Backend enforcement at the configuration layer is the primary control. `.gitignore` expansion, CI/CD checks, IAM scoping, and VPC restrictions are defense-in-depth layers that catch failures in the primary control.

5. **Verifiable before deployable.** Every hardening change must have an associated test. No change is considered complete until its test passes in CI.

### 2.2 Environment Classification

| Environment | `ORCHESTRATOR_PRODUCTION_MODE` | Backend Restriction | Diagnostic Persistence | Credential Source |
|-------------|-------------------------------|--------------------|-----------------------|-------------------|
| **Development** | unset or `false` | None (all backends allowed) | Full (current behavior preserved) | `.env` file via `load_dotenv()` |
| **Staging** | `true` | Production-suitable backends only | Full (for validation) | AWS Secrets Manager or env injection |
| **Production** | `true` | `bedrock_converse` only | Policy-controlled (Phase 3) | IAM role / instance profile |

### 2.3 Threat Model Prioritization

The hardening program addresses threats in descending order of blast radius:

1. **Data egress to non-controlled infrastructure** (CRITICAL) — Claude CLI default, semantic dispatch bypass, non-Bedrock backends accepted.
2. **Accidental secret or IP commit** (HIGH) — minimal `.gitignore`, diagnostic directories containing proposal IP.
3. **Missing automated enforcement** (HIGH) — no CI/CD pipeline, no pre-commit hooks.
4. **Credential management** (MEDIUM) — plaintext AWS keys in `.env`, no rotation policy.
5. **Infrastructure configuration gaps** (varies) — VPC, IAM, CloudTrail, GDPR DPA.

---

## 3. Risk Acceptance Section

### 3.1 Temporarily Accepted Risks

The following risks are **explicitly accepted** for the current development and migration-validation phase. They will be remediated in Phase 3 after the prerequisites listed below are satisfied.

| Risk ID | Description | Severity | Accepted Until |
|---------|-------------|----------|----------------|
| **RA-01** | Full LLM response text written to `.claude/skill_diag/{skill}_{run}_response.txt` after every skill invocation | HIGH | Phase 3 gate (see 3.2) |
| **RA-02** | Parsed JSON output written to `.claude/skill_diag/{skill}_{run}_parsed.txt` | MEDIUM | Phase 3 gate |
| **RA-03** | Full system/user prompts written to `.claude/skill_diag/` on transport failure | HIGH | Phase 3 gate |
| **RA-04** | Full prompts/responses written to `.claude/semantic_diag/` on semantic dispatch failure | HIGH | Phase 3 gate |
| **RA-05** | Transport failure diagnostic metadata includes prompt character counts (not content) | LOW | Permanent (no content risk) |

### 3.2 Phase 3 Gate Prerequisites

Production hardening of diagnostic persistence (RA-01 through RA-04) is deferred until **all** of the following are satisfied:

1. **Bedrock migration stabilization** — The `bedrock_converse` backend has been validated for all 30 skills across both TAPM and cli-prompt execution modes with zero transport-layer failures in a complete Phase 1-8 run.
2. **Complete Phase 1-8 orchestration validation** — At least one full DAG run (all 13 nodes, all 11 gates) completes with `overall_status: pass` using the Bedrock Converse backend.
3. **Benchmark equivalence confirmation** — Benchmark telemetry confirms that Bedrock Converse produces structurally equivalent artifacts to Claude CLI for all phases, as measured by schema validation pass rates and gate pass rates.

Until these prerequisites are met, diagnostic persistence remains active to support debugging of transport failures, response parsing issues, and artifact validation mismatches during migration.

### 3.3 Mitigation for Accepted Risks

While RA-01 through RA-04 are accepted, the following mitigations reduce their impact:

- **Phase 0** expands `.gitignore` to cover `.claude/` (prevents accidental commit of diagnostics).
- **Phase 0** rotates AWS credentials (limits blast radius if `.env` is leaked).
- Developers are instructed to not manually `git add .claude/` or override `.gitignore`.
- Diagnostic directories are local-only; they are never transmitted by the runtime.

---

## 4. Security Phase Roadmap

```
Phase 0: Immediate Hygiene                    [Start immediately]
  |  .gitignore expansion
  |  Credential rotation
  |  .env.example audit
  |
  v  (start Phase 1 immediately)
Phase 1: Transport Lockdown                   [Starts after Phase 0]
  |  Production mode env var
  |  Backend enforcement guard
  |  Semantic dispatch backend routing
  |  Fail-closed default behavior
  |  Security test additions
  |
  v  (start Phase 2 repository-side items immediately)
Phase 2: Infrastructure & Compliance          [Starts after Phase 1]
  |
  |-- Repository-side (immediate):
  |     CI/CD pipeline creation
  |     Pre-commit secret scanning
  |     Path resolution tests
  |
  |-- Externally-dependent (variable timeline):
  |     AWS VPC PrivateLink              [AWS admin]
  |     IAM role scoping                 [AWS admin]
  |     CloudTrail enablement            [AWS admin]
  |     CloudWatch verification          [AWS admin]
  |     GDPR DPA execution              [Legal/compliance]
  |     Model availability validation    [DevOps]
  |
  v  (blocked on Phase 3 gate prerequisites, not on Phase 2)
Phase 3: Production Hardening                 [After migration stabilization]
  |  Environment-scoped persistence policy
  |  Diagnostic sanitization for production
  |  Deployment host lockdown
  |  Network egress restrictions
  |  Final production sign-off
  v
  PRODUCTION DEPLOYMENT
```

---

## 5. Phase-by-Phase Remediation Plan

### Phase 0: Immediate Hygiene

**Objective:** Eliminate the highest-probability accidental-exposure risks with zero code changes to the runtime. Start immediately.

| Item | Task | Severity | Type |
|------|------|----------|------|
| P0-1 | Expand `.gitignore` | HIGH | Repository |
| P0-2 | Rotate AWS credentials in `.env` | MEDIUM | Operational |
| P0-3 | Audit `.env.example` for security guidance | LOW | Repository |

### Phase 1: Transport Lockdown

**Objective:** Close all data-egress paths by enforcing Bedrock-only operation in production mode while preserving full development flexibility. Starts immediately after Phase 0.

| Item | Task | Severity | Type |
|------|------|----------|------|
| P1-1 | Implement `ORCHESTRATOR_PRODUCTION_MODE` guard | CRITICAL | Repository |
| P1-2 | Implement production backend enforcement | CRITICAL | Repository |
| P1-3 | Route semantic dispatch through multi-backend config | CRITICAL | Repository |
| P1-4 | Add startup backend logging/warning | MEDIUM | Repository |
| P1-5 | Add production-mode security tests | CRITICAL | Repository |

### Phase 2: Infrastructure and Compliance

**Objective:** Establish the AWS infrastructure and CI/CD controls required for institutional deployment. Repository-side items start immediately after Phase 1. AWS infrastructure and legal/compliance items are externally-dependent and execute whenever the responsible party is available.

| Item | Task | Severity | Type |
|------|------|----------|------|
| P2-1 | Create VPC PrivateLink endpoint for Bedrock | CRITICAL | AWS Infrastructure |
| P2-2 | Create scoped IAM role for Bedrock | CRITICAL | AWS Infrastructure |
| P2-3 | Enable CloudTrail for Bedrock API events | HIGH | AWS Infrastructure |
| P2-4 | Create CI/CD pipeline | HIGH | Deployment |
| P2-5 | Add pre-commit secret scanning hook | MEDIUM | Repository |
| P2-6 | Add `runner/paths.py` test coverage | MEDIUM | Repository |
| P2-7 | Execute GDPR DPA via AWS Artifact | MEDIUM | Operational/Policy |
| P2-8 | Validate model availability in target region | MEDIUM | Operational |
| P2-9 | Verify CloudWatch prompt logging is disabled | MEDIUM | AWS Infrastructure |

### Phase 3: Production Hardening (Post-migration stabilization)

**Objective:** Harden diagnostic persistence, deploy to locked-down production host, and complete final compliance verification.

| Item | Task | Severity | Type |
|------|------|----------|------|
| P3-1 | Design environment-scoped persistence policy | HIGH | Repository |
| P3-2 | Implement persistence policy enforcement | HIGH | Repository |
| P3-3 | Implement diagnostic sanitization for production | HIGH | Repository |
| P3-4 | Deploy to locked-down production host | HIGH | Deployment |
| P3-5 | Configure network egress restrictions | HIGH | AWS Infrastructure |
| P3-6 | Final production compliance verification | CRITICAL | Operational |

---

## 6. Repository-Side Implementation Tasks

### P0-1: Expand `.gitignore`

**Severity:** HIGH
**Rationale:** The current `.gitignore` has only 2 entries (`.env`, `*_accessKeys.csv`). The `.claude/` directory tree contains diagnostic files with full proposal IP, run records, benchmark data, and agent memory. Python bytecode, test caches, and virtual environments are also unprotected.
**Implementation scope:** Single file change.
**Affected files:** `.gitignore`
**Dependency ordering:** None. Can be done immediately.
**Rollback considerations:** Reversible. `git rm --cached` any files that were previously tracked.
**Validation strategy:** `git status` after change confirms no `.claude/` files are staged. CI check (P2-4) validates coverage.

**Required `.gitignore` additions:**

```
# Runtime and diagnostic state
.claude/skill_diag/
.claude/semantic_diag/
.claude/runs/
.claude/logs/
.claude/cache/
.claude/benchmark/

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
*.egg

# Virtual environments
.venv/
venv/
env/

# Test and tooling caches
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage

# Logs
*.log

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

**Note:** `.claude/agent-memory/`, `.claude/agents/`, `.claude/skills/`, `.claude/workflows/` are intentionally NOT gitignored — they are constitutional configuration, not generated state.

---

### P0-3: Audit `.env.example` for Security Guidance

**Severity:** LOW
**Rationale:** `.env.example` should document the production-mode variable and warn against committing credentials.
**Implementation scope:** Documentation change to `.env.example`.
**Affected files:** `.env.example`
**Dependency ordering:** None.
**Rollback considerations:** Fully reversible.
**Validation strategy:** Manual review.

**Required additions to `.env.example`:**

```bash
# --- Production mode (recommended for staging and production) ---
# When true, rejects non-production backends and enforces fail-closed behavior.
# ORCHESTRATOR_PRODUCTION_MODE=true
```

---

### P1-1: Implement `ORCHESTRATOR_PRODUCTION_MODE` Guard

**Severity:** CRITICAL
**Rationale:** The compliance audit found that the default backend is `claude_cli`, which routes all proposal IP through Anthropic infrastructure. There is no mechanism to distinguish production from development behavior. Adding a production-mode environment variable creates the primary enforcement boundary.
**Implementation scope:** Add env var check at the top of `resolve_provider_config()`. When `ORCHESTRATOR_PRODUCTION_MODE=true`, downstream checks (P1-2) are activated.
**Affected files:** `runner/transport/config.py`
**Dependency ordering:** Must be implemented before P1-2 (which uses the production-mode flag).
**Rollback considerations:** Fully reversible. If `ORCHESTRATOR_PRODUCTION_MODE` is unset (the default), all behavior is unchanged. Existing development and test workflows are unaffected.
**Validation strategy:** Test P1-5 (`test_production_mode_rejects_claude_cli`).

**Implementation:**

In `resolve_provider_config()` (currently at line 452 of `runner/transport/config.py`):

```python
def resolve_provider_config() -> ProviderConfig:
    # --- Production mode enforcement ---
    production_mode = (
        os.environ.get("ORCHESTRATOR_PRODUCTION_MODE", "").lower() == "true"
    )

    # [existing preset path ...]
    # [existing legacy path ...]

    # After backend is resolved, enforce production restrictions:
    if production_mode:
        _enforce_production_backend(config)

    return config
```

Add enforcement function:

```python
#: Backends allowed in production mode.
PRODUCTION_BACKENDS: frozenset[str] = frozenset({
    "bedrock_converse",
    "bedrock",
})

def _enforce_production_backend(config: ProviderConfig) -> None:
    """Reject non-production backends when ORCHESTRATOR_PRODUCTION_MODE=true."""
    if config.backend_name not in PRODUCTION_BACKENDS:
        raise ValueError(
            f"ORCHESTRATOR_PRODUCTION_MODE=true but backend "
            f"{config.backend_name!r} is not production-suitable. "
            f"Production-allowed backends: {sorted(PRODUCTION_BACKENDS)}. "
            f"Set ORCHESTRATOR_TRANSPORT_PRESET or "
            f"ORCHESTRATOR_TRANSPORT_BACKEND to a production backend."
        )
```

---

### P1-2: Implement Production Backend Enforcement

**Severity:** CRITICAL
**Rationale:** The `production_suitable` flag on `TransportPreset` is metadata-only and never checked at runtime. All 6 backends are treated equally. An operator can accidentally or intentionally set a non-Bedrock backend in production with no warning or block.
**Implementation scope:** The enforcement function in P1-1 implements this. Additionally, when using presets in production mode, verify `preset.production_suitable`.
**Affected files:** `runner/transport/config.py`
**Dependency ordering:** Depends on P1-1.
**Rollback considerations:** Fully reversible (remove the `_enforce_production_backend` call).
**Validation strategy:** Test P1-5 (`test_production_mode_rejects_non_production_backends`).

**Additional enforcement in `resolve_provider_config_from_preset()`:**

```python
def resolve_provider_config_from_preset(preset_name: str) -> ProviderConfig:
    preset = get_transport_preset(preset_name)

    # Production mode: reject non-production presets
    production_mode = (
        os.environ.get("ORCHESTRATOR_PRODUCTION_MODE", "").lower() == "true"
    )
    if production_mode and not preset.production_suitable:
        raise ValueError(
            f"ORCHESTRATOR_PRODUCTION_MODE=true but preset "
            f"{preset_name!r} is not production-suitable "
            f"(production_suitable=False). Use a production preset."
        )

    # [rest of existing logic ...]
```

---

### P1-3: Route Semantic Dispatch Through Multi-Backend Config

**Severity:** CRITICAL
**Rationale:** The semantic dispatch layer (`runner/semantic_dispatch.py`) always routes through `invoke_claude_text()` via the benchmark transport hook, which always invokes the local `claude` CLI subprocess. This is independent of `ORCHESTRATOR_TRANSPORT_BACKEND`. Even when Bedrock is configured for skills, all 7 semantic predicate evaluations route through Anthropic infrastructure. This is a hidden egress path that violates the data-egress prevention requirement.
**Implementation scope:** Modify `invoke_agent()` in `semantic_dispatch.py` to resolve the transport backend and route through the Bedrock Converse path when configured.
**Affected files:** `runner/semantic_dispatch.py`
**Dependency ordering:** Depends on P1-1 (production mode must exist). Should be implemented after P1-2 to share the backend enforcement logic.
**Rollback considerations:** Medium risk. Semantic predicates currently work reliably via Claude CLI. Routing through Bedrock Converse introduces a new code path that must be validated. Rollback: revert the import change and re-test semantic predicates.
**Validation strategy:** Test P1-5 (`test_semantic_dispatch_uses_configured_backend`). Run at least one full gate evaluation cycle with `bedrock_converse` to confirm semantic predicates work end-to-end.

**Implementation approach:**

The current import in `semantic_dispatch.py` (line 57):
```python
from runner.benchmark.transport_hook import instrumented_invoke as invoke_claude_text
```

This always resolves to `runner.claude_transport.invoke_claude_text`, which is Claude CLI only.

**Required change:** Add a backend-aware invocation path parallel to the skill runtime pattern:

```python
# In invoke_agent(), after building prompts:
provider_config = _resolve_transport_backend()  # reuse from skill_runtime

if provider_config.backend_name == "claude_cli":
    # Existing Claude CLI path (unchanged)
    response_text = invoke_claude_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=AGENT_MODEL,
        max_tokens=AGENT_MAX_TOKENS,
        ...
    )
elif provider_config.backend_name == "bedrock_converse":
    # Native Bedrock Converse path
    from runner.transport.config import build_converse_backend
    backend = build_converse_backend(provider_config, max_tokens=AGENT_MAX_TOKENS)
    result = backend([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    response_text = result.get("content") or ""
else:
    # OpenAI-compatible path
    from runner.transport.config import build_openai_backend
    backend = build_openai_backend(provider_config, max_tokens=AGENT_MAX_TOKENS)
    result = backend([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    response_text = result.get("content") or ""
```

**Note:** The `_resolve_transport_backend()` function and cache can be shared from `skill_runtime.py` by extracting it to a shared module or importing it.

---

### P1-4: Add Startup Backend Logging/Warning

**Severity:** MEDIUM
**Rationale:** Operators should have immediate visibility into which backend is active at DAG startup, especially to detect accidental Claude CLI usage.
**Implementation scope:** Add a log line at startup in `__main__.py` after backend resolution.
**Affected files:** `runner/__main__.py`
**Dependency ordering:** After P1-1.
**Rollback considerations:** Fully reversible (remove log line).
**Validation strategy:** Manual verification in `--verbose` output.

**Implementation:**

```python
# In main(), after RunContext initialization:
from runner.transport.config import resolve_provider_config
try:
    _pc = resolve_provider_config()
    _out(
        f"[BACKEND] transport={_pc.backend_name}  "
        f"model={_pc.model or '(default)'}  "
        f"preset={_pc.preset_name or '(none)'}",
        "backend_info",
        backend=_pc.backend_name,
        model=_pc.model,
        preset=_pc.preset_name,
    )
except ValueError as exc:
    _err(f"Transport configuration error: {exc}")
    return 3
```

---

### P1-5: Add Production-Mode Security Tests

**Severity:** CRITICAL
**Rationale:** Every hardening change requires a corresponding test. Without tests, regressions during ongoing migration work could silently re-open egress paths.
**Implementation scope:** New test file `tests/test_production_mode.py`.
**Affected files:** `tests/test_production_mode.py` (new)
**Dependency ordering:** After P1-1, P1-2, P1-3.
**Rollback considerations:** Tests are additive; no rollback concern.
**Validation strategy:** Tests themselves are the validation.

**Required tests:**

```python
class TestProductionModeEnforcement:
    """Verify ORCHESTRATOR_PRODUCTION_MODE=true enforces backend restrictions."""

    def test_production_mode_rejects_claude_cli_default(self):
        """Default backend (claude_cli) is rejected in production mode."""

    def test_production_mode_rejects_together_ai(self):
        """together_ai backend is rejected in production mode."""

    def test_production_mode_rejects_ollama(self):
        """ollama backend is rejected in production mode."""

    def test_production_mode_rejects_openai_compatible(self):
        """generic openai_compatible backend is rejected in production mode."""

    def test_production_mode_accepts_bedrock_converse(self):
        """bedrock_converse backend is accepted in production mode."""

    def test_production_mode_accepts_bedrock_mantle(self):
        """bedrock (mantle) backend is accepted in production mode."""

    def test_production_mode_rejects_non_production_preset(self):
        """Non-production preset (e.g. OLLAMA_LOCAL) is rejected."""

    def test_production_mode_accepts_production_preset(self):
        """Production preset (BEDROCK_CONVERSE_US) is accepted."""

    def test_development_mode_allows_all_backends(self):
        """When ORCHESTRATOR_PRODUCTION_MODE is unset, all backends allowed."""

class TestSemanticDispatchBackendRouting:
    """Verify semantic dispatch respects configured backend."""

    def test_semantic_dispatch_uses_bedrock_when_configured(self):
        """When backend is bedrock_converse, semantic dispatch does not invoke claude CLI."""
```

---

### P2-5: Add Pre-Commit Secret Scanning Hook

**Severity:** MEDIUM
**Rationale:** With diagnostic files containing proposal IP and `.env` containing credentials, a pre-commit hook provides defense-in-depth against accidental commits of sensitive material.
**Implementation scope:** Add `.pre-commit-config.yaml` with `detect-secrets` hook.
**Affected files:** `.pre-commit-config.yaml` (new)
**Dependency ordering:** None. Can be done in parallel.
**Rollback considerations:** Fully reversible (remove config file, uninstall hook).
**Validation strategy:** Attempt to commit a file containing a fake AWS key pattern; verify hook blocks it.

---

### P2-6: Add `runner/paths.py` Test Coverage

**Severity:** MEDIUM
**Rationale:** `find_repo_root()` and `resolve_repo_path()` are used in 29+ call sites across the codebase. They have zero dedicated tests. `find_repo_root()` walks up the filesystem following resolved symlinks, creating a potential for repo-root spoofing in compromised environments.
**Implementation scope:** New test file `tests/test_paths.py`.
**Affected files:** `tests/test_paths.py` (new)
**Dependency ordering:** None. Can be done in parallel.
**Rollback considerations:** Tests are additive.
**Validation strategy:** Tests themselves are the validation.

**Required tests:**

```python
class TestFindRepoRoot:
    def test_finds_root_from_subdirectory(self): ...
    def test_raises_when_no_markers_found(self): ...
    def test_requires_both_claude_md_and_git(self): ...
    def test_stops_at_filesystem_root(self): ...
    def test_symlink_traversal_returns_resolved_path(self): ...
    def test_max_depth_limit(self): ...

class TestResolveRepoPath:
    def test_absolute_path_returned_unchanged(self): ...
    def test_relative_path_joined_with_repo_root(self): ...
    def test_relative_path_without_root_returns_as_is(self): ...
    def test_forward_slash_paths_work_on_all_platforms(self): ...
```

---

### P3-1: Design Environment-Scoped Persistence Policy

**Severity:** HIGH
**Rationale:** Diagnostic persistence is currently always-on and unconditional. For production, prompt/response content must not be persisted to disk. For development and migration validation, full persistence must be preserved. The solution is an environment-scoped policy that controls persistence behavior based on `ORCHESTRATOR_PRODUCTION_MODE` and an optional `ORCHESTRATOR_DIAGNOSTIC_LEVEL` variable.
**Implementation scope:** Design document and data contract. No code changes in this task.
**Affected files:** None (design only; produces a specification for P3-2).
**Dependency ordering:** After Phase 3 gate prerequisites are met.
**Rollback considerations:** N/A (design only).
**Validation strategy:** Design review against compliance brief requirements.

**Proposed policy:**

| Environment | `ORCHESTRATOR_DIAGNOSTIC_LEVEL` | Behavior |
|-------------|-------------------------------|----------|
| Development | unset or `full` | Current behavior: full response text, full prompts on failure, parsed output. **Preserved unchanged.** |
| Development | `metadata` | Metadata only: char counts, timing, error class. No prompt/response content. |
| Production | unset | Defaults to `metadata`. Full content never written. |
| Production | `full` | **Rejected.** Production mode + full diagnostics is a policy violation. Raises `ValueError` at startup. |
| Production | `metadata` | Metadata only. Explicit confirmation of default. |

**Diagnostic file behavior under `metadata` level:**

| File | `full` level | `metadata` level |
|------|-------------|-----------------|
| `{skill}_{run}_response.txt` | Full response text | **Not written** |
| `{skill}_{run}_parsed.txt` | Parsed JSON (5KB) | **Not written** |
| `{skill}_{run}_phase_e.txt` | Phase E state (no content) | Written (no content risk) |
| `{skill}_{run}_transport_diag.json` | Metadata (no content) | Written (no content risk) |
| `{skill}_{run}_system_prompt.txt` | Full system prompt | **Not written** |
| `{skill}_{run}_user_prompt.txt` | Full user prompt | **Not written** |
| Semantic diag prompts/responses | Full content | **Not written** |

---

### P3-2: Implement Persistence Policy Enforcement

**Severity:** HIGH
**Rationale:** Implements the policy designed in P3-1.
**Implementation scope:** Modify diagnostic write functions in `skill_runtime.py` and `semantic_dispatch.py` to check the persistence policy before writing content files.
**Affected files:** `runner/skill_runtime.py`, `runner/semantic_dispatch.py`
**Dependency ordering:** After P3-1 design is approved and Phase 3 gate prerequisites are met.
**Rollback considerations:** Medium risk. Removing the policy check restores full persistence. All changes are guarded by the new env var; existing behavior is preserved when the var is unset in development.
**Validation strategy:** New tests `test_diagnostic_capture_respects_policy` and `test_production_rejects_full_diagnostics`.

**Implementation locations:**

1. `runner/skill_runtime.py:1710-1748` — unconditional response diagnostic capture. Wrap in policy check.
2. `runner/skill_runtime.py:838-940` — `_write_transport_failure_diagnostics()`. Skip prompt/response companion files under `metadata` policy.
3. `runner/semantic_dispatch.py:316-396` — `_write_semantic_diagnostics()`. Skip prompt/response files under `metadata` policy.

---

### P3-3: Implement Diagnostic Sanitization for Production

**Severity:** HIGH
**Rationale:** Even under `metadata` policy, transport failure metadata files should not contain prompt snippets in error messages. Error messages from LLM providers sometimes echo back portions of the request.
**Implementation scope:** Truncate `exception_message` and `fail_message` fields in diagnostic JSON to safe lengths (200 chars max) and strip any content that matches known prompt patterns.
**Affected files:** `runner/skill_runtime.py`, `runner/semantic_dispatch.py`
**Dependency ordering:** After P3-2.
**Rollback considerations:** Low risk. Reversible by removing truncation.
**Validation strategy:** Test that diagnostic JSON under production mode contains no prompt content in any field.

---

## 7. AWS-Side Implementation Tasks

### P2-1: Create VPC PrivateLink Endpoint for Bedrock

**Severity:** CRITICAL
**Rationale:** Without PrivateLink, Bedrock API calls traverse the public internet. Even with TLS, this violates closed-network requirements for institutional deployment. The Bedrock Security Assessment (Section 4) confirms PrivateLink support.
**Implementation scope:** AWS console or CloudFormation. Create VPC interface endpoint for `bedrock-runtime` service in the target region.
**Affected files:** None (infrastructure-only).
**Dependency ordering:** VPC must exist. Can be done in parallel with all Phase 1 work.
**Rollback considerations:** Endpoint can be deleted. Applications fall back to public endpoint (degraded security posture, not a functional failure).
**Validation strategy:** `aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.<region>.bedrock-runtime` confirms endpoint exists. Test Bedrock Converse call from within VPC succeeds.

---

### P2-2: Create Scoped IAM Role for Bedrock

**Severity:** CRITICAL
**Rationale:** The current `.env` contains IAM user access keys. Production must use an IAM role with least-privilege permissions scoped to specific Bedrock models and regions.
**Implementation scope:** IAM policy creation and role assumption configuration.
**Affected files:** None (infrastructure-only).
**Dependency ordering:** None.
**Rollback considerations:** Role can be deleted; application falls back to IAM user credentials (degraded security posture).
**Validation strategy:** `aws sts get-caller-identity` confirms role assumption. Bedrock Converse call succeeds. Attempt to call a non-allowed model fails with `AccessDeniedException`.

**Required IAM policy:**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowBedrockConverse",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
                "arn:aws:bedrock:*:*:inference-profile/us.anthropic.claude-*"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": ["eu-west-1", "us-east-1"]
                }
            }
        }
    ]
}
```

---

### P2-3: Enable CloudTrail for Bedrock API Events

**Severity:** HIGH
**Rationale:** Auditability is a mandatory requirement per the Bedrock Security Assessment. CloudTrail provides a tamper-evident log of all Bedrock API calls, including caller identity, timestamp, and request metadata (not prompt content).
**Implementation scope:** AWS CloudTrail trail creation or modification.
**Affected files:** None (infrastructure-only).
**Dependency ordering:** None.
**Rollback considerations:** Trail can be disabled. No functional impact.
**Validation strategy:** Make a Bedrock Converse call, then verify the event appears in CloudTrail within 15 minutes.

---

### P2-9: Verify CloudWatch Prompt Logging is Disabled

**Severity:** MEDIUM
**Rationale:** AWS Bedrock supports opt-in model invocation logging to CloudWatch, which can capture prompts and completions. This must be verified as disabled (the default) to prevent unintended prompt retention in AWS infrastructure.
**Implementation scope:** Verification only. Check Bedrock model invocation logging settings in the AWS console.
**Affected files:** None.
**Dependency ordering:** None.
**Rollback considerations:** N/A (verification only).
**Validation strategy:** AWS console > Bedrock > Settings > Model invocation logging > Verify "Disabled". Document the verification with a screenshot or CLI output.

---

## 8. Operational/Policy Tasks

### P0-2: Rotate AWS Credentials

**Severity:** MEDIUM
**Rationale:** The `.env` file contains plaintext `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. While `.env` is gitignored and was never committed, the credentials are at risk if the file is inadvertently shared, copied to a backup, or accessed by unauthorized software.
**Implementation scope:** AWS IAM console. Create new access key, update `.env`, deactivate old key, delete old key after validation.
**Affected files:** `.env` (local only, never committed)
**Dependency ordering:** None.
**Rollback considerations:** If new credentials fail, reactivate old key (before deletion).
**Validation strategy:** Bedrock Converse call succeeds with new credentials. Old credentials return `InvalidClientTokenId`.

---

### P2-7: Execute GDPR DPA via AWS Artifact

**Severity:** MEDIUM
**Rationale:** Mandatory for EU institutional deployment. The AWS GDPR DPA is available as a self-service download via AWS Artifact.
**Implementation scope:** Administrative/legal. Download DPA, execute (sign), file with institutional records.
**Affected files:** None.
**Dependency ordering:** None.
**Rollback considerations:** N/A (legal document).
**Validation strategy:** Signed DPA on file.

---

### P2-8: Validate Model Availability in Target Region

**Severity:** MEDIUM
**Rationale:** Not all Bedrock models are available in all regions. The target model (`us.anthropic.claude-sonnet-4-6` or equivalent) must be confirmed available in the selected region before deployment.
**Implementation scope:** AWS Bedrock console check or `aws bedrock list-foundation-models --region <target>`.
**Affected files:** None.
**Dependency ordering:** Region selection must be finalized (P2-2).
**Rollback considerations:** If model is unavailable, select an alternative region or model.
**Validation strategy:** `aws bedrock list-foundation-models` includes the target model. A test `converse()` call succeeds.

---

## 9. Required Code Modifications

### Summary Table

| ID | File(s) | Change | Phase | Severity | Breaking? |
|----|---------|--------|-------|----------|-----------|
| P0-1 | `.gitignore` | Expand from 2 to ~30 entries | 0 | HIGH | No |
| P0-3 | `.env.example` | Add production mode documentation | 0 | LOW | No |
| P1-1 | `runner/transport/config.py` | Add `ORCHESTRATOR_PRODUCTION_MODE` check and `_enforce_production_backend()` | 1 | CRITICAL | No (default is development mode) |
| P1-2 | `runner/transport/config.py` | Add preset `production_suitable` check in production mode | 1 | CRITICAL | No |
| P1-3 | `runner/semantic_dispatch.py` | Add multi-backend resolution to `invoke_agent()` | 1 | CRITICAL | No (Claude CLI path preserved as default) |
| P1-4 | `runner/__main__.py` | Add backend info log at startup | 1 | MEDIUM | No |
| P1-5 | `tests/test_production_mode.py` (new) | Production-mode enforcement tests | 1 | CRITICAL | No |
| P2-5 | `.pre-commit-config.yaml` (new) | Secret scanning hook | 2 | MEDIUM | No |
| P2-6 | `tests/test_paths.py` (new) | Path resolution security tests | 2 | MEDIUM | No |
| P3-1 | (design document) | Persistence policy specification | 3 | HIGH | No |
| P3-2 | `runner/skill_runtime.py`, `runner/semantic_dispatch.py` | Persistence policy enforcement | 3 | HIGH | No (default preserves current behavior) |
| P3-3 | `runner/skill_runtime.py`, `runner/semantic_dispatch.py` | Error message sanitization in production | 3 | HIGH | No |

**Key guarantee:** No modification changes default development-mode behavior. All enforcement is gated behind `ORCHESTRATOR_PRODUCTION_MODE=true`. The migration validation workflow is unaffected.

---

## 10. Required CI/CD Controls

### P2-4: Create CI/CD Pipeline

**Severity:** HIGH
**Rationale:** 95 test files and 1600+ tests exist but are only validated manually. Security-critical tests (sandbox, path traversal, symlink escape) are among them. Without CI, regressions can be introduced silently.
**Implementation scope:** GitHub Actions workflow (or equivalent).
**Affected files:** `.github/workflows/ci.yml` (new)
**Dependency ordering:** None. Can be done in parallel with all other work.
**Rollback considerations:** Workflow can be disabled or deleted.
**Validation strategy:** Pipeline runs on push, all tests pass.

**Required CI jobs:**

| Job | Purpose | Trigger |
|-----|---------|---------|
| `test` | Run full test suite (`pytest tests/`) | Push, PR |
| `security-tests` | Run sandbox/path/symlink tests specifically | Push, PR |
| `secret-scan` | Run `detect-secrets` scan on diff | PR |
| `gitignore-check` | Verify no `.claude/`, `__pycache__/`, `.env` files are tracked | Push, PR |
| `production-backend-check` | Run production-mode enforcement tests | Push, PR |
| `dependency-audit` | `pip-audit` for known CVEs in dependencies | Weekly schedule |

---

## 11. Required Test Coverage

### Summary of All Required Tests

| Test ID | Test Name | Phase | Priority | Tests What |
|---------|-----------|-------|----------|------------|
| T1-1 | `test_production_mode_rejects_claude_cli_default` | 1 | CRITICAL | P1-1 enforcement |
| T1-2 | `test_production_mode_rejects_together_ai` | 1 | CRITICAL | P1-2 enforcement |
| T1-3 | `test_production_mode_rejects_ollama` | 1 | CRITICAL | P1-2 enforcement |
| T1-4 | `test_production_mode_rejects_openai_compatible` | 1 | CRITICAL | P1-2 enforcement |
| T1-5 | `test_production_mode_accepts_bedrock_converse` | 1 | CRITICAL | P1-2 positive case |
| T1-6 | `test_production_mode_accepts_bedrock_mantle` | 1 | CRITICAL | P1-2 positive case |
| T1-7 | `test_production_mode_rejects_non_production_preset` | 1 | CRITICAL | P1-2 preset enforcement |
| T1-8 | `test_production_mode_accepts_production_preset` | 1 | CRITICAL | P1-2 preset positive case |
| T1-9 | `test_development_mode_allows_all_backends` | 1 | CRITICAL | Non-regression for dev |
| T1-10 | `test_semantic_dispatch_uses_bedrock_when_configured` | 1 | CRITICAL | P1-3 semantic routing |
| T2-1 | `test_find_repo_root_from_subdirectory` | 2 | MEDIUM | Path resolution |
| T2-2 | `test_find_repo_root_raises_when_no_markers` | 2 | MEDIUM | Fail-closed behavior |
| T2-3 | `test_find_repo_root_requires_both_markers` | 2 | MEDIUM | Double-marker requirement |
| T2-4 | `test_find_repo_root_symlink_traversal` | 2 | MEDIUM | Symlink safety |
| T2-5 | `test_resolve_repo_path_absolute_unchanged` | 2 | MEDIUM | Path resolution |
| T2-6 | `test_resolve_repo_path_relative_joined` | 2 | MEDIUM | Path resolution |
| T2-7 | `test_gitignore_covers_claude_directory` | 2 | MEDIUM | P0-1 validation |
| T3-1 | `test_diagnostic_capture_respects_metadata_policy` | 3 | HIGH | P3-2 enforcement |
| T3-2 | `test_production_rejects_full_diagnostics` | 3 | HIGH | P3-2 rejection |
| T3-3 | `test_error_message_sanitization_in_production` | 3 | HIGH | P3-3 enforcement |

---

## 12. Production Deployment Gates

Each gate must be satisfied before proceeding to the next deployment stage.

### Gate 1: Phase 0 Complete

- [ ] `.gitignore` expanded and committed
- [ ] AWS credentials rotated
- [ ] `.env.example` updated with production mode documentation
- [ ] No `.claude/` files are tracked in git

### Gate 2: Phase 1 Complete

- [ ] `ORCHESTRATOR_PRODUCTION_MODE` guard implemented
- [ ] Production backend enforcement implemented
- [ ] Semantic dispatch multi-backend routing implemented
- [ ] Startup backend logging implemented
- [ ] All T1-* tests pass
- [ ] Full test suite (1600+ tests) passes with no regressions
- [ ] Migration validation workflow confirmed unaffected (development-mode DAG run succeeds)

### Gate 3: Phase 2 Complete

- [ ] VPC PrivateLink endpoint created and verified
- [ ] IAM role created with least-privilege policy
- [ ] CloudTrail enabled and verified
- [ ] CloudWatch prompt logging verified disabled
- [ ] CI/CD pipeline running and green
- [ ] Pre-commit secret scanning installed
- [ ] `runner/paths.py` test coverage added
- [ ] GDPR DPA executed
- [ ] Model availability validated in target region

### Gate 4: Phase 3 Prerequisites Met

- [ ] Bedrock Converse backend validated for all 30 skills (TAPM + cli-prompt)
- [ ] Complete Phase 1-8 DAG run passes with `bedrock_converse` backend
- [ ] Benchmark equivalence confirmed between Claude CLI and Bedrock Converse

### Gate 5: Phase 3 Complete (Production Sign-Off)

- [ ] Environment-scoped persistence policy designed and approved
- [ ] Persistence policy enforcement implemented
- [ ] Diagnostic sanitization implemented
- [ ] All T3-* tests pass
- [ ] Production deployment host configured:
  - [ ] IAM role credentials (no access keys)
  - [ ] No Claude CLI binary installed
  - [ ] Network egress restricted to VPC PrivateLink
  - [ ] `ORCHESTRATOR_PRODUCTION_MODE=true` set
  - [ ] `ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US` (or EU equivalent) set
- [ ] End-to-end production validation: full DAG run with production config succeeds
- [ ] Compliance verification: all CRITICAL and HIGH findings from `security_compliance_brief.md` resolved

---

## 13. Deferred Hardening Items

The following items are identified but intentionally deferred beyond Phase 3:

| Item | Rationale for Deferral | Trigger for Revisit |
|------|----------------------|---------------------|
| **Region allowlist enforcement** (`ORCHESTRATOR_ALLOWED_REGIONS`) | Operational policy is sufficient for initial deployment. Code-level enforcement is defense-in-depth that can be added later. | Multi-region deployment or compliance audit finding. |
| **Automatic credential rotation** | IAM role credentials are automatically rotated by AWS. Access key rotation is manual but has a defined 90-day policy. Automation is an optimization. | Scale-out to multiple deployment hosts or SOC audit requirement. |
| **Encrypted diagnostic storage** | Phase 3 disables content persistence in production. Encrypted storage is only needed if full diagnostics are re-enabled for production debugging. | Production debugging incident requiring full diagnostics. |
| **Bedrock Provisioned Throughput** | On-demand throughput is sufficient for initial deployment. Provisioned throughput reserves dedicated capacity for predictable latency. | SLA requirements or latency complaints during high-volume proposal preparation. |
| **API key rotation for bedrock-mantle** | `bedrock_converse` (native IAM) is the approved production backend, not `bedrock` (mantle + API key). Mantle key rotation is only relevant if mantle is used. | Decision to use bedrock-mantle instead of native Converse API. |

---

## 14. Temporary Risk Acceptance Rationale

### Why Diagnostic Persistence is Preserved

The diagnostic persistence infrastructure (`.claude/skill_diag/`, `.claude/semantic_diag/`) serves three critical functions during the current migration-validation phase:

1. **Transport failure debugging.** When a Bedrock Converse call fails, the full prompt and response are essential for diagnosing whether the failure is in message format conversion, tool schema translation, or model behavior differences. Without these diagnostics, transport failures during migration testing are opaque.

2. **Response parsing validation.** The skill runtime's JSON extraction logic (`_extract_json_response`) handles multiple response shapes (bare JSON, markdown-fenced, embedded in prose). When migrating to a new backend, the response format may differ. The `_response.txt` and `_parsed.txt` diagnostics allow direct comparison of raw vs. parsed output.

3. **Benchmark equivalence analysis.** Comparing Claude CLI output to Bedrock Converse output requires being able to inspect actual responses. The benchmark telemetry captures only character counts; the diagnostic files provide the content-level comparison needed for equivalence confirmation.

### Why This is Safe During Development

1. **`.gitignore` expansion (Phase 0)** prevents accidental commit of diagnostic directories.
2. **Development happens on a local workstation**, not a shared server.
3. **No automated pipeline** currently pushes diagnostic data anywhere.
4. **The diagnostic directories are ephemeral** — they can be deleted at any time without affecting the constitutional state in `docs/`.

### When This Acceptance Expires

This risk acceptance expires when Phase 3 gate prerequisites (Section 3.2) are met. At that point, the persistence policy (P3-1, P3-2) must be implemented before production deployment.

---

## 15. Final Production-Readiness Criteria

The Proposal Orchestrator is production-ready when **all** of the following are true:

### Transport Security

- [ ] `ORCHESTRATOR_PRODUCTION_MODE=true` rejects all non-production backends
- [ ] Default backend (when unset) fails closed in production mode
- [ ] Semantic dispatch routes through the configured backend (not hardcoded Claude CLI)
- [ ] No Claude CLI binary is present on the production deployment host
- [ ] Network egress is restricted to VPC PrivateLink endpoint

### Infrastructure Security

- [ ] VPC PrivateLink endpoint for Bedrock is active and verified
- [ ] IAM role with least-privilege Bedrock policy is active
- [ ] CloudTrail is logging Bedrock API events
- [ ] CloudWatch model invocation logging is verified disabled
- [ ] Credentials are injected via IAM role (no access keys in files)

### Data Protection

- [ ] Diagnostic persistence is policy-controlled (metadata-only in production)
- [ ] No prompt or response content is written to disk in production mode
- [ ] `.gitignore` covers all generated/sensitive directories
- [ ] No secrets are present in tracked files

### Compliance

- [ ] GDPR DPA executed via AWS Artifact
- [ ] Target model confirmed available in selected region
- [ ] Data residency confirmed (region-locked IAM policy)

### Verification

- [ ] CI/CD pipeline running with all security checks green
- [ ] Pre-commit secret scanning active
- [ ] All CRITICAL and HIGH security tests passing
- [ ] Full DAG run (Phase 1-8) succeeds with production configuration
- [ ] Benchmark equivalence between Claude CLI and Bedrock Converse confirmed

### Operational

- [ ] Production environment configuration documented
- [ ] Credential rotation policy documented (90-day max for any access keys)
- [ ] Incident response procedure documented for credential compromise
- [ ] Rollback procedure documented for backend configuration errors

---

*Implementation plan produced 2026-05-28. Based on security compliance audit of same date. This plan governs the hardening roadmap and must be updated when Phase 3 gate prerequisites are met.*
