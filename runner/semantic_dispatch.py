"""
Semantic predicate dispatch layer (Step 11 — corrected).

Invokes the designated agent for each semantic predicate via the Claude
runtime transport (local ``claude`` CLI through
:func:`runner.claude_transport.invoke_claude_text`).  The agent reads the
supplied artifact content and applies open-ended constitutional judgment,
returning a structured result conforming to the §4.9 result schema.  No
local rule about what constitutes a violation is encoded here: the agent
reasons from the actual artifact content and the constitutional rule
stated in its system prompt.

See gate_rules_library_plan.md §4.9 for the result schema and
§6.1 step 8 for the runner integration contract.

Agent invocation model
-----------------------
For each semantic predicate the dispatcher:

1. Resolves every string-valued arg in the predicate ``args`` block to
   an absolute path, substituting ``${run_id}`` tokens.
2. Reads artifact content from those paths (files read directly;
   directories enumerate their direct-child ``.json`` files).
3. Builds a system prompt that states the agent's role, the predicate
   description, the constitutional rule, and the mandatory JSON response
   schema (§4.9).
4. Invokes ``claude-sonnet-4-6`` via the runtime transport with the
   system prompt and a user message containing the artifact content.
5. Parses the agent's JSON response and validates it with
   :func:`validate_semantic_result`.

Failure discipline
------------------
Every finding in a ``status: fail`` result MUST include:

* ``violated_rule`` — a named CLAUDE.md section.
* ``evidence_path`` — the specific artifact path containing the
  violation.

The runner rejects findings that omit either field.  Dispatch errors
(unknown function, transport failure, malformed response) produce a
sentinel dict with ``_dispatch_error: True`` and ``status: "error"``;
this intentionally fails :func:`validate_semantic_result` so the caller
treats it as a gate failure.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from runner.claude_transport import ClaudeTransportError, invoke_claude_text
from runner.paths import resolve_repo_path

# ---------------------------------------------------------------------------
# Schema constants  (§4.9)
# ---------------------------------------------------------------------------

#: Required top-level fields in every semantic result.
REQUIRED_RESULT_FIELDS: frozenset[str] = frozenset(
    {
        "predicate_id",
        "function",
        "status",
        "agent",
        "constitutional_rule",
        "artifacts_inspected",
        "findings",
    }
)

#: Valid values for the top-level ``status`` field.
VALID_STATUSES: frozenset[str] = frozenset({"pass", "fail"})

#: Required fields in every entry of the ``findings`` list.
REQUIRED_FINDING_FIELDS: frozenset[str] = frozenset(
    {"claim", "violated_rule", "evidence_path", "severity"}
)

#: Valid values for finding ``severity``.
VALID_SEVERITIES: frozenset[str] = frozenset({"critical", "major"})

#: Claude model used for semantic predicate evaluation.
AGENT_MODEL: str = "claude-sonnet-4-6"

#: Maximum tokens the agent may use in its response.
AGENT_MAX_TOKENS: int = 2048


# ---------------------------------------------------------------------------
# Semantic predicate configuration registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticPredicateConfig:
    """
    Invocation configuration for a single semantic predicate.

    Carries everything the dispatcher needs to invoke the designated
    agent and build the correct prompts.  This is a configuration record,
    not a handler callable.
    """

    function: str
    agent: str
    constitutional_rule: str
    description: str


#: Maps semantic predicate function names to their invocation configurations.
#: Semantic predicates are evaluated by Claude (via the runtime transport), not by local functions.
SEMANTIC_REGISTRY: dict[str, SemanticPredicateConfig] = {
    "no_unresolved_scope_conflicts": SemanticPredicateConfig(
        function="no_unresolved_scope_conflicts",
        agent="concept_refiner",
        constitutional_rule="CLAUDE.md §7 Phase 2 gate",
        description=(
            "No scope conflict between the Phase 2 refined concept output and "
            "Tier 2B scope requirements remains unresolved."
        ),
    ),
    "no_cross_tier_contradictions": SemanticPredicateConfig(
        function="no_cross_tier_contradictions",
        agent="constitutional_compliance_check",
        constitutional_rule="CLAUDE.md §11.4, §13.3",
        description=(
            "No factual claim in Tier 5 proposal sections contradicts confirmed "
            "Tier 3 project facts."
        ),
    ),
    "no_unsupported_tier5_claims": SemanticPredicateConfig(
        function="no_unsupported_tier5_claims",
        agent="constitutional_compliance_check",
        constitutional_rule="CLAUDE.md §13.3",
        description=(
            "No project fact asserted in Tier 5 (partner name, capability, role, "
            "objective, prior experience, budget figure, team size, equipment) is "
            "absent from Tier 3."
        ),
    ),
    "no_budget_gate_contradiction": SemanticPredicateConfig(
        function="no_budget_gate_contradiction",
        agent="constitutional_compliance_check",
        constitutional_rule="CLAUDE.md §8.4, §13.4",
        description=(
            "No Tier 5 section references a specific budget figure, effort "
            "allocation, or resource commitment that is not present in the "
            "validated budget response."
        ),
    ),
    "no_higher_tier_contradiction": SemanticPredicateConfig(
        function="no_higher_tier_contradiction",
        agent="constitutional_compliance_check",
        constitutional_rule="CLAUDE.md §13.2, §11.3",
        description=(
            "No Tier 5 section asserts a call constraint, scope boundary, expected "
            "outcome, or expected impact not traceable to Tier 2A or Tier 2B source "
            "documents."
        ),
    ),
    "no_forbidden_schema_authority": SemanticPredicateConfig(
        function="no_forbidden_schema_authority",
        agent="constitutional_compliance_check",
        constitutional_rule="CLAUDE.md §13.1",
        description=(
            "No Tier 5 section is structured according to a Grant Agreement Annex "
            "template rather than the active application form (Tier 2A)."
        ),
    ),
    "no_gap_masked_as_confirmed": SemanticPredicateConfig(
        function="no_gap_masked_as_confirmed",
        agent="constitutional_compliance_check",
        constitutional_rule="CLAUDE.md §12.2",
        description=(
            "No Tier 5 section presents content with 'Confirmed' validation status "
            "where the underlying source is 'Unresolved' or 'Assumed' in the "
            "relevant Tier 4 phase output."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_semantic_result(result: Any) -> tuple[bool, str]:
    """
    Validate a semantic predicate result dict against the §4.9 schema.

    Returns
    -------
    (True, "")
        Result conforms to the schema.
    (False, reason)
        Result is malformed; *reason* is a machine-readable explanation.

    Rules
    -----
    * Result must be a ``dict``.
    * All :data:`REQUIRED_RESULT_FIELDS` must be present.
    * ``status`` must be ``"pass"`` or ``"fail"``.
    * ``findings`` must be a list.
    * Every finding must be a dict with all :data:`REQUIRED_FINDING_FIELDS`,
      each non-empty.
    * ``severity`` in each finding must be ``"critical"`` or ``"major"``.
    """
    if not isinstance(result, dict):
        return False, (
            f"semantic result must be a dict; got {type(result).__name__}"
        )

    missing = REQUIRED_RESULT_FIELDS - result.keys()
    if missing:
        return False, (
            f"semantic result missing required fields: {sorted(missing)}"
        )

    status = result["status"]
    if status not in VALID_STATUSES:
        return False, (
            f"semantic result has invalid status {status!r}; "
            "expected 'pass' or 'fail'"
        )

    findings = result["findings"]
    if not isinstance(findings, list):
        return False, (
            f"semantic result 'findings' must be a list; "
            f"got {type(findings).__name__}"
        )

    for i, finding in enumerate(findings):
        if not isinstance(finding, dict):
            return False, (
                f"findings[{i}] must be a dict; got {type(finding).__name__}"
            )
        missing_f = REQUIRED_FINDING_FIELDS - finding.keys()
        if missing_f:
            return False, (
                f"findings[{i}] missing required fields: {sorted(missing_f)}.  "
                "Every finding must include 'violated_rule' and 'evidence_path' "
                "(gate_rules_library_plan.md §4.9)."
            )
        for fname in ("claim", "violated_rule", "evidence_path"):
            if not str(finding.get(fname, "")).strip():
                return False, (
                    f"findings[{i}].{fname!r} must be a non-empty string.  "
                    "Narrative-only findings without a named rule and evidence "
                    "path are rejected."
                )
        sev = finding.get("severity")
        if sev not in VALID_SEVERITIES:
            return False, (
                f"findings[{i}].severity {sev!r} is not valid; "
                f"expected one of {sorted(VALID_SEVERITIES)}"
            )

    return True, ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _dispatch_error_result(pred_id: str, func_name: str, reason: str) -> dict:
    """
    Return a sentinel dict that signals a dispatch-level failure.

    The result intentionally uses ``status: "error"`` (not in
    :data:`VALID_STATUSES`) and omits required fields so that
    :func:`validate_semantic_result` returns ``(False, …)``.  Callers
    identify dispatch errors via the ``_dispatch_error`` boolean key.
    """
    return {
        "predicate_id": pred_id,
        "function": func_name,
        "status": "error",          # invalid → validation rejects this
        "findings": [],
        "_dispatch_error": True,
        "_dispatch_error_reason": reason,
    }


def _read_artifacts(
    args: dict,
    repo_root: Path,
) -> tuple[dict[str, str], list[str]]:
    """
    Read artifact content from all string-valued path args.

    File paths are read directly.  Directory paths have every direct-child
    ``.json`` file read.  Non-existent or unreadable paths are silently
    skipped (their absence is the deterministic layer's responsibility).

    Returns
    -------
    artifact_contents
        ``{absolute_path_str: utf8_text}`` for every file read.
    inspected_paths
        Ordered list of absolute path strings successfully read.
    """
    contents: dict[str, str] = {}
    inspected: list[str] = []

    for value in args.values():
        if not isinstance(value, str):
            continue
        resolved = resolve_repo_path(value, repo_root)
        if resolved.is_file():
            try:
                text = resolved.read_text(encoding="utf-8-sig")
                contents[str(resolved)] = text
                inspected.append(str(resolved))
            except OSError:
                pass
        elif resolved.is_dir():
            for child in sorted(resolved.iterdir()):
                if child.is_file() and child.suffix.lower() == ".json":
                    try:
                        text = child.read_text(encoding="utf-8-sig")
                        contents[str(child)] = text
                        inspected.append(str(child))
                    except OSError:
                        pass

    return contents, inspected


# §4.9 result schema block embedded in the system prompt.
_RESULT_SCHEMA: str = """\
{
  "predicate_id": "<omit or set to any string — runner injects authoritative value>",
  "function": "<the predicate function name>",
  "status": "pass" | "fail",
  "agent": "<your agent identifier>",
  "constitutional_rule": "<the CLAUDE.md section this predicate enforces>",
  "artifacts_inspected": ["<path1>", "<path2>", ...],
  "findings": [
    {
      "claim": "<the specific text, assertion, or content that violates the rule>",
      "violated_rule": "<named CLAUDE.md section, e.g. CLAUDE.md §13.3>",
      "evidence_path": "<absolute path to the artifact containing the violation>",
      "severity": "critical" | "major"
    }
  ],
  "fail_message": "<one-sentence summary when status is fail; empty string when pass>"
}"""


def _build_system_prompt(config: SemanticPredicateConfig) -> str:
    """
    Build the system prompt for the designated agent.

    States the agent's constitutional role, the predicate it must
    evaluate, the rule it enforces, and the exact JSON schema it must
    return.
    """
    return (
        f"You are {config.agent}, a specialised constitutional compliance "
        "agent in the Horizon Europe Proposal Orchestration System.\n\n"
        "Your task is to evaluate the following semantic predicate:\n\n"
        f"  Function:            {config.function}\n"
        f"  Description:         {config.description}\n"
        f"  Constitutional rule: {config.constitutional_rule}\n\n"
        "Evaluation procedure:\n"
        "1. Read every artifact provided in the user message carefully.\n"
        "2. Determine whether the predicate condition is satisfied by reasoning "
        "from the artifact content — do not rely on prior knowledge.\n"
        "3. If violations are found, identify: the specific claim or section "
        "content, the named CLAUDE.md section violated, the artifact path, "
        "and the severity (critical or major).\n"
        "4. Return ONLY a JSON object conforming to the result schema below.  "
        "No prose before or after the JSON object.\n\n"
        f"Result schema:\n{_RESULT_SCHEMA}\n\n"
        "Rules:\n"
        f'- Return status "pass" when no violations of '
        f"{config.constitutional_rule} are found.\n"
        '- Return status "fail" when at least one violation is found.\n'
        "- Every finding MUST include a named CLAUDE.md section in "
        "violated_rule and an evidence_path pointing to a specific artifact.\n"
        "- Do NOT invent violations.  Only report what is directly evidenced "
        "in the provided artifact content.\n"
        "- Do NOT use prior knowledge of project facts.  Reason only from the "
        "provided artifact content.\n"
        '- severity "critical" = immediate gate blocker; '
        '"major" = significant but less urgent.'
    )


def _build_user_prompt(
    config: SemanticPredicateConfig,
    artifact_contents: dict[str, str],
    resolved_args: dict,
) -> str:
    """
    Build the user-turn prompt containing artifact content for inspection.
    """
    parts: list[str] = [
        f"Evaluate predicate: {config.function}",
        f"Constitutional rule: {config.constitutional_rule}",
        "",
    ]

    if artifact_contents:
        parts.append(
            f"Artifacts provided for inspection ({len(artifact_contents)} file(s)):"
        )
        for path_str, content in artifact_contents.items():
            parts.append(f"\n=== {path_str} ===")
            parts.append(content)
            parts.append(f"=== end {path_str} ===")
    else:
        parts.append(
            "(No artifact files could be read at this time.  "
            "Predicate args: " + repr(resolved_args) + ")"
        )

    parts.append("\nReturn the evaluation result as a single JSON object.")
    return "\n".join(parts)


def _extract_json(text: str) -> Optional[dict]:
    """
    Extract the first JSON object from *text*.

    Handles bare JSON, JSON inside a markdown code block, and JSON
    preceded or followed by prose.  Returns ``None`` if no valid JSON
    object can be found.
    """
    stripped = text.strip()

    # 1. Try parsing the whole response as JSON.
    # If it parses but is not a dict (e.g. a list), stop — don't extract
    # a nested dict from inside a top-level array.
    try:
        data = json.loads(stripped)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    # 2. Try extracting from a markdown code fence
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

    # 3. Try finding any JSON object anywhere in the text
    obj_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if obj_match:
        try:
            data = json.loads(obj_match.group())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Agent invocation
# ---------------------------------------------------------------------------


def invoke_agent(
    pred_entry: dict,
    run_id: str,
    repo_root: Path,
) -> dict:
    """
    Invoke the designated agent via the Claude runtime transport.

    Reads artifact content, builds prompts, invokes ``claude-sonnet-4-6``
    through the local ``claude`` CLI, and returns the raw result dict for
    validation by :func:`validate_semantic_result`.

    Parameters
    ----------
    pred_entry:
        The predicate dict from ``gate_rules_library.yaml`` (must include
        ``predicate_id``, ``function``, and ``args``).
    run_id:
        Current run UUID; ``${run_id}`` tokens in args are substituted.
    repo_root:
        Absolute path to the repository root.

    Returns
    -------
    dict
        Raw result from the agent, or a dispatch-error sentinel on failure.
        Always validate before use.  ``predicate_id`` and
        ``artifacts_inspected`` are always set by this function, not by
        the agent.
    """
    pred_id: str = pred_entry.get("predicate_id", "<unknown>")
    func_name: str = pred_entry.get("function", "")
    raw_args: dict = pred_entry.get("args") or {}

    if func_name not in SEMANTIC_REGISTRY:
        return _dispatch_error_result(
            pred_id,
            func_name,
            f"Unknown semantic predicate function {func_name!r}; "
            f"available: {sorted(SEMANTIC_REGISTRY)}",
        )

    config = SEMANTIC_REGISTRY[func_name]

    # Substitute ${run_id} tokens in string arg values
    resolved_args: dict = {
        k: v.replace("${run_id}", run_id) if isinstance(v, str) else v
        for k, v in raw_args.items()
    }

    # Read artifact content from disk
    artifact_contents, inspected_paths = _read_artifacts(resolved_args, repo_root)

    # Build prompts
    system_prompt = _build_system_prompt(config)
    user_prompt = _build_user_prompt(config, artifact_contents, resolved_args)

    # Invoke the agent via the Claude runtime transport
    try:
        response_text: str = invoke_claude_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=AGENT_MODEL,
            max_tokens=AGENT_MAX_TOKENS,
        )
    except ClaudeTransportError as exc:
        return _dispatch_error_result(
            pred_id,
            func_name,
            f"Claude transport failed for {func_name!r}: {exc}",
        )

    # Parse the agent's JSON response
    result = _extract_json(response_text)
    if result is None:
        return _dispatch_error_result(
            pred_id,
            func_name,
            f"Agent returned a non-JSON response for {func_name!r}: "
            f"{response_text[:300]!r}",
        )

    # Inject authoritative predicate_id (always override agent's value)
    result["predicate_id"] = pred_id

    # Set artifacts_inspected from ground truth (what we actually read),
    # not from the agent's self-report, for auditability.
    result["artifacts_inspected"] = inspected_paths

    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def dispatch_semantic_predicate(
    pred_entry: dict,
    run_id: str,
    repo_root: Path,
) -> dict:
    """
    Dispatch a single semantic predicate via the designated agent.

    Called by ``evaluate_gate()`` after all deterministic predicates have
    passed.  Delegates to :func:`invoke_agent`, which reads artifact
    content and invokes Claude through the runtime transport.

    The caller is responsible for validating the returned dict with
    :func:`validate_semantic_result` before treating it as authoritative.

    Parameters
    ----------
    pred_entry:
        The predicate dict from ``gate_rules_library.yaml``.
    run_id:
        Current run UUID; ``${run_id}`` tokens in args are substituted.
    repo_root:
        Absolute path to the repository root.

    Returns
    -------
    dict
        Raw semantic result.  May be malformed; always validate before use.
    """
    return invoke_agent(pred_entry, run_id, repo_root)
