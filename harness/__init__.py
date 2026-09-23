"""
Evaluation & Integrity Harness — out-of-band QA substrate (ticket E1).

This package is the out-of-band scaffolding every harness metric (E2–E9) stands
on.  It is **architecturally distinct from the runtime DAG**: ``harness`` may
import ``runner`` (to reuse the transport and read the deterministic predicate
registry), but ``runner`` never imports ``harness`` — an enforced one-way
dependency that makes "the harness is never a runtime gate" a structural fact,
not a promise.  A test (``tests/harness/test_boundary.py``) guards the direction.

The substrate, and the guardrails each piece enforces:

* :mod:`harness.verdict` — verdicts typed ``Inferred``, never ``Confirmed``; the
  N≥3 majority-vote scaffold for any score that will inform a decision.
* :mod:`harness.provenance` — ``{judge_model, judge_version, prompt_hash, score,
  rationale}`` logged for every verdict.
* :mod:`harness.routing` — deterministic-first routing: a property a deterministic
  predicate can check is never judged; the judge runs only in the semantic gap.
* :mod:`harness.judge` — a pinned, non-drafter judge (temp 0) over the
  OpenAI-compatible transport; grader–generator independence and no silent repair.
* :mod:`harness.report` — reporting-only output; advisory to a human, never a
  fail-closed runtime gate.

The boundary between this harness and the runtime is documented in
``harness/HARNESS.md``.

Constitutional authority:
    Subordinate to CLAUDE.md.  Nothing in this package evaluates a gate, invokes
    a pipeline agent, writes a canonical Tier 1–5 artifact, or modifies scheduler
    state.  Its outputs are ``Inferred`` evidence that advises human decisions
    *about* the pipeline (merges, prompt changes, model swaps, release cuts).
"""

from harness.verdict import (  # noqa: F401
    EVIDENCE_TYPE_INFERRED,
    MIN_MAJORITY_SAMPLES,
    MajorityVerdict,
    Verdict,
    majority_vote,
    validate_sample_count,
)
from harness.jsonl_log import JsonlLog  # noqa: F401
from harness.provenance import (  # noqa: F401
    REQUIRED_PROVENANCE_FIELDS,
    ProvenanceLog,
    ProvenanceRecord,
    prompt_hash,
)
from harness.routing import (  # noqa: F401
    DeterministicCoverageError,
    RoutingAuthority,
    RoutingDecision,
    assert_judgeable,
    deterministic_predicate_names,
    route,
    semantic_inrun_predicate_names,
)
from harness.judge import (  # noqa: F401
    DEFAULT_JUDGE_MAX_TOKENS,
    Judge,
    JudgeConfig,
    JudgeConfigError,
    JudgeError,
    JudgeIndependenceError,
    JudgeResponseError,
    JudgeResult,
    MajorityJudgeResult,
    drafter_models,
    resolve_judge_config,
)
from harness.report import (  # noqa: F401
    Finding,
    HarnessReport,
    build_report,
)

# -- E1.5 judge-reliability calibration ------------------------------------- #
from harness.gold_set import (  # noqa: F401
    RECOMMENDED_MAX_PAIRS,
    RECOMMENDED_MIN_PAIRS,
    TO_BE_LABELED,
    GoldPair,
    GoldSet,
    GoldSetError,
    gold_set_hash,
    load_gold_set,
    seed_pairs_from_claim_statuses,
    write_gold_set_template,
)
from harness.faithfulness import (  # noqa: F401
    FAITHFULNESS_METRIC,
    build_faithfulness_prompt,
    judge_pair_supported,
    resolve_source_text,
)
from harness.calibration import (  # noqa: F401
    DEFAULT_GRADUATION_THRESHOLD,
    GRADUATION_ADVISORY,
    GRADUATION_GATING_PERMITTED,
    CalibrationError,
    CalibrationLog,
    CalibrationReport,
    ConfusionMatrix,
    GraduationDecision,
    GraduationThreshold,
    calibrate,
    calibrate_with_judge,
    confusion_from_labels,
    graduation_for,
)

__all__ = [
    # verdict
    "EVIDENCE_TYPE_INFERRED",
    "MIN_MAJORITY_SAMPLES",
    "Verdict",
    "MajorityVerdict",
    "majority_vote",
    "validate_sample_count",
    # provenance
    "REQUIRED_PROVENANCE_FIELDS",
    "prompt_hash",
    "ProvenanceRecord",
    "ProvenanceLog",
    "JsonlLog",
    # routing
    "DeterministicCoverageError",
    "RoutingAuthority",
    "RoutingDecision",
    "deterministic_predicate_names",
    "semantic_inrun_predicate_names",
    "route",
    "assert_judgeable",
    # judge
    "DEFAULT_JUDGE_MAX_TOKENS",
    "JudgeError",
    "JudgeConfigError",
    "JudgeIndependenceError",
    "JudgeResponseError",
    "JudgeConfig",
    "JudgeResult",
    "MajorityJudgeResult",
    "Judge",
    "drafter_models",
    "resolve_judge_config",
    # report
    "Finding",
    "HarnessReport",
    "build_report",
    # E1.5 gold set
    "RECOMMENDED_MIN_PAIRS",
    "RECOMMENDED_MAX_PAIRS",
    "TO_BE_LABELED",
    "GoldPair",
    "GoldSet",
    "GoldSetError",
    "load_gold_set",
    "gold_set_hash",
    "seed_pairs_from_claim_statuses",
    "write_gold_set_template",
    # E1.5 faithfulness primitive
    "FAITHFULNESS_METRIC",
    "build_faithfulness_prompt",
    "resolve_source_text",
    "judge_pair_supported",
    # E1.5 calibration
    "GRADUATION_ADVISORY",
    "GRADUATION_GATING_PERMITTED",
    "DEFAULT_GRADUATION_THRESHOLD",
    "CalibrationError",
    "ConfusionMatrix",
    "GraduationThreshold",
    "CalibrationReport",
    "GraduationDecision",
    "confusion_from_labels",
    "calibrate",
    "calibrate_with_judge",
    "graduation_for",
    "CalibrationLog",
]
