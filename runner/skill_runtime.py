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
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import yaml

from runner.claude_transport import (
    DEFAULT_TIMEOUT_SECONDS,
    ClaudeCLITimeoutError,
    ClaudeTransportError,
    invoke_claude_text,
)
from runner.runtime_models import SkillResult

logger = logging.getLogger(__name__)

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

#: Timeout for TAPM invocations (tool-augmented mode).
#: TAPM invocations involve multiple Read/Glob tool round-trips,
#: each adding latency.  The default 300s is insufficient for
#: skills that read multiple files and produce complex output.
TAPM_TIMEOUT_SECONDS: int = 600


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
# Contextual descriptor detection
# ---------------------------------------------------------------------------


def _is_contextual_descriptor(reads_from_entry: str) -> bool:
    """Return ``True`` when *reads_from_entry* is a contextual input descriptor
    rather than a real filesystem path.

    Some skills (e.g. ``decision-log-update``) declare ``reads_from`` entries
    that are prose descriptions of their input context rather than repository
    paths.  These must be skipped by path resolution and filesystem validation
    so they don't trigger spurious "Required input does not exist" failures.

    Recognition heuristic: all real repository paths in the skill catalog are
    repo-relative paths without embedded whitespace (e.g.
    ``docs/tier3_project_instantiation/project_brief/``, ``CLAUDE.md``).
    Contextual descriptors are natural-language prose that always contain
    at least one space character (e.g.
    ``"Any phase context requiring durable recording"``).
    """
    return " " in reads_from_entry


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
        if _is_contextual_descriptor(rel_path):
            continue  # prose descriptor, not a filesystem path
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
    writes_to: list[str] | None = None,
) -> list[str]:
    """Validate that all declared inputs are present and non-empty.

    When *writes_to* is provided, files that appear in both *reads_from*
    and *writes_to* are treated as upsert targets: an empty object ``{}``
    is accepted as a valid initial state because the skill is about to
    populate it.

    Returns a list of validation errors.  Empty list means all inputs valid.
    """
    # Normalize writes_to paths for reliable overlap detection
    norm_writes = {
        p.replace("\\", "/").rstrip("/")
        for p in (writes_to or [])
    }

    errors: list[str] = []
    for rel_path in reads_from:
        if _is_contextual_descriptor(rel_path):
            continue  # prose descriptor, not a filesystem path
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
                norm_rel = rel_path.replace("\\", "/").rstrip("/")
                if writes_to is not None and norm_rel in norm_writes:
                    pass  # valid upsert seed — skill will populate
                else:
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
    repo_root: Path,
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

    # Determine if the output schema requires run_id/schema_id
    any_schema_requires_run_id = False
    for rel_path in writes_to:
        abs_wpath = repo_root / rel_path
        if rel_path.endswith("/") or abs_wpath.is_dir():
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
                        if entry.get("schema_id_value"):
                            any_schema_requires_run_id = True
                            break
                if any_schema_requires_run_id:
                    break
        else:
            w_entry = _find_schema_for_path(rel_path, repo_root)
            if w_entry is not None and w_entry.get("schema_id_value"):
                any_schema_requires_run_id = True
        if any_schema_requires_run_id:
            break

    if any_schema_requires_run_id:
        system_prompt += (
            "\nYou MUST include these fields in every output artifact:\n"
            f'- "run_id": "{run_id}"\n'
            "- The appropriate schema_id as defined in the skill "
            "specification\n"
            "- Do NOT include an artifact_status field\n"
        )
    else:
        system_prompt += (
            "\nDo NOT include run_id, schema_id, or artifact_status fields "
            "in the output — this artifact type does not use them.\n"
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
    if any_schema_requires_run_id:
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

    # Look up schemas for writes_to paths to determine metadata
    # requirements and build schema hints for the user prompt.
    schema_hints: list[str] = []
    any_schema_requires_run_id = False
    for rel_path in writes_to:
        abs_wpath = repo_root / rel_path
        if rel_path.endswith("/") or abs_wpath.is_dir():
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
                        if sid:
                            any_schema_requires_run_id = True
                        hint = f"  - {cp}"
                        if sid:
                            hint += f" (schema_id: {sid!r})"
                        if req:
                            hint += f" required fields: {', '.join(req)}"
                        schema_hints.append(hint)
        else:
            w_entry = _find_schema_for_path(rel_path, repo_root)
            if w_entry is not None:
                sid, req = _extract_schema_requirements(w_entry)
                if sid:
                    any_schema_requires_run_id = True
                hint = f"  - {rel_path}"
                if sid:
                    hint += f" (schema_id: {sid!r})"
                if req:
                    hint += f" required fields: {', '.join(req)}"
                schema_hints.append(hint)

    # Output field requirements — conditional on artifact type
    if any_schema_requires_run_id:
        system_prompt += (
            "You MUST include these fields in every output artifact:\n"
            f'- "run_id": "{run_id}"\n'
            "- The appropriate schema_id as defined in the skill "
            "specification\n"
            "- Do NOT include an artifact_status field\n"
        )
    else:
        system_prompt += (
            "Do NOT include run_id, schema_id, or artifact_status fields "
            "in the output — this artifact type does not use them.\n"
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
    if any_schema_requires_run_id:
        user_prompt += f"run_id: {run_id}\n"
    if writes_to:
        user_prompt += f"writes_to: {', '.join(writes_to)}\n"

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
# Timeout diagnostic bundle
# ---------------------------------------------------------------------------


def _write_timeout_diagnostics(
    *,
    skill_id: str,
    run_id: str,
    node_id: str | None,
    mode: str,
    reads_from: list[str],
    writes_to: list[str],
    system_prompt: str,
    user_prompt: str,
    exc: ClaudeCLITimeoutError,
    repo_root: Path,
) -> dict[str, str]:
    """Write a diagnostic bundle for a cli-prompt timeout failure.

    Returns a dict mapping logical names to repo-relative paths of
    the written diagnostic files.
    """
    diag_dir = repo_root / ".claude" / "skill_diag"
    diag_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{skill_id}_{run_id[:8]}"
    written: dict[str, str] = {}

    partial_stdout = exc.stdout or ""
    partial_stderr = exc.stderr or ""

    # -- timeout_meta.json --
    meta = {
        "skill_id": skill_id,
        "execution_mode": mode,
        "run_id": run_id,
        "node_id": node_id,
        "reads_from": reads_from,
        "writes_to": writes_to,
        "model": SKILL_MODEL,
        "max_tokens": SKILL_MAX_TOKENS,
        "timeout_seconds": exc.timeout_seconds,
        "elapsed_seconds": exc.elapsed_seconds,
        "system_prompt_size": len(system_prompt),
        "user_prompt_size": len(user_prompt),
        "command": exc.command,
        "had_partial_stdout": bool(partial_stdout.strip()),
        "had_stderr": bool(partial_stderr.strip()),
    }

    file_map = {
        "meta": (f"{prefix}_timeout_meta.json", None),
        "system_prompt": (f"{prefix}_system_prompt.txt", system_prompt),
        "user_prompt": (f"{prefix}_user_prompt.txt", user_prompt),
        "stdout": (f"{prefix}_stdout.txt", partial_stdout),
        "stderr": (f"{prefix}_stderr.txt", partial_stderr),
    }

    # Populate diagnostic_files in meta before writing
    meta["diagnostic_files"] = {
        k: f".claude/skill_diag/{fname}" for k, (fname, _) in file_map.items()
    }

    try:
        meta_path = diag_dir / file_map["meta"][0]
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        written["meta"] = f".claude/skill_diag/{file_map['meta'][0]}"
    except OSError:
        pass

    for key in ("system_prompt", "user_prompt", "stdout", "stderr"):
        fname, content = file_map[key]
        try:
            (diag_dir / fname).write_text(content or "", encoding="utf-8")
            written[key] = f".claude/skill_diag/{fname}"
        except OSError:
            pass

    return written


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
    *,
    require_run_id: bool = True,
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
    require_run_id:
        Whether to enforce ``run_id`` presence and correctness.  Phase-output
        canonical artifacts (which carry a ``schema_id_value``) require
        ``run_id``; Tier 2B/2A extracted artifacts (``provenance_class:
        manually_placed``, no ``schema_id_value``) do not.  Callers set
        this explicitly based on the artifact type.
    """
    errors: list[str] = []

    # run_id check — only for artifact types that carry it
    if require_run_id:
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
    *,
    node_id: str | None = None,
) -> SkillResult:
    """Execute a skill specification via Claude and return a SkillResult.

    This is a **Claude runtime transport adapter**, not a Markdown
    interpreter.  The skill ``.md`` file is loaded as prompt context;
    Claude performs the domain reasoning; this function handles I/O,
    validation, and atomic writes.

    Supports two execution modes controlled by the ``execution_mode``
    field in the skill catalog entry:

    - ``"cli-prompt"`` (default): All inputs are resolved from disk,
      serialized into the prompt, and piped to ``claude -p``.
    - ``"tapm"``: Tool-Augmented Prompt Mode.  Only task metadata and
      the skill spec are included in the prompt.  Claude reads declared
      inputs from disk via Read/Glob tools during execution.

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
        from disk using the skill's ``reads_from`` paths.  Ignored in
        TAPM mode (Claude reads inputs from disk directly).
    node_id:
        Optional workflow node identifier (e.g. ``"n01_call_analysis"``).
        Included as task metadata in TAPM prompts for traceability.
        Ignored in cli-prompt mode.

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

    # ── Mode selection ────────────────────────────────────────────────
    mode = entry.get("execution_mode", "cli-prompt")
    _skill_t0 = time.monotonic()
    logger.info(
        "  skill START  id=%s  mode=%s  node=%s  run=%s",
        skill_id, mode, node_id or "-", run_id[:8],
    )

    if mode == "tapm":
        # ── TAPM Path: Phases A'-C' ──────────────────────────────────
        #
        # Skip _resolve_inputs() and _validate_skill_inputs(): Claude
        # reads declared inputs from disk via the Read tool.
        # Skip _assemble_skill_prompt(): use _assemble_tapm_prompt().

        system_prompt, user_prompt = _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id=skill_id,
            run_id=run_id,
            reads_from=reads_from,
            writes_to=writes_to,
            constraints=constraints,
            repo_root=repo_root,
            node_id=node_id,
        )
        logger.info(
            "  skill INVOKE id=%s  sys=%d  user=%d  timeout=%ds",
            skill_id, len(system_prompt), len(user_prompt),
            TAPM_TIMEOUT_SECONDS,
        )

        try:
            response_text = invoke_claude_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=SKILL_MODEL,
                max_tokens=SKILL_MAX_TOKENS,
                tools=["Read", "Glob"],
                timeout_seconds=TAPM_TIMEOUT_SECONDS,
            )
        except ClaudeTransportError as exc:
            # Diagnostic: capture transport failure for debugging
            _diag_dir = repo_root / ".claude" / "skill_diag"
            _diag_dir.mkdir(parents=True, exist_ok=True)
            try:
                (
                    _diag_dir / f"{skill_id}_{run_id[:8]}_transport_fail.txt"
                ).write_text(
                    f"=== Transport failure ===\n"
                    f"skill_id: {skill_id}\n"
                    f"mode: tapm\n"
                    f"error: {exc}\n"
                    f"timeout_seconds: {TAPM_TIMEOUT_SECONDS}\n"
                    f"=== END ===\n",
                    encoding="utf-8",
                )
            except OSError:
                pass
            _elapsed = time.monotonic() - _skill_t0
            logger.info(
                "  skill FAIL   id=%s  category=INCOMPLETE_OUTPUT  elapsed=%.1fs",
                skill_id, _elapsed,
            )
            return SkillResult(
                status="failure",
                failure_reason=(
                    f"Skill {skill_id!r}: Claude transport failed: {exc}"
                ),
                failure_category="INCOMPLETE_OUTPUT",
            )

    elif mode == "cli-prompt":
        # ── CLI-Prompt Path: Phases A-C (unchanged) ──────────────────

        # Resolve inputs from disk
        resolved_inputs = _resolve_inputs(reads_from, repo_root, inputs)

        # Validate inputs
        validation_errors = _validate_skill_inputs(
            skill_id, reads_from, repo_root, resolved_inputs, writes_to
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

        # Phase B: Prompt assembly
        system_prompt, user_prompt = _assemble_skill_prompt(
            skill_spec=skill_spec,
            inputs=resolved_inputs,
            run_id=run_id,
            writes_to=writes_to,
            constraints=constraints,
            repo_root=repo_root,
        )
        logger.info(
            "  skill INVOKE id=%s  sys=%d  user=%d  timeout=%ds",
            skill_id, len(system_prompt), len(user_prompt),
            DEFAULT_TIMEOUT_SECONDS,
        )

        # Phase C: Claude invocation via runtime transport
        try:
            response_text = invoke_claude_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=SKILL_MODEL,
                max_tokens=SKILL_MAX_TOKENS,
            )
        except ClaudeCLITimeoutError as exc:
            diag_paths = _write_timeout_diagnostics(
                skill_id=skill_id,
                run_id=run_id,
                node_id=node_id,
                mode=mode,
                reads_from=reads_from,
                writes_to=writes_to,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                exc=exc,
                repo_root=repo_root,
            )
            meta_rel = diag_paths.get("meta", "")
            _elapsed = time.monotonic() - _skill_t0
            logger.info(
                "  skill TIMEOUT id=%s  elapsed=%.1fs  diag=%s",
                skill_id, _elapsed, meta_rel,
            )
            return SkillResult(
                status="failure",
                failure_reason=(
                    f"Skill {skill_id!r}: Claude transport failed: {exc}. "
                    f"Diagnostics written to {meta_rel}"
                ),
                failure_category="INCOMPLETE_OUTPUT",
            )
        except ClaudeTransportError as exc:
            _elapsed = time.monotonic() - _skill_t0
            logger.info(
                "  skill FAIL   id=%s  category=INCOMPLETE_OUTPUT  elapsed=%.1fs",
                skill_id, _elapsed,
            )
            return SkillResult(
                status="failure",
                failure_reason=(
                    f"Skill {skill_id!r}: Claude transport failed: {exc}"
                ),
                failure_category="INCOMPLETE_OUTPUT",
            )

    else:
        return SkillResult(
            status="failure",
            failure_reason=(
                f"Skill {skill_id!r}: unrecognized execution_mode "
                f"{mode!r}; must be 'cli-prompt' or 'tapm'"
            ),
            failure_category="CONSTRAINT_VIOLATION",
        )

    # ── Phase D: Response parsing and validation ───────────────────────

    assert response_text is not None  # guaranteed by api_error check

    # ── Diagnostic capture (temporary) ──────────────────────────────
    _diag_dir = repo_root / ".claude" / "skill_diag"
    _diag_dir.mkdir(parents=True, exist_ok=True)
    _diag_path = _diag_dir / f"{skill_id}_{run_id[:8]}_response.txt"
    try:
        _diag_path.write_text(
            f"=== skill_id: {skill_id} ===\n"
            f"=== mode: {mode} ===\n"
            f"=== response_text length: {len(response_text)} ===\n"
            f"=== response_text (full) ===\n{response_text}\n"
            f"=== END ===\n",
            encoding="utf-8",
        )
    except OSError:
        pass  # Best-effort diagnostic

    parsed = _extract_json_response(response_text)

    # Diagnostic: log parse result
    try:
        _diag_parse_path = _diag_dir / f"{skill_id}_{run_id[:8]}_parsed.txt"
        if parsed is not None:
            _diag_parse_path.write_text(
                f"=== parsed OK ===\n"
                f"=== top-level keys: {list(parsed.keys())} ===\n"
                f"=== parsed content ===\n"
                f"{json.dumps(parsed, indent=2)[:5000]}\n"
                f"=== END ===\n",
                encoding="utf-8",
            )
        else:
            _diag_parse_path.write_text(
                f"=== parsed FAILED (None) ===\n"
                f"=== response_text first 1000 chars ===\n"
                f"{response_text[:1000]}\n"
                f"=== END ===\n",
                encoding="utf-8",
            )
    except OSError:
        pass

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
    # Supports two write modes:
    #
    # 1. Single-artifact mode (default): writes_to resolves to exactly
    #    one canonical artifact path.  Claude's full response is written
    #    to that path after validation.
    #
    # 2. Multi-artifact mode: the combined writes_to entries resolve to
    #    more than one canonical artifact path.  This may occur when a
    #    single directory contains multiple canonical schemas, OR when
    #    multiple independent writes_to entries (directories and/or
    #    files) each resolve to one or more canonical schemas.  Claude's
    #    response contains root fields matching each schema's required
    #    fields.  Each matching sub-object is extracted, validated
    #    independently, and written to its own canonical path.
    #
    # Multi-artifact mode activates when the total number of resolved
    # canonical artifacts across ALL writes_to entries exceeds one.

    outputs_written: list[str] = []

    # Collect ALL matching canonical artifacts for each writes_to path.
    dir_artifacts: list[tuple[str, dict]] = []  # (canonical_rel, schema_entry)

    for rel_path in writes_to:
        abs_path = repo_root / rel_path
        if rel_path.endswith("/") or abs_path.is_dir():
            # Directory write path — collect all canonical artifacts
            # whose canonical_path lives inside this directory.
            spec = _load_artifact_schemas(repo_root)
            dir_norm = rel_path.rstrip("/")
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
                    if cp.startswith(dir_norm + "/"):
                        dir_artifacts.append((cp, entry))
        else:
            # File write path — look for an exact canonical_path match.
            file_entry = _find_schema_for_path(rel_path, repo_root)
            dir_artifacts.append((rel_path, file_entry or {}))

        # All writes_to entries are iterated — no early break.
        # Artifacts from independent directories/files accumulate in
        # dir_artifacts and are handled by multi-artifact mode below.

    # ── Deduplicate dir_artifacts by canonical_rel ──────────────────
    # Multiple writes_to entries could theoretically resolve to the same
    # canonical path (config mistake).  Deduplicate to avoid double
    # validation/write.
    if dir_artifacts:
        _seen: set[str] = set()
        _unique: list[tuple[str, dict]] = []
        for _cp, _se in dir_artifacts:
            if _cp not in _seen:
                _seen.add(_cp)
                _unique.append((_cp, _se))
        dir_artifacts = _unique

    # ── Multi-artifact write path ────────────────────────────────────
    # Diagnostic: Phase E state
    try:
        _diag_phase_e = _diag_dir / f"{skill_id}_{run_id[:8]}_phase_e.txt"
        _diag_phase_e.write_text(
            f"=== Phase E ===\n"
            f"dir_artifacts count: {len(dir_artifacts)}\n"
            f"dir_artifacts paths: {[cp for cp, _ in dir_artifacts]}\n"
            f"parsed keys (if parsed): {list(parsed.keys()) if parsed else 'N/A'}\n"
            f"=== END ===\n",
            encoding="utf-8",
        )
    except (OSError, NameError):
        pass
    if len(dir_artifacts) > 1:
        all_errors: list[str] = []
        pending_writes: list[tuple[str, dict]] = []

        # Metadata fields are stamped separately from domain fields.
        _META_FIELDS = {"schema_id", "run_id"}

        for canonical_rel, s_entry in dir_artifacts:
            exp_sid, req_fields = _extract_schema_requirements(s_entry)
            need_run_id = exp_sid is not None

            if not req_fields:
                continue  # Skip schemas with no required fields

            # Domain fields = required fields minus metadata.
            # The first domain field is used as the anchor to detect
            # whether Claude returned a flat or nested response shape.
            domain_fields = [f for f in req_fields if f not in _META_FIELDS]
            if not domain_fields:
                continue  # No domain fields to anchor extraction

            anchor_field = domain_fields[0]

            # Claude may return one of several response shapes:
            #   Flat:           { "evaluation_matrix": {...}, "instruments": [...] }
            #   Canonical-keyed: { "docs/.../call_analysis_summary.json": {...} }
            #   Basename-keyed:  { "call_analysis_summary.json": {...} }
            #   Stem-keyed:      { "call_analysis_summary": {...} }
            # Detect shape using the anchor field, then collect ALL
            # required fields from the identified source dict.
            sub_artifact: dict | None = None

            if anchor_field in parsed:
                # Flat shape — domain fields at top level of parsed.
                # Collect all required fields present at top level.
                sub_artifact = {}
                for f in req_fields:
                    if f in parsed:
                        sub_artifact[f] = parsed[f]
            else:
                # Try nested shapes: canonical path, basename, stem.
                file_key = canonical_rel.rsplit("/", 1)[-1]
                file_key_stem = file_key.rsplit(".", 1)[0]
                source: dict | None = None
                for key in (canonical_rel, file_key, file_key_stem):
                    nested = parsed.get(key)
                    if isinstance(nested, dict) and anchor_field in nested:
                        source = nested
                        break

                if source is not None:
                    sub_artifact = {}
                    for f in req_fields:
                        if f in source:
                            sub_artifact[f] = source[f]

            if sub_artifact is None:
                all_errors.append(
                    f"Multi-artifact response missing field "
                    f"{anchor_field!r} for {canonical_rel!r}"
                )
                continue

            # Stamp metadata from top-level parsed as fallback
            if need_run_id and "run_id" not in sub_artifact and "run_id" in parsed:
                sub_artifact["run_id"] = parsed["run_id"]
            if (
                exp_sid is not None
                and "schema_id" not in sub_artifact
                and "schema_id" in parsed
            ):
                sub_artifact["schema_id"] = parsed["schema_id"]

            # Validate the sub-artifact independently
            sub_errors = _validate_skill_output(
                response=sub_artifact,
                run_id=run_id,
                expected_schema_id=exp_sid,
                required_fields=req_fields,
                require_run_id=need_run_id,
            )
            if sub_errors:
                all_errors.append(
                    f"Validation failed for {canonical_rel!r}: "
                    + "; ".join(sub_errors)
                )
            else:
                pending_writes.append((canonical_rel, sub_artifact))

        if all_errors:
            return SkillResult(
                status="failure",
                failure_reason=(
                    f"Skill {skill_id!r} multi-artifact validation failed: "
                    + "; ".join(all_errors)
                ),
                failure_category="MALFORMED_ARTIFACT",
            )

        if not pending_writes:
            return SkillResult(
                status="failure",
                failure_reason=(
                    f"Skill {skill_id!r}: no sub-artifacts matched in response"
                ),
                failure_category="INCOMPLETE_OUTPUT",
            )

        # Write all validated sub-artifacts
        for canonical_rel, content in pending_writes:
            write_error = _atomic_write(content, repo_root / canonical_rel)
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

        return SkillResult(
            status="success",
            outputs_written=outputs_written,
        )

    # ── Single-artifact write path (existing behavior) ───────────────
    canonical_rel: str | None = None
    schema_entry: dict | None = None
    expected_schema_id: str | None = None
    required_fields: list[str] | None = None

    if dir_artifacts:
        canonical_rel, schema_entry = dir_artifacts[0]
    else:
        # Fallback: if no canonical schema found, use first writes_to as-is
        if writes_to:
            first = writes_to[0]
            if first.endswith("/"):
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

    require_run_id = expected_schema_id is not None

    # Validate response against the real schema (no silent repair)
    output_errors = _validate_skill_output(
        response=parsed,
        run_id=run_id,
        expected_schema_id=expected_schema_id,
        required_fields=required_fields,
        require_run_id=require_run_id,
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

    _elapsed = time.monotonic() - _skill_t0
    logger.info(
        "  skill OK     id=%s  outputs=%d  elapsed=%.1fs",
        skill_id, len(outputs_written), _elapsed,
    )
    return SkillResult(
        status="success",
        outputs_written=outputs_written,
    )
