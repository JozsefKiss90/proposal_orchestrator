"""The n07 budget gate node writes both of its artifacts.

`budget-interface-validation` declares two `writes_to` directories: the
integration validation directory and the Phase 7 phase-output directory.
It carried no `output_contract`, so the skill runtime took the
single-artifact path and landed exactly one file.  The skill then
declared `gate_pass_declaration: "pass"` and named a validation artifact
it had never written, `_determine_can_evaluate_exit_gate` found the
validation directory holding only `.gitkeep`, and the node failed at
`agent_body` with `INCOMPLETE_OUTPUT` before `gate_09` was ever
evaluated (CLAUDE.md §17.3.2, §17.6.6).

Two things were missing, and either alone is useless:

1. The integration validation artifact had no schema anywhere in
   `artifact_schema_specification.yaml`, and the sections the skill
   runtime searched did not cover `docs/integrations/` at all.  The
   multi-artifact writer skips an artifact whose schema declares no
   required fields, so it would have skipped this one.
2. The catalog entry declared no `output_contract`, so the second
   artifact could not be written even with a schema.

These tests pin both halves, and the invariant that makes the flat
multi-artifact response shape viable: the two artifacts' required field
names must not collide.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

import runner.agent_runtime as ar
import runner.skill_runtime as sr
from runner.skill_runtime import run_skill

REPO = Path(__file__).resolve().parents[2]
SPEC_REL = (
    ".claude/workflows/system_orchestration/artifact_schema_specification.yaml"
)
CATALOG_REL = ".claude/workflows/system_orchestration/skill_catalog.yaml"
MANIFEST_REL = ".claude/workflows/system_orchestration/manifest.compile.yaml"

VALIDATION_DIR = "docs/integrations/lump_sum_budget_planner/validation"
VALIDATION_PATH = f"{VALIDATION_DIR}/budget_validation_response.json"
ASSESSMENT_PATH = (
    "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/"
    "budget_gate_assessment.json"
)

# The eight fields the skill specification's Mode B output construction
# names for the validation artifact, in the order the schema declares
# them.  Order matters: the multi-artifact writer anchors on the first
# non-metadata required field, so a reordering changes the key Claude is
# asked for.
VALIDATION_FIELDS = (
    "validation_id",
    "validation_type",
    "contract_version",
    "validated_file_reference",
    "conformance_status",
    "non_conformance_findings",
    "structural_consistency_findings",
    "timestamp",
)
EXPECTED_VALIDATION_FIELDS = set(VALIDATION_FIELDS)


def _yaml(rel: str) -> dict:
    return yaml.safe_load((REPO / rel).read_text(encoding="utf-8-sig"))


def _catalog_entry(skill_id: str) -> dict:
    for entry in _yaml(CATALOG_REL)["skill_catalog"]:
        if entry.get("id") == skill_id:
            return entry
    raise AssertionError(f"no skill_catalog entry for {skill_id!r}")


def _schema_entry(rel_path: str) -> dict:
    entry = sr._find_schema_for_path(rel_path, REPO)
    assert entry is not None, f"no schema entry resolves {rel_path!r}"
    return entry


def _required(entry: dict) -> set[str]:
    _sid, req = sr._extract_schema_requirements(entry)
    return set(req)


# ---------------------------------------------------------------------------
# The schema the writer needs
# ---------------------------------------------------------------------------


class TestTheValidationArtifactHasASchema:
    """Without a schema the multi-artifact writer skips the artifact."""

    def test_the_canonical_path_resolves_to_a_schema_entry(self):
        assert _schema_entry(VALIDATION_PATH)["canonical_path"] == VALIDATION_PATH

    def test_it_declares_the_fields_the_skill_spec_names(self):
        assert _required(_schema_entry(VALIDATION_PATH)) == (
            EXPECTED_VALIDATION_FIELDS
        )

    def test_it_declares_them_in_the_order_the_writer_anchors_on(self):
        entry = _schema_entry(VALIDATION_PATH)
        assert sr._extract_schema_requirements(entry)[1] == list(
            VALIDATION_FIELDS
        )

    def test_it_declares_no_schema_id_so_no_run_id_is_demanded_of_it(self):
        """The skill spec's output table says run_id is not required here.

        ``_extract_schema_requirements`` returns the ``schema_id_value``,
        and the writer sets ``need_run_id`` from whether that is present.
        An absent value keeps the artifact free of both metadata fields,
        which is what the specification describes.
        """
        entry = _schema_entry(VALIDATION_PATH)
        assert entry.get("schema_id_value") is None
        assert "run_id" not in _required(entry)
        assert "schema_id" not in _required(entry)

    def test_it_lives_under_the_directory_the_catalog_declares(self):
        writes_to = _catalog_entry("budget-interface-validation")["writes_to"]
        assert any(
            VALIDATION_PATH.startswith(w.rstrip("/") + "/") for w in writes_to
        )

    def test_it_lives_under_the_artifact_the_manifest_registers(self):
        registry = _yaml(MANIFEST_REL)["artifact_registry"]
        entry = next(
            e for e in registry
            if e.get("artifact_id") == "a_int_budget_validation"
        )
        assert VALIDATION_PATH.startswith(entry["path"].rstrip("/") + "/")
        assert entry["tier"] == "integration_validation"


class TestTheSearchedSectionsReachTheIntegrationDirectory:
    """The section list was a closed set that stopped at Tier 2A."""

    def test_the_section_keys_are_one_shared_constant(self):
        assert isinstance(sr._SCHEMA_SECTION_KEYS, tuple)
        assert len(sr._SCHEMA_SECTION_KEYS) == len(set(sr._SCHEMA_SECTION_KEYS))

    def test_the_integration_validation_section_is_searched(self):
        assert "integration_validation_schemas" in sr._SCHEMA_SECTION_KEYS

    def test_every_searched_section_exists_or_is_tolerated(self):
        """A searched key naming no section is dead weight, not an error.

        ``checkpoint_schemas`` has always been such a key.  The point of
        this test is that the new key is not: it must name a real
        section, or the schema it was added for is unreachable.
        """
        spec = _yaml(SPEC_REL)
        assert isinstance(spec.get("integration_validation_schemas"), dict)


# ---------------------------------------------------------------------------
# The contract that lets both land
# ---------------------------------------------------------------------------


class TestTheSkillDeclaresTheMultiArtifactContract:

    def test_the_catalog_entry_declares_it(self):
        entry = _catalog_entry("budget-interface-validation")
        assert entry.get("output_contract") == "multi_artifact"

    def test_both_writes_to_entries_resolve_to_a_canonical_artifact(self):
        """Under the single-artifact path only ``dir_artifacts[0]`` is used.

        With the validation schema present and the contract absent, the
        whole parsed response would be written to whichever of the two
        resolved first — so the schema and the contract are a pair, not
        two independent improvements.
        """
        writes_to = _catalog_entry("budget-interface-validation")["writes_to"]
        resolved: list[str] = []
        spec = _yaml(SPEC_REL)
        for rel in writes_to:
            dir_norm = rel.rstrip("/")
            for key in sr._SCHEMA_SECTION_KEYS:
                section = spec.get(key)
                if not isinstance(section, dict):
                    continue
                for entry in section.values():
                    if not isinstance(entry, dict):
                        continue
                    cp = entry.get("canonical_path", "")
                    if cp.startswith(dir_norm + "/"):
                        resolved.append(cp)
        assert set(resolved) == {VALIDATION_PATH, ASSESSMENT_PATH}


class TestTheTwoArtifactsDoNotCollide:
    """The multi-artifact prompt demands one flat object for both."""

    def test_their_required_field_names_are_disjoint(self):
        validation = _required(_schema_entry(VALIDATION_PATH))
        assessment = _required(_schema_entry(ASSESSMENT_PATH))
        # schema_id and run_id are the writer's own metadata fields and
        # are stamped per artifact, not extracted by name collision.
        domain = {"schema_id", "run_id"}
        assert not (validation - domain) & (assessment - domain)

    def test_each_anchor_field_is_unique_to_its_artifact(self):
        """The writer detects the response shape from the first field.

        The anchor is the first required field that is not metadata, so
        the assessment anchors on ``gate_pass_declaration`` rather than
        on ``schema_id``.
        """
        meta = {"schema_id", "run_id"}

        def _anchor(rel_path: str) -> str:
            req = sr._extract_schema_requirements(_schema_entry(rel_path))[1]
            return [f for f in req if f not in meta][0]

        validation_anchor = _anchor(VALIDATION_PATH)
        assessment_anchor = _anchor(ASSESSMENT_PATH)
        assert validation_anchor == "validation_id"
        assert assessment_anchor == "gate_pass_declaration"
        assert validation_anchor not in _required(_schema_entry(ASSESSMENT_PATH))
        assert assessment_anchor not in _required(_schema_entry(VALIDATION_PATH))


# ---------------------------------------------------------------------------
# Behaviour: one response, two files
# ---------------------------------------------------------------------------

_TRANSPORT = "runner.skill_runtime.invoke_claude_text"


def _write_yaml(path: Path, data: Any) -> None:
    """Write *data* preserving key order.

    ``yaml.dump`` sorts keys by default, which would reorder the schema's
    ``fields`` and move the anchor field the writer keys on.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


@pytest.fixture
def budget_repo(tmp_path: Path) -> Path:
    """A synthetic repo carrying this skill's real two-artifact shape."""
    sr._catalog_cache.clear()
    sr._schema_spec_cache.clear()

    root = tmp_path
    _write_yaml(
        root / CATALOG_REL,
        {"skill_catalog": [{
            "id": "budget-interface-validation",
            "execution_mode": "cli-prompt",
            "output_contract": "multi_artifact",
            "reads_from": [],
            "writes_to": [
                VALIDATION_DIR + "/",
                "docs/tier4_orchestration_state/phase_outputs/"
                "phase7_budget_gate/",
            ],
            "constitutional_constraints": [],
        }]},
    )
    _write_yaml(
        root / SPEC_REL,
        {
            "integration_validation_schemas": {
                "budget_validation": {
                    "canonical_path": VALIDATION_PATH,
                    "fields": {
                        name: {"type": "string", "required": True}
                        for name in VALIDATION_FIELDS
                    },
                },
            },
            "tier4_phase_output_schemas": {
                "budget_gate_assessment": {
                    "schema_id_value": "orch.phase7.budget_gate_assessment.v1",
                    "canonical_path": ASSESSMENT_PATH,
                    "fields": {
                        "schema_id": {"type": "string", "required": True},
                        "run_id": {"type": "string", "required": True},
                        "gate_pass_declaration": {
                            "type": "string", "required": True,
                        },
                        "wp_coverage_results": {
                            "type": "array", "required": True,
                        },
                    },
                },
            },
        },
    )
    spec = root / ".claude/skills/budget-interface-validation.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("# budget-interface-validation\nspec.", encoding="utf-8")

    (root / VALIDATION_DIR).mkdir(parents=True, exist_ok=True)
    yield root

    sr._catalog_cache.clear()
    sr._schema_spec_cache.clear()


def _good_response(run_id: str) -> dict:
    """One flat object carrying both artifacts' fields, as prompted."""
    body = {name: f"value-for-{name}" for name in VALIDATION_FIELDS}
    body.update({
        "schema_id": "orch.phase7.budget_gate_assessment.v1",
        "run_id": run_id,
        "gate_pass_declaration": "pass",
        "wp_coverage_results": [{"wp_id": "WP1", "present_in_budget": True}],
    })
    return body


class TestOneResponseWritesBothFiles:

    def test_both_canonical_paths_are_written(self, budget_repo: Path):
        with patch(_TRANSPORT, return_value=json.dumps(_good_response("r1"))):
            result = run_skill(
                skill_id="budget-interface-validation",
                run_id="r1",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        assert result.status == "success", result.failure_reason
        assert set(result.outputs_written) == {VALIDATION_PATH, ASSESSMENT_PATH}
        assert (budget_repo / VALIDATION_PATH).is_file()
        assert (budget_repo / ASSESSMENT_PATH).is_file()

    def test_the_validation_file_carries_its_own_fields_only(
        self, budget_repo: Path
    ):
        with patch(_TRANSPORT, return_value=json.dumps(_good_response("r2"))):
            run_skill(
                skill_id="budget-interface-validation",
                run_id="r2",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        written = json.loads(
            (budget_repo / VALIDATION_PATH).read_text(encoding="utf-8-sig")
        )
        assert set(written) == EXPECTED_VALIDATION_FIELDS
        assert "gate_pass_declaration" not in written

    def test_the_assessment_still_carries_its_metadata(
        self, budget_repo: Path
    ):
        with patch(_TRANSPORT, return_value=json.dumps(_good_response("r3"))):
            run_skill(
                skill_id="budget-interface-validation",
                run_id="r3",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        written = json.loads(
            (budget_repo / ASSESSMENT_PATH).read_text(encoding="utf-8-sig")
        )
        assert written["run_id"] == "r3"
        assert written["schema_id"] == "orch.phase7.budget_gate_assessment.v1"
        assert written["gate_pass_declaration"] == "pass"

    def test_the_directory_now_holds_a_json_file_for_the_disk_check(
        self, budget_repo: Path
    ):
        """This is the condition that failed the node at ``agent_body``."""
        with patch(_TRANSPORT, return_value=json.dumps(_good_response("r4"))):
            run_skill(
                skill_id="budget-interface-validation",
                run_id="r4",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        json_files = [
            p for p in (budget_repo / VALIDATION_DIR).iterdir()
            if p.suffix == ".json" and p.is_file()
        ]
        assert len(json_files) == 1


class TestAnIncompleteResponseFailsRatherThanLandingHalf:

    def test_a_response_without_the_validation_fields_fails(
        self, budget_repo: Path
    ):
        partial = _good_response("r5")
        for f in EXPECTED_VALIDATION_FIELDS:
            partial.pop(f)
        with patch(_TRANSPORT, return_value=json.dumps(partial)):
            result = run_skill(
                skill_id="budget-interface-validation",
                run_id="r5",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        assert result.status == "failure"
        assert "validation_id" in (result.failure_reason or "")
        assert not (budget_repo / VALIDATION_PATH).exists()

    def test_nothing_is_written_when_one_artifact_fails_validation(
        self, budget_repo: Path
    ):
        """The writer validates every sub-artifact before any write."""
        broken = _good_response("r6")
        broken.pop("gate_pass_declaration")
        with patch(_TRANSPORT, return_value=json.dumps(broken)):
            result = run_skill(
                skill_id="budget-interface-validation",
                run_id="r6",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        assert result.status == "failure"
        assert not (budget_repo / VALIDATION_PATH).exists()
        assert not (budget_repo / ASSESSMENT_PATH).exists()


class TestItRefusesArtifactStatusRatherThanDroppingIt:
    """§17.6.5: its presence is a validation failure, not auto-correctable.

    The writer builds each sub-artifact from its schema's required
    fields, and ``artifact_status`` is declared optional. Without an
    explicit check it never reaches ``_validate_skill_output`` and is
    silently discarded — the single-artifact path fails on it, so
    routing this skill to the multi-artifact path would have turned a
    mandated failure into a silent repair.
    """

    def test_the_response_is_rejected(self, budget_repo: Path):
        stamped = _good_response("r9")
        stamped["artifact_status"] = "valid"
        with patch(_TRANSPORT, return_value=json.dumps(stamped)):
            result = run_skill(
                skill_id="budget-interface-validation",
                run_id="r9",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "artifact_status" in (result.failure_reason or "")

    def test_neither_artifact_is_written(self, budget_repo: Path):
        stamped = _good_response("r10")
        stamped["artifact_status"] = "valid"
        with patch(_TRANSPORT, return_value=json.dumps(stamped)):
            run_skill(
                skill_id="budget-interface-validation",
                run_id="r10",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        assert not (budget_repo / VALIDATION_PATH).exists()
        assert not (budget_repo / ASSESSMENT_PATH).exists()


class TestThePromptNamesBothAnchorFields:
    """Claude is told which top-level keys the flat response needs."""

    def test_both_anchors_appear_in_the_assembled_prompt(
        self, budget_repo: Path
    ):
        captured: dict[str, str] = {}

        def _capture(**kwargs):
            captured["prompt"] = kwargs.get("user_prompt", "") or ""
            captured["system"] = kwargs.get("system_prompt", "") or ""
            return json.dumps(_good_response("r7"))

        with patch(_TRANSPORT, side_effect=_capture):
            run_skill(
                skill_id="budget-interface-validation",
                run_id="r7",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        prompt = captured["prompt"]
        assert "Multi-Artifact Response Format" in prompt
        assert VALIDATION_PATH in prompt

        # The directive block, not the schema-hints lines above it. The
        # hints name every required field of both artifacts, so looking
        # for a field anywhere in the prompt proves nothing.
        directive = prompt.split("Multi-Artifact Response Format", 1)[1]
        assert '- "validation_id"' in directive
        assert '- "gate_pass_declaration"' in directive

    def test_the_directive_asks_for_no_metadata_field(
        self, budget_repo: Path
    ):
        """The anchor is the first required field that is not metadata.

        Taking the literal first field instead named ``schema_id`` for
        the assessment, so the prompt asked for a key the writer never
        looks for and never asked for ``gate_pass_declaration``.
        """
        captured: dict[str, str] = {}

        def _capture(**kwargs):
            captured["prompt"] = kwargs.get("user_prompt", "") or ""
            return json.dumps(_good_response("r8"))

        with patch(_TRANSPORT, side_effect=_capture):
            run_skill(
                skill_id="budget-interface-validation",
                run_id="r8",
                node_id="n07_budget_gate",
                repo_root=budget_repo,
            )
        directive = captured["prompt"].split(
            "Multi-Artifact Response Format", 1
        )[1]
        assert '- "schema_id"' not in directive
        assert '- "run_id"' not in directive

    def test_the_anchor_helper_skips_metadata(self):
        assert sr._anchor_field(["schema_id", "run_id", "x"]) == "x"
        assert sr._anchor_field(["x", "schema_id"]) == "x"
        assert sr._anchor_field(["schema_id", "run_id"]) is None
        assert sr._anchor_field([]) is None

    def test_the_writer_and_the_prompt_read_the_same_anchor(self):
        """One function now decides it; this pins that they agree.

        The real catalog entry and the real schemas are used, so a
        reordering of either schema's fields is caught here.
        """
        directive = sr._multi_artifact_directive(
            _catalog_entry("budget-interface-validation")["writes_to"], REPO
        )
        for rel_path in (VALIDATION_PATH, ASSESSMENT_PATH):
            req = sr._extract_schema_requirements(_schema_entry(rel_path))[1]
            assert f'- "{sr._anchor_field(req)}"' in directive

# ---------------------------------------------------------------------------
# The readiness check that failed the node
# ---------------------------------------------------------------------------


class TestTheExitGateReadinessCheckFlips:
    """`_determine_can_evaluate_exit_gate` is what blocked n07.

    It reads the manifest artifact registry and then the disk, so these
    tests use the real manifest against a scratch tree: the registry is
    the contract, the tree is what a skill run leaves behind.
    """

    def _paths(self) -> list[str]:
        return ar._get_artifacts_produced_by_node(
            "n07_budget_gate", REPO, manifest_path=REPO / MANIFEST_REL
        )

    def test_the_node_has_exactly_two_gate_relevant_artifacts(self):
        assert sorted(self._paths()) == sorted([
            "docs/integrations/lump_sum_budget_planner/validation/",
            "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/",
        ])

    def test_the_budget_request_is_not_one_of_them(self):
        """It is Tier 3 and carries no gate_dependency, so it cannot block."""
        assert not any("budget_request" in p for p in self._paths())

    def test_an_empty_validation_directory_still_blocks(self, tmp_path: Path):
        for rel in self._paths():
            (tmp_path / rel).mkdir(parents=True, exist_ok=True)
        (tmp_path / ASSESSMENT_PATH).write_text(
            json.dumps({"gate_pass_declaration": "pass"}), encoding="utf-8"
        )
        assert ar._determine_can_evaluate_exit_gate(
            "n07_budget_gate", tmp_path, manifest_path=REPO / MANIFEST_REL
        ) is False

    def test_the_canonical_validation_file_is_enough_to_let_the_gate_run(
        self, tmp_path: Path
    ):
        for rel in self._paths():
            (tmp_path / rel).mkdir(parents=True, exist_ok=True)
        (tmp_path / ASSESSMENT_PATH).write_text(
            json.dumps({"gate_pass_declaration": "pass"}), encoding="utf-8"
        )
        (tmp_path / VALIDATION_PATH).write_text(
            json.dumps({"validation_id": "x"}), encoding="utf-8"
        )
        assert ar._determine_can_evaluate_exit_gate(
            "n07_budget_gate", tmp_path, manifest_path=REPO / MANIFEST_REL
        ) is True

    def test_whatever_sits_in_validation_is_the_canonical_artifact(self):
        """g08_p03 only counts files, so this test reads them.

        The predicate is dir_non_empty: any .json releases it. So the
        directory must hold the canonical artifact and nothing else —
        a hand-placed file, or one under the old timestamped name, would
        pass the gate on something no skill produced. Empty is a valid
        state and passes here: the fix is the skill being able to write
        the artifact, not the file existing.
        """
        required = _required(_schema_entry(VALIDATION_PATH))
        found = [
            f for f in (REPO / VALIDATION_DIR).iterdir()
            if f.suffix == ".json" and f.is_file()
        ]
        assert [f.name for f in found] in ([], ["budget_validation_response.json"])
        for f in found:
            written = json.loads(f.read_text(encoding="utf-8-sig"))
            assert required <= set(written), (
                f"{f.name} is missing {sorted(required - set(written))}"
            )
