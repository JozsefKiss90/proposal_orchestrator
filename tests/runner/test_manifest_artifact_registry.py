"""
Manifest artifact-registry consistency (Phase 8 stepwise ticket 1).

Every ``produced_by`` / ``consumed_by`` id in the manifest
``artifact_registry`` must resolve against the manifest's own registries:

* node ids -> ``node_registry`` (producers and consumers),
* gate ids -> ``gate_registry`` (consumers only — gates consume artifacts
  as evidence, e.g. ``a_t5_part_b_assembled_draft``),
* the ``external_system`` sentinel (producer only — the lump-sum budget
  response is constitutionally produced outside this repository, §8.1).

Retired node ids (the pre-decomposition ``n08a_section_drafting`` /
``n08c_evaluator_review``) must not survive as dangling references, so any
feature that resolves registry entries can never land on a retired node.
"""

from __future__ import annotations

import pytest
import yaml

from runner.manifest_reader import MANIFEST_REL_PATH

#: Producer id documented in the artifact registry for artifacts produced
#: outside this repository (lump-sum budget responses, §8.1).
EXTERNAL_PRODUCER_SENTINEL = "external_system"


def _load_production_manifest() -> dict:
    from runner.paths import find_repo_root

    try:
        repo_root = find_repo_root()
    except RuntimeError:
        pytest.skip("repo root not discoverable in this environment")

    manifest_path = repo_root / MANIFEST_REL_PATH
    if not manifest_path.exists():
        pytest.skip("manifest.compile.yaml not present")

    with manifest_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _registry_ids(manifest: dict, registry: str, key: str) -> set[str]:
    return {
        entry[key]
        for entry in manifest.get(registry, [])
        if isinstance(entry, dict) and key in entry
    }


def _ref_ids(value: object) -> list[str]:
    """Normalise a produced_by/consumed_by field to a list of id strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


class TestArtifactRegistryNodeRefs:
    """artifact_registry references resolve against the manifest registries."""

    def test_all_artifact_refs_resolve(self) -> None:
        manifest = _load_production_manifest()

        node_ids = _registry_ids(manifest, "node_registry", "node_id")
        gate_ids = _registry_ids(manifest, "gate_registry", "gate_id")
        assert node_ids, "node_registry is empty or unreadable"
        assert gate_ids, "gate_registry is empty or unreadable"

        producer_vocab = node_ids | {EXTERNAL_PRODUCER_SENTINEL}
        consumer_vocab = node_ids | gate_ids

        artifact_registry = manifest.get("artifact_registry", [])
        assert artifact_registry, "artifact_registry is empty or unreadable"

        dangling: list[str] = []
        for entry in artifact_registry:
            if not isinstance(entry, dict):
                continue
            artifact_id = entry.get("artifact_id", "<missing artifact_id>")
            for ref in _ref_ids(entry.get("produced_by")):
                if ref not in producer_vocab:
                    dangling.append(f"{artifact_id}.produced_by: {ref}")
            for ref in _ref_ids(entry.get("consumed_by")):
                if ref not in consumer_vocab:
                    dangling.append(f"{artifact_id}.consumed_by: {ref}")

        assert not dangling, (
            "artifact_registry references ids that resolve to no node "
            "(or gate, for consumers) in the manifest registries — retired "
            "ids must be remapped to live nodes:\n  "
            + "\n  ".join(dangling)
        )

    def test_retired_phase8_node_ids_absent_from_artifact_registry(self) -> None:
        """
        The pre-decomposition Phase 8 node ids must not appear anywhere in
        the artifact registry (regression guard for the specific ticket-1
        retirement, sharper than the generic resolution check above).
        """
        manifest = _load_production_manifest()
        retired = {"n08a_section_drafting", "n08c_evaluator_review"}

        offenders: list[str] = []
        for entry in manifest.get("artifact_registry", []):
            if not isinstance(entry, dict):
                continue
            artifact_id = entry.get("artifact_id", "<missing artifact_id>")
            for field in ("produced_by", "consumed_by"):
                for ref in _ref_ids(entry.get(field)):
                    if ref in retired:
                        offenders.append(f"{artifact_id}.{field}: {ref}")

        assert not offenders, (
            "retired Phase 8 node ids still referenced:\n  "
            + "\n  ".join(offenders)
        )
