# Security Compliance Brief

## Proposal Orchestrator — AWS Bedrock Production-Readiness Audit

**Date:** 2026-05-28
**Baseline:** `docs/benchmark_reports/aws_bedrock_security_assessment.md`
**Scope:** Repository-wide security, transport, logging, sandbox, IAM, deployment
**Branch:** `benchmark_engine`
**Status:** CONDITIONAL PASS — Remediation Required Before Production

---

## 1. Executive Summary

The Proposal Orchestrator has a well-architected security foundation: sandboxed tool execution with symlink escape protection, atomic file writes, fail-closed transport semantics, and a configurable multi-backend transport layer with native Bedrock Converse API support. However, the system is **not production-ready** in its current state. Critical gaps include: the default transport backend is `claude_cli` (Anthropic infrastructure, not Bedrock), there is no runtime enforcement preventing non-Bedrock backends in production, diagnostic files persist full prompt content and LLM responses to disk, `.claude/` directories containing sensitive diagnostics are not gitignored, the `.gitignore` is dangerously minimal, AWS IAM credentials exist in plaintext in the local `.env` file (not committed but at risk), and no CI/CD pipeline exists for security validation. The system requires 7 repository-side, 5 AWS infrastructure-side, and 4 operational/policy-side remediations before institutional deployment.

---

## 2. Security Architecture Overview

### Transport Layer Stack

```
CLI Entry Point (__main__.py)
    |
    +-- DAGScheduler (dag_scheduler.py)
           |
           +-- Agent Runtime (agent_runtime.py)
                  |
                  +-- Skill Runtime (skill_runtime.py)
                         |
                         +-- Backend Resolution (transport/config.py)
                         |      |
                         |      +-- ORCHESTRATOR_TRANSPORT_PRESET env var
                         |      +-- ORCHESTRATOR_TRANSPORT_BACKEND env var
                         |      +-- Default: "claude_cli"
                         |
                         +-- Three backend paths:
                               |
                               +-- claude_cli: subprocess("claude -p") → Anthropic infra
                               +-- bedrock_converse: boto3 → Bedrock Converse API (native)
                               +-- bedrock/openai_compatible: httpx → bedrock-mantle/v1
```

### Backend Selection Mechanism

| Env Var | Default | Effect |
|---------|---------|--------|
| `ORCHESTRATOR_TRANSPORT_PRESET` | (unset) | Named preset (e.g. `BEDROCK_CONVERSE_US`) |
| `ORCHESTRATOR_TRANSPORT_BACKEND` | `claude_cli` | Backend selector |
| `ORCHESTRATOR_TRANSPORT_ENDPOINT` | (unset) | Base URL for HTTP backends |
| `ORCHESTRATOR_TRANSPORT_API_KEY` | (unset) | API key (never logged in ProviderConfig) |
| `ORCHESTRATOR_TRANSPORT_MODEL` | varies | Model ID override |
| `AWS_REGION` | `eu-west-1` / `us-east-1` | AWS region for Bedrock |

### Supported Backends

| Backend | Transport | Auth | Production Suitable (declared) | Production Suitable (enforced) |
|---------|-----------|------|-------------------------------|-------------------------------|
| `claude_cli` | subprocess → local `claude` binary | Claude Code Max subscription | **No** | **Not enforced** |
| `bedrock_converse` | boto3 → Bedrock Converse API | IAM credentials (standard AWS chain) | **Yes** | **Not enforced** |
| `bedrock` | httpx → bedrock-mantle OpenAI-compat | API key (Bearer token) | Yes (with PrivateLink) | **Not enforced** |
| `together_ai` | httpx → api.together.ai | API key | No | **Not enforced** |
| `ollama` | httpx → localhost:11434 | None | No | **Not enforced** |
| `openai_compatible` | httpx → user-specified URL | API key | No | **Not enforced** |

---

## 3. Compliance Status Matrix

| Requirement (from Bedrock Security Assessment) | Status | Severity | Details |
|---|---|---|---|
| Zero data retention | PASS (with production mode) | ~~HIGH~~ RESOLVED | Bedrock: PASS. Production mode (P1-1) prevents Claude CLI usage. In development mode, Claude CLI is still allowed. |
| Training opt-out default | PASS (with production mode) | ~~MEDIUM~~ RESOLVED | Bedrock: PASS. Production mode prevents Claude CLI usage. |
| Data residency controls | PASS (with production mode) | ~~HIGH~~ RESOLVED | Bedrock: PASS (region-locked). Production mode prevents Claude CLI (no data residency guarantee). |
| Private networking / VPC / PrivateLink | UNKNOWN / REQUIRES INFRASTRUCTURE VALIDATION | HIGH | Documented in presets but no VPC configuration exists in the repository. Infrastructure-side requirement. |
| API key scope isolation | CONDITIONAL PASS | MEDIUM | Bedrock IAM: PASS. API key value correctly excluded from `ProviderConfig` but retrieved from env at build time. |
| Auditability (CloudTrail) | UNKNOWN / REQUIRES INFRASTRUCTURE VALIDATION | MEDIUM | Not configured; infrastructure-side requirement. |
| Structured outputs/function support | PASS | — | Bedrock Converse tool calling implemented and tested. |
| Model routing transparency | PASS | — | Explicit model IDs; no opaque routing. |
| Contractual DPA availability | UNKNOWN / REQUIRES INFRASTRUCTURE VALIDATION | MEDIUM | AWS Artifact; operational/policy-side requirement. |
| GDPR posture | UNKNOWN / REQUIRES INFRASTRUCTURE VALIDATION | MEDIUM | Requires region selection, DPA execution, and data processing records. |
| Data outflow prevention | RESOLVED (production mode) | ~~CRITICAL~~ RESOLVED | `ORCHESTRATOR_PRODUCTION_MODE=true` rejects all non-production backends (claude_cli, together_ai, ollama, openai_compatible). Semantic dispatch routes through configured backend. Default claude_cli fails closed in production mode. (Phase 1 — P1-1, P1-2, P1-3) |
| Fail-closed on backend unavailability | PASS | — | Transport errors propagate as SkillResult failures; no silent fallback between backends. |
| Sandbox enforcement (TAPM) | PASS | — | Path authorization, symlink escape protection, declared-input boundary, read-only tools. Tested. |
| Prompt retention prevention | FAIL | HIGH | Full prompts and LLM responses written to `.claude/skill_diag/` and `.claude/semantic_diag/` as diagnostic files. |
| Secret handling | PARTIALLY RESOLVED | HIGH | AWS credentials in `.env` (DEFERRED — operational: P0-2 credential rotation). `.gitignore` expanded to ~40 entries covering `.claude/` runtime dirs, `__pycache__/`, caches, logs, IDE, OS files (RESOLVED — P0-1). Previously-tracked `.claude/benchmark/`, `.claude/runs/`, `.claude/skill_diag/`, and `__pycache__/` files removed from git index. |
| Production backend enforcement | RESOLVED | ~~CRITICAL~~ RESOLVED | `ORCHESTRATOR_PRODUCTION_MODE=true` enforces `PRODUCTION_BACKENDS` (bedrock_converse, bedrock). Preset `production_suitable` flag checked at runtime. Non-production backends rejected with clear error. 34 security tests verify enforcement. (Phase 1 — P1-1, P1-2, P1-5) |
| Logging safety | CONDITIONAL PASS | MEDIUM | Prompts not logged via `logging` module. But diagnostic files on disk contain full prompts. |
| Token telemetry safety | PASS | — | Benchmark hook captures char counts only; prompt content is never captured. |
| CI/CD security validation | PARTIALLY RESOLVED | ~~HIGH~~ MEDIUM | No CI/CD pipeline yet (P2-4 deferred — requires GitHub Actions setup). Pre-commit secret scanning hook added (P2-5). 39 sandbox hardening tests added. |
| Path resolution testing | RESOLVED | ~~MEDIUM~~ RESOLVED | `tests/test_paths.py` added with 17 tests covering `find_repo_root()` and `resolve_repo_path()`: subdirectory discovery, missing markers, double-marker requirement, max depth, symlink traversal, path normalization, absolute/relative handling. (Phase 2 — P2-6) |

---

## 4. Repository-Wide Threat Surface Analysis

### 4.1 Data Egress Paths

| Path | Risk | Current State |
|------|------|---------------|
| Claude CLI subprocess | **CRITICAL** — prompts sent to Anthropic infrastructure | Default backend; no production enforcement |
| bedrock-mantle HTTP endpoint | MEDIUM — traverses public internet unless PrivateLink configured | Supported; TLS enforced by httpx default |
| Bedrock Converse (boto3) | LOW — native AWS SDK; supports PrivateLink | Supported; IAM auth |
| Together AI HTTP endpoint | HIGH — third-party US-based service; no DPA | Supported; no production block |
| Ollama localhost | LOW — local only | Supported |
| Generic OpenAI-compatible | HIGH — arbitrary endpoint; no TLS enforcement | Supported; no production block |
| Diagnostic files on disk | HIGH — full prompt/response content written to `.claude/skill_diag/` | Active in all modes |

### 4.2 Secret Exposure Surfaces

| Surface | Risk | File(s) |
|---------|------|---------|
| `.env` file | CRITICAL — contains AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, CONTEXT7_API_KEY | `.env` (gitignored but not rotated) |
| `.claude/` diagnostic directories | MITIGATED (gitignored) — was HIGH, now covered by `.gitignore` expansion (P0-1) | `.claude/skill_diag/*`, `.claude/semantic_diag/*` |
| `.gitignore` incompleteness | RESOLVED — expanded to ~40 entries (P0-1) | `.gitignore` |
| `load_dotenv()` at module import | MEDIUM — credentials loaded into process env at import time | `runner/transport/config.py:50`, `runner/__main__.py:28` |

---

## 5. Confirmed Compliant Components

| Component | File(s) | Finding |
|-----------|---------|---------|
| **TAPM Sandbox** | `runner/transport/tool_executor.py` | Path authorization via `is_within()` using `Path.resolve().relative_to()` (not string prefix). Symlink escape detected. Read-only (no Write/Edit tools). Per-file 500KB and total 5MB read budgets. Tests cover traversal, symlink escape, outside-repo, and budget enforcement. **PASS** |
| **Tool Loop Safety** | `runner/transport/tool_loop.py` | Max-rounds guard (25). Unknown tool names produce structured errors. Malformed arguments produce errors. Never writes to filesystem. Timeout enforcement. **PASS** |
| **Bedrock Converse Backend** | `runner/transport/bedrock_converse.py` | Native boto3 `converse()` API. IAM auth via standard AWS credential chain. Proper error classification (auth, rate-limit, validation, server). No retries (max_attempts=0). **PASS** |
| **Atomic File Writes** | `runner/skill_runtime.py:_atomic_write()` | Write-to-temp then atomic move. Read-back validation. Never leaves partial writes. **PASS** |
| **Transport Error Propagation** | `runner/claude_transport.py`, `runner/skill_runtime.py` | `shell=False` in subprocess. All exceptions typed and propagated. No silent retry or fallback between backends. **PASS** |
| **Benchmark Telemetry** | `runner/benchmark/transport_hook.py` | Character counts only; prompt content explicitly never captured. Falls through to plain transport when disabled. **PASS** |
| **API Key Non-Persistence** | `runner/transport/config.py:ProviderConfig` | `api_key_set: bool` stored; actual key value excluded from dataclass. Retrieved from env only at backend build time. **PASS** |
| **Bedrock Model ID Validation** | `runner/transport/config.py:validate_bedrock_model_id()` | Regex validation of `<provider>.<model>` format. **PASS** |

---

## 6. Conditional-Pass Components

### 6.1 Backend Selection Architecture

**Status:** CONDITIONAL PASS
**Severity:** CRITICAL
**Files:** `runner/transport/config.py:477`, `runner/skill_runtime.py:1262`

**Finding:** The `TransportPreset.production_suitable` flag exists on all 7 presets but is **never checked at runtime**. The default backend is `claude_cli` (line 477: `os.environ.get("ORCHESTRATOR_TRANSPORT_BACKEND", "claude_cli")`). Any of the 6 registered backends is accepted without restriction. There is no mechanism to enforce Bedrock-only operation in production.

**Risk:** An operator forgetting to set `ORCHESTRATOR_TRANSPORT_PRESET` or `ORCHESTRATOR_TRANSPORT_BACKEND` will route all proposal IP through Anthropic infrastructure (Claude CLI) instead of Bedrock.

**Classification:** Configuration-level issue.

**Remediation (repository-side):**
- Add a `ORCHESTRATOR_PRODUCTION_MODE=true` env var that, when set, rejects any backend where `production_suitable=False`.
- Change default backend from `claude_cli` to require explicit selection (fail-closed when unset in production mode).
- Log a WARNING at startup when `production_suitable=False` backends are in use.

### 6.2 Semantic Dispatch Transport

**Status:** CONDITIONAL PASS
**Severity:** HIGH
**Files:** `runner/semantic_dispatch.py:57`, `runner/semantic_dispatch.py:646-654`

**Finding:** Semantic dispatch uses `invoke_claude_text()` via the benchmark transport hook, which currently always routes through the Claude CLI transport (`runner/claude_transport.py:invoke_claude_text()`). Semantic predicates do NOT use the multi-backend resolution path — they are hardcoded to the Claude CLI regardless of `ORCHESTRATOR_TRANSPORT_BACKEND`.

**Risk:** Even when Bedrock is configured as the skill backend, all semantic predicate evaluations (7 predicates, invoked per gate evaluation) still route through Anthropic infrastructure. This is a hidden egress path.

**Classification:** Architectural issue.

**Remediation (repository-side):**
- Route semantic dispatch through the same backend resolution as skills.
- Or add a `ORCHESTRATOR_SEMANTIC_BACKEND` override that defaults to the skill backend.

### 6.3 Data Residency via AWS Region

**Status:** CONDITIONAL PASS
**Severity:** MEDIUM
**Files:** `runner/transport/config.py:73-74`, `runner/transport/config.py:558`

**Finding:** AWS region defaults to `eu-west-1` for bedrock-mantle and `us-east-1` for bedrock_converse. Region is configurable via `AWS_REGION` env var. No validation ensures the selected region is an EU region (for GDPR compliance) or that the model is available in that region.

**Classification:** Configuration-level issue.

**Remediation (operational/policy-side):**
- Document required region for institutional deployment.
- Optionally: add `ORCHESTRATOR_ALLOWED_REGIONS` enforcement for production mode.

---

## 7. Non-Compliant or Unresolved Areas

### 7.1 CRITICAL: Default Backend is Claude CLI

**Severity:** CRITICAL
**Files:** `runner/transport/config.py`
**Risk:** Production egress of proposal IP through Anthropic infrastructure.
**Status:** RESOLVED (Phase 1 — P1-1, P1-2, 2026-05-28)

When `ORCHESTRATOR_PRODUCTION_MODE=true`, the default `claude_cli` backend is rejected with a clear error message. Production mode requires explicit selection of a production-suitable backend (`bedrock_converse` or `bedrock`). Development mode behavior is unchanged — `claude_cli` remains the default when production mode is not set.

Additionally, `__main__.py` now logs the resolved backend at DAG startup (P1-4) and returns exit code 3 on transport configuration errors, providing immediate visibility into the active backend.

**Remediation:** Complete.

### 7.2 CRITICAL: No Runtime Production Backend Enforcement

**Severity:** CRITICAL
**Files:** `runner/transport/config.py`
**Risk:** Non-Bedrock backends accepted in production without warning.
**Status:** RESOLVED (Phase 1 — P1-1, P1-2, 2026-05-28)

`ORCHESTRATOR_PRODUCTION_MODE=true` now enforces `PRODUCTION_BACKENDS` (`bedrock_converse`, `bedrock`). The `production_suitable` flag on `TransportPreset` is checked at runtime during preset resolution — non-production presets are rejected in production mode. Both the preset path and the legacy direct-env-var path enforce the restriction. 34 security tests verify all enforcement paths.

**Remediation:** Complete.

### 7.3 CRITICAL: Semantic Dispatch Bypasses Backend Selection

**Severity:** CRITICAL
**Files:** `runner/semantic_dispatch.py`
**Risk:** Hidden data egress through Claude CLI even when Bedrock is configured for skills.
**Status:** RESOLVED (Phase 1 — P1-3, 2026-05-28)

Semantic dispatch now resolves the transport backend via `resolve_provider_config()` — the same path used by the skill runtime. When `bedrock_converse` is configured, semantic predicate evaluation routes through the native Bedrock Converse backend. When `bedrock` (mantle) or other OpenAI-compatible backends are configured, semantic dispatch routes through `build_openai_backend()`. The `claude_cli` path is preserved only when explicitly selected (development mode). Production-mode enforcement applies equally to semantic predicates — no hidden egress paths remain.

**Remediation:** Complete.

### 7.4 HIGH: Full Prompt/Response Content Written to Disk

**Severity:** HIGH
**Files:**
- `runner/skill_runtime.py:1710-1748` — diagnostic capture writes full response text
- `runner/skill_runtime.py:838-940` — transport failure diagnostics write full system+user prompts
- `runner/semantic_dispatch.py:316-396` — semantic diagnostics write full prompts and responses
**Output paths:** `.claude/skill_diag/`, `.claude/semantic_diag/`
**Risk:** Proposal IP (full proposal content, project data, partner details, budget information) is persisted in plaintext diagnostic files after every skill invocation and every transport failure.
**Status:** FAIL

The skill runtime writes **every** LLM response to `{skill_id}_{run_id}_response.txt` at line 1714 as a "diagnostic capture (temporary)" — but there is no mechanism to remove these files. Transport failure diagnostics write full `system_prompt.txt` and `user_prompt.txt` files. These files contain the complete serialized proposal content.

**Remediation:** Repository-side.
- Remove the unconditional response diagnostic capture (lines 1710-1748), or gate it behind a `ORCHESTRATOR_DEBUG_DIAGNOSTICS=true` env var disabled by default.
- Ensure transport failure diagnostics either omit prompt content in production or are encrypted/auto-purged.

### 7.5 HIGH: `.gitignore` is Dangerously Minimal

**Severity:** HIGH
**File:** `.gitignore`
**Risk:** Accidental commit of secrets, diagnostics, cache, and proposal IP.
**Status:** RESOLVED (Phase 0 — P0-1, 2026-05-28)

`.gitignore` expanded from 2 entries to ~40 entries covering:
- `.claude/skill_diag/`, `.claude/semantic_diag/`, `.claude/runs/`, `.claude/logs/`, `.claude/cache/`, `.claude/benchmark/` (runtime/diagnostic state)
- `__pycache__/`, `*.py[cod]`, `*$py.class`, `*.egg-info/`, `dist/`, `build/`, `*.egg` (Python)
- `.venv/`, `venv/`, `env/` (virtual environments)
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `.coverage` (test/tooling caches)
- `*.log` (logs)
- `.idea/`, `.vscode/`, `*.swp`, `*.swo` (IDE)
- `.DS_Store`, `Thumbs.db` (OS)

Constitutional configuration (`.claude/agents/`, `.claude/skills/`, `.claude/workflows/`) intentionally remains tracked. Previously-tracked runtime files (319 files across `.claude/benchmark/`, `.claude/runs/`, `.claude/skill_diag/`, `__pycache__/`) removed from git index via `git rm --cached`.

**Remediation:** Complete.

### 7.6 HIGH: No CI/CD Pipeline

**Severity:** HIGH
**File:** (absent — no `.github/workflows/` directory)
**Risk:** No automated security validation, no pre-commit secret scanning, no test enforcement.
**Status:** FAIL

With 95 test files and 1600+ tests, the test suite is comprehensive. But there is no CI pipeline to run these tests automatically. Security-critical tests (sandbox, path traversal, symlink escape) exist but are only validated manually.

**Remediation:** Deployment-side.
- Create a CI pipeline that runs the full test suite on every push/PR.
- Add pre-commit hooks for secret scanning (e.g. `detect-secrets`, `trufflehog`).
- Add a production-backend validation test that asserts `claude_cli` is not the active backend.

### 7.7 MEDIUM: `runner/paths.py` Has Zero Dedicated Tests

**Severity:** MEDIUM
**File:** `runner/paths.py` (83 lines, 2 functions)
**Risk:** Path resolution is security-foundational but untested.
**Status:** RESOLVED (Phase 2 — P2-6, 2026-05-28)

`tests/test_paths.py` created with 17 tests covering:
- `find_repo_root()`: subdirectory discovery, root-itself, missing markers (CLAUDE.md only, .git only), both-marker requirement, filesystem root stop, 20-level max depth, symlink traversal (returns resolved path), absolute path guarantee, .git-as-file (worktree) support
- `resolve_repo_path()`: absolute unchanged, relative joined, relative without root, forward-slash normalization on all platforms, Path object input, `../` traversal in relative paths, absolute ignores repo_root

**Remediation:** Complete.

### 7.8 MEDIUM: AWS Credentials in `.env`

**Severity:** MEDIUM (mitigated by `.env` being gitignored)
**File:** `.env:9-10`
**Risk:** Credential exposure if `.env` is inadvertently shared, copied, or committed to a fork.
**Status:** FAIL

The `.env` file contains plaintext `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` for an IAM user. While this is gitignored and was never committed, it is a credential management risk for production deployment.

**Remediation:** Operational/policy-side.
- Rotate the exposed credentials immediately.
- Use IAM roles / instance profiles for production instead of long-term access keys.
- Use AWS Secrets Manager or SSM Parameter Store for credential injection.

---

## 8. Hidden Egress Risk Analysis

| Egress Path | Trigger | Data Exposed | Severity |
|---|---|---|---|
| Claude CLI (default backend) | Missing/empty `ORCHESTRATOR_TRANSPORT_BACKEND` | Full prompts + proposal content | CRITICAL |
| Claude CLI (semantic dispatch) | Always active regardless of backend config | Semantic predicate evaluation prompts + artifact content | CRITICAL |
| Together AI endpoint | `ORCHESTRATOR_TRANSPORT_BACKEND=together_ai` | Full prompts + proposal content | HIGH |
| Generic OpenAI-compatible | `ORCHESTRATOR_TRANSPORT_BACKEND=openai_compatible` with arbitrary endpoint | Full prompts to arbitrary URL | HIGH |
| Diagnostic files on disk | Every skill invocation | Full LLM responses (proposal sections, analysis) | HIGH |
| Transport failure diagnostics | Any transport error | Full system+user prompts (serialized proposal data) | HIGH |
| `.claude/` directory | Accidental git add | Diagnostics, run records, agent memory | HIGH |

---

## 9. AWS-Side Required Controls

| Control | Requirement | Status | Remediation |
|---------|-------------|--------|-------------|
| VPC Endpoint (PrivateLink) for Bedrock | Mandatory for closed-network operation | **Not configured** | Create VPC interface endpoint for `bedrock-runtime` service. Verify with `aws ec2 describe-vpc-endpoints`. |
| CloudTrail logging for Bedrock API calls | Mandatory for auditability | **Not configured** | Enable CloudTrail trail covering Bedrock service events. |
| IAM policy scoped to Bedrock models | Mandatory for least-privilege | **Unknown** | Create IAM policy with `bedrock:InvokeModel` scoped to specific model ARNs and regions. |
| Region enforcement via IAM condition | Recommended for data residency | **Not configured** | Add `aws:RequestedRegion` condition key to IAM policies. |
| CloudWatch opt-in logging | Assessment required | **Unknown** | Verify CloudWatch is NOT configured to log prompts/completions (default: off). Document the decision. |
| GDPR DPA execution | Mandatory for EU institutional | **Not executed** | Download and execute via AWS Artifact. |
| Model availability validation | Required pre-deployment | **Not validated** | Confirm target model is available in selected region via Bedrock console. |

---

## 10. Repository-Side Required Controls

| Control | Current State | Required Change | Priority |
|---------|---------------|-----------------|----------|
| Production backend enforcement | RESOLVED (P1-1, P1-2) — `ORCHESTRATOR_PRODUCTION_MODE=true` enforces `PRODUCTION_BACKENDS` | N/A | ~~CRITICAL~~ RESOLVED |
| Default backend fail-closed | RESOLVED (P1-1) — claude_cli rejected in production mode | N/A | ~~CRITICAL~~ RESOLVED |
| Semantic dispatch backend routing | RESOLVED (P1-3) — routes through `resolve_provider_config()` | N/A | ~~CRITICAL~~ RESOLVED |
| Diagnostic prompt capture | Always-on, writes full content | Disable by default; gate behind debug flag | HIGH |
| `.gitignore` completeness | RESOLVED (P0-1) — expanded to ~40 entries | N/A | ~~HIGH~~ RESOLVED |
| Transport failure prompt sanitization | Full prompts written to disk | Truncate or omit prompt content in production mode | HIGH |
| Secret detection pre-commit | RESOLVED (P2-5) — `.pre-commit-config.yaml` with detect-secrets, private-key detection, large-file guard | N/A | ~~MEDIUM~~ RESOLVED |

---

## 11. Mandatory Fail-Closed Requirements

| Requirement | Current Behavior | Required Behavior |
|---|---|---|
| Missing backend configuration | Silently defaults to `claude_cli` | FAIL with clear error message in production mode |
| `production_suitable=False` backend in production mode | Accepted without warning | REJECT with explanation of which backends are production-suitable |
| Missing AWS credentials for Bedrock Converse | boto3 raises `NoCredentialsError` | Already fail-closed (PASS) |
| Missing API key for bedrock-mantle | `ValueError` raised in `_resolve_bedrock()` | Already fail-closed (PASS) |
| Transport error (any backend) | SkillResult(status="failure") propagated | Already fail-closed (PASS) |
| Sandbox path violation (TAPM) | Structured error returned to LLM | Already fail-closed (PASS) |
| Symlink escape (TAPM) | Access denied | Already fail-closed (PASS) |
| Malformed LLM response | SkillResult(status="failure", category="INCOMPLETE_OUTPUT") | Already fail-closed (PASS) |

---

## 12. Logging and Telemetry Analysis

### 12.1 Python Logging Module

| Logger | Level | Content | Prompt Data? |
|--------|-------|---------|-------------|
| `runner.skill_runtime` | INFO | Skill ID, mode, prompt char counts, elapsed time | **No** |
| `runner.semantic_dispatch` | (none configured) | N/A | **No** |
| `runner.transport.bedrock_converse` | (module-level) | Error messages | **No** |
| `runner.transport.openai_compatible` | (module-level) | Error messages | **No** |
| `runner.scheduler` | DEBUG/WARNING | Node states, gate results | **No** |

**Verdict:** Python logging is clean — no prompt content logged. **PASS**

### 12.2 Disk Persistence

| Path | Content | Prompt Data? | Severity |
|------|---------|-------------|----------|
| `.claude/skill_diag/{skill}_{run}_response.txt` | Full LLM response text | **YES** | HIGH |
| `.claude/skill_diag/{skill}_{run}_parsed.txt` | Parsed JSON output (truncated to 5KB) | **YES** | MEDIUM |
| `.claude/skill_diag/{skill}_{run}_phase_e.txt` | Phase E diagnostic state | **No** | LOW |
| `.claude/skill_diag/{skill}_{run}_system_prompt.txt` | Full system prompt (on transport failure) | **YES** | HIGH |
| `.claude/skill_diag/{skill}_{run}_user_prompt.txt` | Full user prompt (on transport failure) | **YES** | HIGH |
| `.claude/skill_diag/{skill}_{run}_transport_diag.json` | Transport failure metadata (no content) | **No** | LOW |
| `.claude/semantic_diag/{func}_{run}_system_prompt.txt` | Semantic system prompt (on failure) | **YES** (artifact content) | HIGH |
| `.claude/semantic_diag/{func}_{run}_user_prompt.txt` | Semantic user prompt (on failure) | **YES** (artifact content) | HIGH |
| `.claude/semantic_diag/{func}_{run}_response.txt` | Semantic response (on failure) | **YES** | HIGH |

**Verdict:** Disk diagnostics contain full proposal IP. **FAIL**

### 12.3 Benchmark Telemetry

| Data | Captured? | Persisted? | Content? |
|------|-----------|------------|----------|
| System prompt char count | Yes | In-memory ledger | No |
| User prompt char count | Yes | In-memory ledger | No |
| Response char count | Yes | In-memory ledger | No |
| Prompt content | **Never** | — | — |
| Response content | **Never** | — | — |
| Wall clock timing | Yes | In-memory ledger | No |
| Model identifier | Yes | In-memory ledger | No |
| Error class/message | Yes (truncated to 500 chars) | In-memory ledger | Partial (error messages only) |

**Verdict:** Benchmark telemetry is clean. **PASS**

---

## 13. Production Deployment Requirements

### 13.1 Environment Configuration

```bash
# MANDATORY for production
ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US  # or BEDROCK_EU_PRODUCTION
ORCHESTRATOR_TRANSPORT_MODEL=us.anthropic.claude-sonnet-4-6
AWS_REGION=eu-west-1  # or target EU region

# MANDATORY if using bedrock-mantle (not needed for bedrock_converse)
ORCHESTRATOR_TRANSPORT_API_KEY=<bedrock-api-key>

# RECOMMENDED for production enforcement (requires code change)
ORCHESTRATOR_PRODUCTION_MODE=true

# MUST NOT be set in production
# ORCHESTRATOR_TRANSPORT_BACKEND=claude_cli
# ORCHESTRATOR_TRANSPORT_BACKEND=together_ai
# ORCHESTRATOR_TRANSPORT_BACKEND=ollama
# ORCHESTRATOR_TRANSPORT_BACKEND=openai_compatible
```

### 13.2 AWS Infrastructure

1. VPC with PrivateLink endpoint for Bedrock
2. IAM role with `bedrock:InvokeModel` scoped to target model ARNs and region
3. CloudTrail trail for Bedrock API events
4. CloudWatch verified to NOT log prompt content (opt-in logging disabled)
5. GDPR DPA executed via AWS Artifact

### 13.3 Deployment Host

1. `.env` file with production credentials injected via secrets manager (not plaintext)
2. Diagnostic directories (`.claude/skill_diag/`, `.claude/semantic_diag/`) either:
   - Disabled via `ORCHESTRATOR_DEBUG_DIAGNOSTICS=false`, or
   - Mounted on encrypted ephemeral storage with auto-purge
3. No Claude CLI binary installed (removes fallback risk entirely)
4. Network egress restricted to VPC PrivateLink endpoint only

---

## 14. CI/CD Security Requirements

| Requirement | Implementation |
|-------------|---------------|
| Full test suite execution | GitHub Actions or equivalent, triggered on push and PR |
| Secret scanning | `detect-secrets` pre-commit hook + CI check |
| Backend restriction test | Assert `resolve_provider_config()` rejects `claude_cli` when `ORCHESTRATOR_PRODUCTION_MODE=true` |
| Sandbox security tests | Run `test_transport_tool_executor.py` tests (path traversal, symlink escape, budget limits) |
| Dependency audit | `pip-audit` or `safety` check for known CVEs in `boto3`, `httpx`, `pyyaml` |
| `.gitignore` validation | CI check that `.claude/`, `__pycache__/`, `.env` are not tracked |
| Credential rotation | Automated rotation of AWS access keys (max 90-day lifetime) |

---

## 15. Required Code Modifications

### 15.1 Production Backend Enforcement (CRITICAL) — RESOLVED

**File:** `runner/transport/config.py`
**Status:** RESOLVED (Phase 1 — P1-1, P1-2, 2026-05-28). `is_production_mode()`, `PRODUCTION_BACKENDS`, `_enforce_production_backend()` added. Both `resolve_provider_config()` and `resolve_provider_config_from_preset()` enforce production restrictions. 34 security tests in `tests/test_production_mode.py`.

### 15.2 Semantic Dispatch Backend Routing (CRITICAL) — RESOLVED

**File:** `runner/semantic_dispatch.py`
**Status:** RESOLVED (Phase 1 — P1-3, 2026-05-28). `_resolve_semantic_backend()` and `_invoke_via_backend()` route semantic predicates through `resolve_provider_config()`. Bedrock Converse and OpenAI-compatible paths added alongside existing Claude CLI path.

### 15.3 Diagnostic Capture Gating (HIGH)

**File:** `runner/skill_runtime.py`
**Change:** Gate the unconditional response diagnostic capture (lines 1710-1748) behind `ORCHESTRATOR_DEBUG_DIAGNOSTICS=true`. Default to disabled.

### 15.4 Transport Failure Prompt Sanitization (HIGH)

**Files:** `runner/skill_runtime.py:838-940`, `runner/semantic_dispatch.py:316-396`
**Change:** In production mode, write only metadata (char counts, error details) to diagnostic files. Omit full prompt/response text.

### 15.5 `.gitignore` Expansion (HIGH) — RESOLVED

**File:** `.gitignore`
**Status:** RESOLVED (Phase 0 — P0-1, 2026-05-28). Expanded to ~40 entries. Previously-tracked runtime files removed from git index. See Section 7.5 for details.

---

## 16. Required Infrastructure Modifications

| Modification | Owner | Priority |
|---|---|---|
| Create VPC PrivateLink endpoint for Bedrock | AWS account administrator | CRITICAL |
| Create scoped IAM role for Bedrock | AWS account administrator | CRITICAL |
| Enable CloudTrail for Bedrock | AWS account administrator | HIGH |
| Configure network egress restrictions | Infrastructure/networking team | HIGH |
| Set up AWS Secrets Manager for credential injection | DevOps | MEDIUM |
| Execute GDPR DPA via AWS Artifact | Institutional compliance officer | MEDIUM |
| Validate model availability in target region | DevOps | MEDIUM |

---

## 17. Required Test Coverage Additions

| Test | Purpose | Priority |
|------|---------|----------|
| `test_production_mode_rejects_claude_cli` | Verify production mode blocks `claude_cli` default | CRITICAL |
| `test_production_mode_rejects_non_production_backends` | Verify Together AI, Ollama, generic rejected in production | CRITICAL |
| `test_semantic_dispatch_uses_configured_backend` | Verify semantic dispatch respects `ORCHESTRATOR_TRANSPORT_BACKEND` | CRITICAL |
| `test_diagnostic_capture_disabled_by_default` | Verify no prompt content written without debug flag | HIGH |
| `test_diagnostic_capture_production_sanitization` | Verify production mode omits prompt content from failure diagnostics | HIGH |
| `test_gitignore_covers_sensitive_paths` | Validate `.gitignore` includes `.claude/` and standard patterns | MEDIUM |
| `test_no_secrets_in_tracked_files` | Scan tracked files for credential patterns | MEDIUM |
| `test_find_repo_root_symlink_traversal` | Verify `find_repo_root()` is not tricked by symlink chains | MEDIUM |
| `test_resolve_repo_path_traversal` | Verify `../` sequences in paths don't escape repo root | MEDIUM |
| `test_find_repo_root_missing_markers` | Verify `RuntimeError` when CLAUDE.md/.git absent | MEDIUM |
| `test_bedrock_converse_iam_auth_required` | Verify Bedrock Converse fails without IAM credentials | LOW (already covered by boto3) |

---

## 18. Final Compliance Verdict

### Overall Status: **CONDITIONAL PASS — NOT PRODUCTION-READY**

The Proposal Orchestrator has strong security fundamentals:
- Well-designed TAPM sandbox with path authorization and symlink escape protection
- Fail-closed transport error semantics
- Atomic file writes
- Clean benchmark telemetry (no prompt capture)
- API key non-persistence in configuration objects
- Native Bedrock Converse support via boto3

All **three CRITICAL issues** identified in the original audit have been resolved by Phase 1:

1. ~~**Default backend is `claude_cli`**~~ **RESOLVED** — Production mode rejects `claude_cli` and all non-production backends.
2. ~~**No production backend enforcement**~~ **RESOLVED** — `PRODUCTION_BACKENDS` enforced at runtime. `production_suitable` flag checked for presets.
3. ~~**Semantic dispatch bypasses backend selection**~~ **RESOLVED** — Routes through `resolve_provider_config()`. No hidden Claude CLI paths in production mode.

Additionally, **three remaining HIGH-severity issues** require remediation (one HIGH resolved in Phase 0):

4. **Full prompt/response content persisted to disk** in diagnostic files. (TEMPORARILY ACCEPTED — RA-01 through RA-04, pending Phase 3 gate prerequisites)
5. ~~**`.gitignore` covers only 2 patterns** — sensitive directories at risk of accidental commit.~~ **RESOLVED** (Phase 0 — P0-1, 2026-05-28). `.gitignore` expanded to ~40 entries. Previously-tracked runtime files removed from git index.
6. **No CI/CD pipeline** — security tests are not automated. (DEFERRED — Phase 2, P2-4)
7. **AWS credentials in plaintext `.env`** — operational credential management risk. (DEFERRED — Phase 0 operational item P0-2: credential rotation is non-repository-side)

### Production Sign-Off Criteria

All of the following must be satisfied before institutional production deployment:

- [x] Production backend enforcement code implemented and tested (RESOLVED — Phase 1, P1-1/P1-2)
- [x] Semantic dispatch routed through multi-backend config (RESOLVED — Phase 1, P1-3)
- [ ] Diagnostic prompt capture disabled by default (or production-sanitized)
- [x] `.gitignore` expanded to cover `.claude/` and standard patterns (RESOLVED — Phase 0, P0-1)
- [ ] CI/CD pipeline created with full test suite execution (DEFERRED — P2-4 requires GitHub Actions setup)
- [x] Secret scanning pre-commit hook installed (RESOLVED — Phase 2, P2-5)
- [ ] AWS VPC PrivateLink endpoint configured for Bedrock
- [ ] IAM role scoped to target models and regions
- [ ] CloudTrail enabled for Bedrock API events
- [ ] GDPR DPA executed via AWS Artifact
- [ ] AWS credentials rotated and managed via Secrets Manager or IAM roles
- [ ] Deployment host configured with no Claude CLI binary installed
- [ ] Network egress restricted to VPC PrivateLink endpoint
- [ ] All CRITICAL and HIGH test coverage additions implemented and passing

---

---

## 19. Phase 0 Remediation Record

**Date:** 2026-05-28
**Scope:** Phase 0 (Immediate Hygiene) from `security_hardening_implementation_plan.md`

### Implemented

| Item | Status | Details |
|------|--------|---------|
| P0-1 | RESOLVED | `.gitignore` expanded from 2 to ~40 entries. 319 previously-tracked runtime files (`benchmark/`, `runs/`, `skill_diag/`, `__pycache__/`) removed from git index. Constitutional dirs (`agents/`, `skills/`, `workflows/`) remain tracked. |
| P0-3 | RESOLVED | `.env.example` updated with `ORCHESTRATOR_PRODUCTION_MODE` documentation, security warnings for credential handling, and production-mode guidance. |

### Deferred (Operational — Non-Repository-Side)

| Item | Status | Reason |
|------|--------|--------|
| P0-2 | DEFERRED | AWS credential rotation is an operational/AWS IAM console task, not a repository-side change. Must be performed by AWS account administrator. |

### Findings Status After Phase 0

| Finding | Original Severity | Status After Phase 0 |
|---------|------------------|---------------------|
| 7.1 Default backend is Claude CLI | CRITICAL | UNRESOLVED — requires Phase 1 (P1-1) |
| 7.2 No production backend enforcement | CRITICAL | UNRESOLVED — requires Phase 1 (P1-2) |
| 7.3 Semantic dispatch bypasses backend | CRITICAL | UNRESOLVED — requires Phase 1 (P1-3) |
| 7.4 Full prompt/response on disk | HIGH | TEMPORARILY ACCEPTED (RA-01–RA-04) — deferred to Phase 3 |
| 7.5 `.gitignore` minimal | HIGH | RESOLVED (P0-1) |
| 7.6 No CI/CD pipeline | HIGH | UNRESOLVED — requires Phase 2 (P2-4) |
| 7.7 `runner/paths.py` untested | MEDIUM | UNRESOLVED — requires Phase 2 (P2-6) |
| 7.8 AWS credentials in `.env` | MEDIUM | DEFERRED (P0-2 operational) |

---

## 20. Phase 1 Remediation Record

**Date:** 2026-05-28
**Scope:** Phase 1 (Transport Lockdown) from `security_hardening_implementation_plan.md`

### Implemented

| Item | Status | Details |
|------|--------|---------|
| P1-1 | RESOLVED | `ORCHESTRATOR_PRODUCTION_MODE` env var guard. `is_production_mode()` helper. Production mode rejects all non-production backends in both legacy and preset resolution paths. |
| P1-2 | RESOLVED | `PRODUCTION_BACKENDS` constant (`bedrock_converse`, `bedrock`). `_enforce_production_backend()` function. Preset `production_suitable` flag checked at runtime. |
| P1-3 | RESOLVED | `_resolve_semantic_backend()` and `_invoke_via_backend()` added to `semantic_dispatch.py`. Semantic predicates now route through `resolve_provider_config()`. Bedrock Converse, OpenAI-compatible, and Claude CLI paths all supported. |
| P1-4 | RESOLVED | `__main__.py` logs resolved backend, model, preset, and production mode at DAG startup. Returns exit code 3 on transport configuration errors. |
| P1-5 | RESOLVED | 34 security tests in `tests/test_production_mode.py`: production enforcement (11 tests), development preservation (5 tests), `is_production_mode()` (5 tests), `PRODUCTION_BACKENDS` (7 tests), semantic dispatch routing (3 tests), fail-closed behavior (2 tests), startup logging (1 test). |

### Findings Status After Phase 1

| Finding | Original Severity | Status After Phase 1 |
|---------|------------------|---------------------|
| 7.1 Default backend is Claude CLI | CRITICAL | RESOLVED (P1-1) |
| 7.2 No production backend enforcement | CRITICAL | RESOLVED (P1-1, P1-2) |
| 7.3 Semantic dispatch bypasses backend | CRITICAL | RESOLVED (P1-3) |
| 7.4 Full prompt/response on disk | HIGH | TEMPORARILY ACCEPTED (RA-01–RA-04) — deferred to Phase 3 |
| 7.5 `.gitignore` minimal | HIGH | RESOLVED (P0-1) |
| 7.6 No CI/CD pipeline | HIGH | UNRESOLVED — requires Phase 2 (P2-4) |
| 7.7 `runner/paths.py` untested | MEDIUM | UNRESOLVED — requires Phase 2 (P2-6) |
| 7.8 AWS credentials in `.env` | MEDIUM | DEFERRED (P0-2 operational) |

### CRITICAL Findings: None remaining

All three CRITICAL findings (7.1, 7.2, 7.3) are resolved. No CRITICAL findings remain.

### HIGH Findings: 3 remaining

- 7.4 (diagnostic persistence) — TEMPORARILY ACCEPTED, deferred to Phase 3
- 7.6 (no CI/CD pipeline) — Phase 2
- Secret handling (P0-2 credential rotation) — operational, deferred

---

---

## 21. Phase 2 Remediation Record

**Date:** 2026-05-28
**Scope:** Phase 2 (Infrastructure and Compliance — repository-side items) from `security_hardening_implementation_plan.md`

### Implemented (Repository-Side)

| Item | Status | Details |
|------|--------|---------|
| P2-5 | RESOLVED | `.pre-commit-config.yaml` created with: `detect-secrets` v1.5.0 (credential detection), `detect-private-key` (private key detection), `check-added-large-files` (500KB limit), `check-merge-conflict`, `check-yaml`, `check-case-conflict`, `end-of-file-fixer`, `trailing-whitespace`. |
| P2-6 | RESOLVED | `tests/test_paths.py` created with 17 tests for `find_repo_root()` and `resolve_repo_path()`. Covers: subdirectory discovery, root-itself, missing markers, double-marker requirement, max depth (20 levels), symlink traversal, absolute path guarantee, .git-as-file (worktree), path normalization across platforms. |
| Sandbox hardening | RESOLVED | `tests/test_sandbox_hardening.py` created with 39 tests. Covers: path injection edge cases (empty/null/whitespace/integer/NUL), Windows reserved names, `../` traversal, glob injection, 11 dangerous tool rejections (Write/Edit/Bash/Delete/exec/subprocess/eval/WebFetch/WebSearch/NotebookEdit/os.system), case-sensitive tool names, tool loop max-rounds and timeout enforcement, malformed arguments, `shell=False` subprocess verification (source audit), declared-input boundary exhaustive checks, `is_within` edge cases. |

### Deferred (Non-Repository-Side)

| Item | Status | Reason |
|------|--------|--------|
| P2-1 | DEFERRED | VPC PrivateLink endpoint — AWS infrastructure, requires AWS admin. |
| P2-2 | DEFERRED | Scoped IAM role — AWS infrastructure, requires AWS admin. |
| P2-3 | DEFERRED | CloudTrail — AWS infrastructure, requires AWS admin. |
| P2-4 | DEFERRED | CI/CD pipeline — requires GitHub Actions setup (deployment-side). |
| P2-7 | DEFERRED | GDPR DPA — operational/legal, requires compliance officer. |
| P2-8 | DEFERRED | Model availability validation — operational, requires DevOps. |
| P2-9 | DEFERRED | CloudWatch prompt logging verification — AWS infrastructure. |

### Findings Status After Phase 2

| Finding | Original Severity | Status After Phase 2 |
|---------|------------------|---------------------|
| 7.1 Default backend is Claude CLI | CRITICAL | RESOLVED (P1-1) |
| 7.2 No production backend enforcement | CRITICAL | RESOLVED (P1-1, P1-2) |
| 7.3 Semantic dispatch bypasses backend | CRITICAL | RESOLVED (P1-3) |
| 7.4 Full prompt/response on disk | HIGH | TEMPORARILY ACCEPTED (RA-01–RA-04) — deferred to Phase 3 |
| 7.5 `.gitignore` minimal | HIGH | RESOLVED (P0-1) |
| 7.6 No CI/CD pipeline | HIGH | PARTIALLY RESOLVED — pre-commit hooks added (P2-5), CI/CD pipeline deferred (P2-4) |
| 7.7 `runner/paths.py` untested | MEDIUM | RESOLVED (P2-6) |
| 7.8 AWS credentials in `.env` | MEDIUM | DEFERRED (P0-2 operational) |
| Sandbox enforcement | N/A (audit) | PASS — 39 hardening tests confirm: tool rejection, path traversal prevention, symlink escape detection, declared-input enforcement, subprocess shell=False, tool loop bounds |

### CRITICAL Findings: None remaining

All three CRITICAL findings (7.1, 7.2, 7.3) were resolved in Phase 1. No new CRITICAL findings introduced.

### HIGH Findings: 2 remaining

- 7.4 (diagnostic persistence) — TEMPORARILY ACCEPTED, deferred to Phase 3
- 7.6 (CI/CD pipeline) — PARTIALLY RESOLVED (pre-commit hooks present; GitHub Actions pipeline deferred)

### MEDIUM Findings: 1 remaining

- 7.8 (AWS credentials in `.env`) — DEFERRED (operational)

---

*Document produced by security compliance audit, 2026-05-28. Phase 0 remediation record appended 2026-05-28. Phase 1 remediation record appended 2026-05-28. Phase 2 remediation record appended 2026-05-28. This is an assessment document, not a certification. Implementation of remediation steps is required before production deployment.*
