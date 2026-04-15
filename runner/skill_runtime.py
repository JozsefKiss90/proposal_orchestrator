"""
Skill runtime — Claude runtime transport adapter layer.

Loads a skill execution specification (``.claude/skills/<skill_id>.md``),
assembles prompt context from canonical inputs, invokes Claude through the
configured runtime transport (local ``claude`` CLI via
:func:`runner.claude_transport.invoke_claude_text`), parses the structured
JSON response, validates outputs against the expected schema, writes
canonical artifacts atomically, and returns a :class:`SkillResult`.

Skill ``.md`` files are **specifications, not executable code**.  Domain
reasoning is performed by Claude; this module handles prompt assembly,
transport invocation, response parsing, validation, and atomic I/O.

Follows the same architectural pattern as ``runner/semantic_dispatch.py``
``invoke_agent()`` but at runtime-integration scope — producing canonical
Tier 4/Tier 5 artifacts rather than predicate results.

Authoritative sources:
    runtime_integration_plan.md §7, §8, §10.2
    runtime_integration_execution_plan.md Step 4
    skill_runtime_contract.md §C.3–C.11
    skill_catalog.yaml (reads_from, writes_to, constitutional_constraints)

Constitutional authority:
    Subordinate to CLAUDE.md.  This module does not invoke other skills,
    does not invoke agents, does not evaluate gates, and does not compute
    budget figures.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Optional

import yaml

from runner.claude_transport import ClaudeTransportError, invoke_claude_text
from runner.runtime_models import SkillResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Repo-relative path to the skill catalog.
SKILL_CATALOG_REL_PATH: str = (
    ".claude/workflows/system_orchestration/skill_catalog.yaml"
)

#: Repo-relative path to the artifact schema specification.
ARTIFACT_SCHEMA_REL_PATH: str = (
    ".claude/workflows/system_orchestration/artifact_schema_specification.yaml"
)

#: Repo-relative directory containing skill specification files.
SKILL_SPECS_REL_DIR: str = ".claude/skills"

#: Claude model used for skill execution.
SKILL_MODEL: str = "claude-sonnet-4-6"

#: Maximum tokens for skill execution responses.
SKILL_MAX_TOKENS: int = 8192


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SkillRuntimeError(Exception):
    """Raised for infrastructure failures outside the normal failure protocol.

    Failures that are part of the skill contract (missing inputs, malformed
    artifacts, constraint violations, etc.) are returned as ``SkillResult``
    with the appropriate ``failure_category``.  ``SkillRuntimeError`` is
    reserved for truly unexpected errors such as the skill catalog being
    unreadable or the Claude CLI being unavailable.
    """


# ---------------------------------------------------------------------------
# Skill catalog loader (cached per repo_root)
# ---------------------------------------------------------------------------

_catalog_cache: dict[str, list[dict]] = {}


def _load_skill_catalog(repo_root: Path) -> list[dict]:
    """Load and cache ``skill_catalog.yaml``."""
    key = str(repo_root)
    if key in _catalog_cache:
        return _catalog_cache[key]

    catalog_path = repo_root / SKILL_CATALOG_REL_PATH
    if not catalog_path.exists():
        raise SkillRuntimeError(
            f"Skill catalog not found: {catalog_path}"
        )
    try:
        raw = catalog_path.read_text(encoding="utf-8-sig")
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError) as exc:
        raise SkillRuntimeError(
            f"Cannot load skill catalog {catalog_path}: {exc}"
        ) from exc

    entries = data.get("skill_catalog", [])
    if not isinstance(entries, list):
        raise SkillRuntimeError("skill_catalog is not a list")

    _catalog_cache[key] = entries
    return entries


def _get_skill_entry(skill_id: str, repo_root: Path) -> dict:
    """Return the catalog entry for *skill_id*."""
    for entry in _load_skill_catalog(repo_root):
        if entry.get("id") == skill_id:
            return entry
    raise SkillRuntimeError(
        f"Skill {skill_id!r} not found in skill_catalog.yaml"
    )


# ---------------------------------------------------------------------------
# Artifact schema specification loader (cached per repo_root)
# ---------------------------------------------------------------------------

_schema_spec_cache: dict[str, dict] = {}


def _load_artifact_schemas(repo_root: Path) -> dict:
    """Load and cache ``artifact_schema_specification.yaml``.

    Returns the full parsed YAML dict.
    """
    key = str(repo_root)
    if key in _schema_spec_cache:
        return _schema_spec_cache[key]

    schema_path = repo_root / ARTIFACT_SCHEMA_REL_PATH
    if not schema_path.exists():
        raise SkillRuntimeError(
            f"Artifact schema specification not found: {schema_path}"
        )
    try:
        raw = schema_path.read_text(encoding="utf-8-sig")
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError) as exc:
        raise SkillRuntimeError(
            f"Cannot load artifact schema specification: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise SkillRuntimeError(
            "Artifact schema specification root is not a dict"
        )
    _schema_spec_cache[key] = data
    return data


def _find_schema_for_path(
    canonical_path: str,
    repo_root: Path,
) -> dict | None:
    """Find the schema entry whose ``canonical_path`` matches.

    Searches all schema sections (``tier4_phase_output_schemas``,
    ``tier5_deliverable_schemas``, ``tier3_source_schemas``,
    ``tier2b_extracted_schemas``, ``tier2a_extracted_schemas``,
    ``checkpoint_schemas``).  Returns the schema entry dict, or ``None``
    if no match is found.
    """
    spec = _load_artifact_schemas(repo_root)
    # Normalise to forward-slash repo-relative string
    norm = canonical_path.replace("\\", "/")
    for section_key in (
        "tier4_phase_output_schemas",
        "tier5_deliverable_schemas",
        "tier3_source_schemas",
        "tier2b_extracted_schemas",
        "tier2a_extracted_schemas",
        "checkpoint_schemas",
    ):
        section = spec.get(section_key)
        if not isinstance(section, dict):
            continue
        for _name, entry in section.items():
            if not isinstance(entry, dict):
                continue
            if entry.get("canonical_path", "").replace("\\", "/") == norm:
                return entry
    return None


def _extract_schema_requirements(
    schema_entry: dict,
) -> tuple[str | None, list[str]]:
    """Extract ``(schema_id_value, required_field_names)`` from a schema entry.

    Returns ``(None, [])`` if the entry has no fields section.
    """
    schema_id = schema_entry.get("schema_id_value")
    required: list[str] = []
    fields = schema_entry.get("fields")
    if isinstance(fields, dict):
        for field_name, field_def in fields.items():
            if isinstance(field_def, dict) and field_def.get("required"):
                required.append(field_name)
    return schema_id, required


# ---------------------------------------------------------------------------
# Phase A — Load and resolve
# ---------------------------------------------------------------------------


def _load_skill_spec(skill_id: str, repo_root: Path) -> str:
    """Load the skill execution specification Markdown content."""
    spec_path = repo_root / SKILL_SPECS_REL_DIR / f"{skill_id}.md"
    if not spec_path.exists():
        raise SkillRuntimeError(
            f"Skill spec file not found: {spec_path}"
        )
    return spec_path.read_text(encoding="utf-8-sig")


def _resolve_inputs(
    reads_from: list[str],
    repo_root: Path,
    caller_inputs: dict[str, Any],
) -> dict[str, Any]:
    """Read canonical input artifacts from disk.

    Returns a merged dict of *caller_inputs* plus artifacts read from the
    ``reads_from`` paths.  Keys are the repo-relative paths; values are
    the parsed JSON content or raw text content.
    """
    resolved: dict[str, Any] = dict(caller_inputs)
    for rel_path in reads_from:
        abs_path = repo_root / rel_path
        if str(rel_path) in resolved:
            continue  # caller already provided this input
        if abs_path.is_dir():
            # For directory paths, collect all JSON files inside
            if abs_path.exists():
                for child in sorted(abs_path.iterdir()):
                    if child.suffix == ".json" and child.is_file():
                        child_rel = str(child.relative_to(repo_root))
                        if child_rel not in resolved:
                            try:
                                resolved[child_rel] = json.loads(
                                    child.read_text(encoding="utf-8-sig")
                                )
                            except (json.JSONDecodeError, OSError):
                                resolved[child_rel] = None
        elif abs_path.is_file():
            try:
                resolved[rel_path] = json.loads(
                    abs_path.read_text(encoding="utf-8-sig")
                )
            except json.JSONDecodeError:
                resolved[rel_path] = abs_path.read_text(encoding="utf-8-sig")
            except OSError:
                resolved[rel_path] = None
        # If path doesn't exist, it stays absent — validated in next step
    return resolved


def _validate_skill_inputs(
    skill_id: str,
    reads_from: list[str],
    repo_root: Path,
    resolved_inputs: dict[str, Any],
) -> list[str]:
    """Validate that all declared inputs are present and non-empty.

    Returns a list of validation errors.  Empty list means all inputs valid.
    """
    errors: list[str] = []
    for rel_path in reads_from:
        abs_path = repo_root / rel_path
        if abs_path.is_dir():
            if not abs_path.exists():
                errors.append(
                    f"Required input directory does not exist: {rel_path}"
                )
            elif not any(abs_path.iterdir()):
                errors.append(
                    f"Required input directory is empty: {rel_path}"
                )
        elif abs_path.is_file():
            content = resolved_inputs.get(rel_path)
            if content is None:
                errors.append(
                    f"Required input is null/unreadable: {rel_path}"
                )
            elif isinstance(content, dict) and not content:
                errors.append(
                    f"Required input is an empty object: {rel_path}"
                )
        else:
            errors.append(
                f"Required input does not exist: {rel_path}"
            )
    return errors


# ---------------------------------------------------------------------------
# Phase B — Prompt assembly
# ---------------------------------------------------------------------------


def _assemble_skill_prompt(
    skill_spec: str,
    inputs: dict[str, Any],
    run_id: str,
    writes_to: list[str],
    constraints: list[str],
) -> tuple[str, str]:
    """Assemble the system and user prompts for Claude invocation.

    Returns ``(system_prompt, user_prompt)``.
    """
    system_prompt = (
        "You are a skill execution engine for the Horizon Europe Proposal "
        "Orchestration System. You execute skill specifications precisely. "
        "You MUST return a single JSON object as your response — no prose, "
        "no markdown wrapping, no explanation. The JSON must conform to the "
        "output schema described in the skill specification.\n\n"
        "Constitutional constraints (hard failures if violated):\n"
    )
    for c in constraints:
        system_prompt += f"- {c}\n"
    system_prompt += (
        "\nYou MUST include these fields in every output artifact:\n"
        f'- "run_id": "{run_id}"\n'
        "- The appropriate schema_id as defined in the skill specification\n"
        "- Do NOT include an artifact_status field\n"
    )

    # User prompt: skill spec + inputs
    user_prompt = "# Skill Execution Specification\n\n"
    user_prompt += skill_spec
    user_prompt += "\n\n# Canonical Inputs\n\n"
    for path, content in inputs.items():
        user_prompt += f"## {path}\n\n"
        if isinstance(content, (dict, list)):
            user_prompt += f"```json\n{json.dumps(content, indent=2)}\n```\n\n"
        elif content is not None:
            user_prompt += f"```\n{content}\n```\n\n"
        else:
            user_prompt += "(not available)\n\n"

    user_prompt += "# Output Requirements\n\n"
    user_prompt += f"run_id: {run_id}\n"
    user_prompt += f"writes_to: {', '.join(writes_to)}\n"
    user_prompt += (
        "\nReturn a single JSON object conforming to the output schema "
        "defined in the skill specification above. Do not wrap in markdown. "
        "Do not include explanatory text."
    )

    return system_prompt, user_prompt


def _assemble_tapm_prompt(
    skill_spec: str,
    skill_id: str,
    run_id: str,
    reads_from: list[str],
    writes_to: list[str],
    constraints: list[str],
    repo_root: Path,
    node_id: str | None = None,
) -> tuple[str, str]:
    """Assemble TAPM (Tool-Augmented Prompt Mode) prompts for Claude.

    Unlike :func:`_assemble_skill_prompt`, this function does **not**
    serialize input file contents into the prompt.  Instead it provides
    declared input *paths* so Claude can read them from disk via the
    Read tool during execution.

    Returns ``(system_prompt, user_prompt)`` with a combined size of
    ~5-30KB (vs. 150-800KB in cli-prompt mode).
    """
    # ── System prompt ─────────────────────────────────────────────────
    system_prompt = (
        "You are a skill execution engine for the Horizon Europe Proposal "
        "Orchestration System. You execute skill specifications precisely. "
        "You MUST return a single JSON object as your response — no prose, "
        "no markdown wrapping, no explanation. The JSON must conform to the "
        "output schema described in the skill specification.\n\n"
    )

    # TAPM input-boundary instructions
    system_prompt += (
        "## Tool Access and Input Boundary\n\n"
        "You have access to the Read and Glob tools to read files from disk.\n"
        "Read ONLY the files listed in the Declared Inputs section of the "
        "task prompt. Do not read files outside the declared set.\n"
        "Do not use the Glob tool to discover files beyond the declared "
        "input paths. If a declared input is a directory, you may use Glob "
        "to list its contents, but do not navigate outside declared "
        "directories.\n"
        "Do not use any tools other than Read and Glob.\n\n"
    )

    # Constitutional constraints
    if constraints:
        system_prompt += "Constitutional constraints (hard failures if violated):\n"
        for c in constraints:
            system_prompt += f"- {c}\n"
        system_prompt += "\n"

    # Output field requirements
    system_prompt += (
        "You MUST include these fields in every output artifact:\n"
        f'- "run_id": "{run_id}"\n'
        "- The appropriate schema_id as defined in the skill specification\n"
        "- Do NOT include an artifact_status field\n"
    )

    # ── User prompt ───────────────────────────────────────────────────
    user_prompt = "# Skill Execution Specification\n\n"
    user_prompt += skill_spec

    # Task metadata
    user_prompt += "\n\n# Task Metadata\n\n"
    user_prompt += f"skill_id: {skill_id}\n"
    user_prompt += f"run_id: {run_id}\n"
    if node_id is not None:
        user_prompt += f"node_id: {node_id}\n"

    # Declared inputs — paths only, NO contents
    user_prompt += "\n# Declared Inputs\n\n"
    user_prompt += (
        "Read these files from disk using the Read tool. "
        "Do not read files outside this set.\n\n"
    )
    if reads_from:
        for rel_path in reads_from:
            abs_path = str(repo_root / rel_path)
            user_prompt += f"- {abs_path}\n"
    else:
        user_prompt += "(no declared inputs)\n"

    # Output requirements with schema hints
    user_prompt += "\n# Output Requirements\n\n"
    user_prompt += f"run_id: {run_id}\n"
    if writes_to:
        user_prompt += f"writes_to: {', '.join(writes_to)}\n"

    # Look up schema hints for writes_to paths
    schema_hints: list[str] = []
    for rel_path in writes_to:
        abs_path = repo_root / rel_path
        if rel_path.endswith("/") or abs_path.is_dir():
            # Directory — find all schemas under this prefix
            try:
                spec_data = _load_artifact_schemas(repo_root)
            except SkillRuntimeError:
                continue
            dir_norm = rel_path.rstrip("/")
            for section_key in (
                "tier4_phase_output_schemas",
                "tier5_deliverable_schemas",
                "tier3_source_schemas",
                "tier2b_extracted_schemas",
                "tier2a_extracted_schemas",
                "checkpoint_schemas",
            ):
                section = spec_data.get(section_key)
                if not isinstance(section, dict):
                    continue
                for _name, entry in section.items():
                    if not isinstance(entry, dict):
                        continue
                    cp = entry.get("canonical_path", "")
                    if cp.startswith(dir_norm + "/"):
                        sid, req = _extract_schema_requirements(entry)
                        hint = f"  - {cp}"
                        if sid:
                            hint += f" (schema_id: {sid!r})"
                        if req:
                            hint += f" required fields: {', '.join(req)}"
                        schema_hints.append(hint)
        else:
            # File — exact match
            schema_entry = _find_schema_for_path(rel_path, repo_root)
            if schema_entry is not None:
                sid, req = _extract_schema_requirements(schema_entry)
                hint = f"  - {rel_path}"
                if sid:
                    hint += f" (schema_id: {sid!r})"
                if req:
                    hint += f" required fields: {', '.join(req)}"
                schema_hints.append(hint)

    if schema_hints:
        user_prompt += "\nExpected output schemas:\n"
        for h in schema_hints:
            user_prompt += h + "\n"

    user_prompt += (
        "\nReturn a single JSON object conforming to the output schema "
        "defined in the skill specification above. Do not wrap in markdown. "
        "Do not include explanatory text."
    )

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Phase C — Claude invocation via runtime transport
# ---------------------------------------------------------------------------


def _invoke_claude(
    system_prompt: str,
    user_prompt: str,
) -> tuple[str | None, str | None]:
    """Invoke Claude via the runtime transport and return ``(response_text, error_message)``.

    Returns ``(text, None)`` on success, ``(None, error_msg)`` on failure.
    Uses the shared :func:`runner.claude_transport.invoke_claude_text`
    adapter, which routes through the local ``claude`` CLI.
    """
    try:
        text = invoke_claude_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=SKILL_MODEL,
            max_tokens=SKILL_MAX_TOKENS,
        )
        return text, None
    except ClaudeTransportError as exc:
        return None, f"Claude transport failed: {exc}"


# ---------------------------------------------------------------------------
# Phase D — Response parsing and validation
# ---------------------------------------------------------------------------


def _extract_json_response(text: str) -> dict | None:
    """Extract the first JSON object from Claude's response text.

    Handles bare JSON, JSON inside markdown code fences, and JSON
    preceded or followed by prose.  Returns ``None`` if no valid JSON
    dict can be found.
    """
    stripped = text.strip()

    # 1. Try whole response as JSON
    try:
        data = json.loads(stripped)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    # 2. Try markdown code fence
    code_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL
    )
    if code_match:
        try:
            data = json.loads(code_match.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 3. Try any JSON object in the text
    obj_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if obj_match:
        try:
            data = json.loads(obj_match.group())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _validate_skill_output(
    response: dict,
    run_id: str,
    expected_schema_id: str | None,
    required_fields: list[str] | None,
) -> list[str]:
    """Validate a parsed skill output against schema expectations.

    Returns a list of validation errors.  Empty list means valid.

    **No silent repair is performed.**  If ``run_id`` is missing or wrong,
    that is a validation error.  If ``artifact_status`` is present, that is
    a validation error.  The caller must not fix these before calling this
    function.

    Parameters
    ----------
    response:
        The parsed JSON dict from Claude's response (unmodified).
    run_id:
        Expected run_id value.
    expected_schema_id:
        Expected ``schema_id`` value from ``artifact_schema_specification.yaml``,
        or ``None`` if the artifact type does not require one (e.g. Tier 2B
        extracted files, validation reports, decision log entries).
    required_fields:
        List of field names that must be present (from the schema's
        ``required: true`` fields), or ``None`` to skip field checks.
    """
    errors: list[str] = []

    # run_id must be present and correct — not silently added
    if "run_id" not in response:
        errors.append("run_id is missing from response")
    elif response["run_id"] != run_id:
        errors.append(
            f"run_id mismatch: expected {run_id!r}, "
            f"got {response['run_id']!r}"
        )

    # schema_id check (only when expected from artifact_schema_specification)
    if expected_schema_id is not None:
        if "schema_id" not in response:
            errors.append(
                f"schema_id is missing; expected {expected_schema_id!r}"
            )
        elif response["schema_id"] != expected_schema_id:
            errors.append(
                f"schema_id mismatch: expected {expected_schema_id!r}, "
                f"got {response['schema_id']!r}"
            )

    # artifact_status must be absent — not silently removed
    if "artifact_status" in response:
        errors.append(
            "artifact_status must be absent at write time "
            "(runner-stamped post-gate); Claude included it in the response"
        )

    # Required fields check (from artifact_schema_specification required: true)
    if required_fields:
        for field_name in required_fields:
            if field_name not in response:
                errors.append(
                    f"Required field missing: {field_name!r} "
                    f"(required by artifact_schema_specification.yaml)"
                )

    return errors


# ---------------------------------------------------------------------------
# Phase E — Atomic canonical write
# ---------------------------------------------------------------------------


def _atomic_write(content: dict, canonical_path: Path) -> str | None:
    """Write *content* as JSON atomically to *canonical_path*.

    Writes to a temp file in the same directory, validates with a
    read-back, then atomically moves to the canonical path.

    Returns ``None`` on success, or an error message on failure.
    The canonical path is never left in a partially-written state.
    """
    canonical_path.parent.mkdir(parents=True, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path_str = tempfile.mkstemp(
            suffix=".tmp",
            dir=str(canonical_path.parent),
        )
        tmp_path = Path(tmp_path_str)

        json_bytes = json.dumps(content, indent=2, ensure_ascii=False).encode(
            "utf-8"
        )
        os.write(fd, json_bytes)
        os.close(fd)
        fd = None

        # Read-back validation
        read_back = json.loads(tmp_path.read_text(encoding="utf-8"))
        if not isinstance(read_back, dict):
            tmp_path.unlink(missing_ok=True)
            return "Read-back validation failed: not a dict"

        # Atomic move
        tmp_path.replace(canonical_path)
        return None

    except Exception as exc:  # noqa: BLE001
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        return f"Atomic write failed: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_skill(
    skill_id: str,
    run_id: str,
    repo_root: Path,
    inputs: dict[str, Any] | None = None,
) -> SkillResult:
    """Execute a skill specification via Claude and return a SkillResult.

    This is a **Claude runtime transport adapter**, not a Markdown
    interpreter.  The skill ``.md`` file is loaded as prompt context;
    Claude performs the domain reasoning; this function handles I/O,
    validation, and atomic writes.

    Parameters
    ----------
    skill_id:
        Skill identifier matching ``skill_catalog.yaml``.
    run_id:
        Current run UUID, propagated into every canonical artifact.
    repo_root:
        Absolute path to the repository root.
    inputs:
        Optional pre-resolved inputs dict.  Keys are repo-relative paths;
        values are parsed artifact content.  Missing inputs are resolved
        from disk using the skill's ``reads_from`` paths.

    Returns
    -------
    SkillResult
        Always returned — never raises for logical failures.  Only
        :class:`SkillRuntimeError` is raised for infrastructure failures.
    """
    if inputs is None:
        inputs = {}

    # ── Phase A: Load and resolve ──────────────────────────────────────

    # Load catalog entry
    try:
        entry = _get_skill_entry(skill_id, repo_root)
    except SkillRuntimeError as exc:
        return SkillResult(
            status="failure",
            failure_reason=str(exc),
            failure_category="MISSING_INPUT",
        )

    reads_from: list[str] = entry.get("reads_from", [])
    writes_to: list[str] = entry.get("writes_to", [])
    constraints: list[str] = entry.get("constitutional_constraints", [])

    # Load skill spec
    try:
        skill_spec = _load_skill_spec(skill_id, repo_root)
    except SkillRuntimeError as exc:
        return SkillResult(
            status="failure",
            failure_reason=str(exc),
            failure_category="MISSING_INPUT",
        )

    # Resolve inputs from disk
    resolved_inputs = _resolve_inputs(reads_from, repo_root, inputs)

    # Validate inputs
    validation_errors = _validate_skill_inputs(
        skill_id, reads_from, repo_root, resolved_inputs
    )
    if validation_errors:
        return SkillResult(
            status="failure",
            failure_reason=(
                f"Input validation failed for skill {skill_id!r}: "
                + "; ".join(validation_errors)
            ),
            failure_category="MISSING_INPUT",
        )

    # ── Phase B: Prompt assembly ───────────────────────────────────────

    system_prompt, user_prompt = _assemble_skill_prompt(
        skill_spec=skill_spec,
        inputs=resolved_inputs,
        run_id=run_id,
        writes_to=writes_to,
        constraints=constraints,
    )

    # ── Phase C: Claude invocation via runtime transport ────────────────

    response_text, api_error = _invoke_claude(system_prompt, user_prompt)
    if api_error is not None:
        return SkillResult(
            status="failure",
            failure_reason=f"Skill {skill_id!r}: {api_error}",
            failure_category="INCOMPLETE_OUTPUT",
        )

    # ── Phase D: Response parsing and validation ───────────────────────

    assert response_text is not None  # guaranteed by api_error check
    parsed = _extract_json_response(response_text)
    if parsed is None:
        return SkillResult(
            status="failure",
            failure_reason=(
                f"Skill {skill_id!r}: Claude returned non-JSON response: "
                f"{response_text[:300]!r}"
            ),
            failure_category="INCOMPLETE_OUTPUT",
        )

    # No silent repair: run_id and artifact_status are validated as-is.
    # If Claude omitted run_id or included artifact_status, that is a
    # MALFORMED_ARTIFACT failure — not silently corrected.

    # ── Phase E: Path-aware canonical write ────────────────────────────
    #
    # Limitation (documented honestly):
    #   This implementation supports writing Claude's single JSON response
    #   to exactly ONE canonical artifact path per invocation.  Skills
    #   whose writes_to declares multiple paths (e.g. a phase output
    #   directory AND a decision_log directory) will write the response
    #   to the first path that resolves to a canonical artifact with a
    #   known schema.  If no canonical schema is found for any writes_to
    #   path, the response is written to the first concrete file path.
    #
    #   Multi-artifact skill output (where Claude returns multiple
    #   distinct artifacts in one response) is not yet supported and
    #   will require a structured multi-artifact response protocol in
    #   a future step.

    outputs_written: list[str] = []

    # Resolve the single canonical output path and its schema.
    canonical_rel: str | None = None
    schema_entry: dict | None = None
    expected_schema_id: str | None = None
    required_fields: list[str] | None = None

    for rel_path in writes_to:
        abs_path = repo_root / rel_path
        if rel_path.endswith("/") or abs_path.is_dir():
            # Directory write path — look for a canonical artifact
            # whose canonical_path lives inside this directory.
            spec = _load_artifact_schemas(repo_root)
            for section_key in (
                "tier4_phase_output_schemas",
                "tier5_deliverable_schemas",
                "tier3_source_schemas",
                "tier2b_extracted_schemas",
                "tier2a_extracted_schemas",
                "checkpoint_schemas",
            ):
                section = spec.get(section_key)
                if not isinstance(section, dict):
                    continue
                for _name, entry in section.items():
                    if not isinstance(entry, dict):
                        continue
                    cp = entry.get("canonical_path", "")
                    dir_norm = rel_path.rstrip("/")
                    if cp.startswith(dir_norm + "/"):
                        schema_entry = entry
                        canonical_rel = cp
                        break
                if schema_entry is not None:
                    break
        else:
            # File write path — look for an exact canonical_path match.
            schema_entry = _find_schema_for_path(rel_path, repo_root)
            canonical_rel = rel_path

        if canonical_rel is not None:
            break

    # Fallback: if no canonical schema found, use first writes_to as-is
    if canonical_rel is None and writes_to:
        first = writes_to[0]
        if first.endswith("/"):
            # Directory with no known schema — write a named file
            canonical_rel = first + f"{skill_id}_{run_id[:8]}.json"
        else:
            canonical_rel = first

    if canonical_rel is None:
        return SkillResult(
            status="failure",
            failure_reason=(
                f"Skill {skill_id!r}: no writes_to path could be resolved"
            ),
            failure_category="INCOMPLETE_OUTPUT",
        )

    # Extract schema requirements for validation
    if schema_entry is not None:
        expected_schema_id, required_fields = _extract_schema_requirements(
            schema_entry
        )

    # Validate response against the real schema (no silent repair)
    output_errors = _validate_skill_output(
        response=parsed,
        run_id=run_id,
        expected_schema_id=expected_schema_id,
        required_fields=required_fields,
    )
    if output_errors:
        return SkillResult(
            status="failure",
            failure_reason=(
                f"Skill {skill_id!r} output validation failed: "
                + "; ".join(output_errors)
            ),
            failure_category="MALFORMED_ARTIFACT",
        )

    # Atomic write to the single resolved canonical path
    canonical_path = repo_root / canonical_rel
    write_error = _atomic_write(parsed, canonical_path)
    if write_error is not None:
        return SkillResult(
            status="failure",
            failure_reason=(
                f"Skill {skill_id!r}: atomic write to "
                f"{canonical_rel!r} failed: {write_error}"
            ),
            failure_category="INCOMPLETE_OUTPUT",
        )
    outputs_written.append(canonical_rel)

    # ── Phase F: Return ────────────────────────────────────────────────

    return SkillResult(
        status="success",
        outputs_written=outputs_written,
    )
