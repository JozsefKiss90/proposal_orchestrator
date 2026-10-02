'use strict';
const fs = require('fs');
const r = require('./ua-arch-results.json');
const nodes = JSON.parse(fs.readFileSync('.ua/intermediate/arch-filenodes.json', 'utf8'));
const G = r.directoryGroups;

const RUNNER = {
  'orchestration-runtime': ['__init__.py','__main__.py','dag_scheduler.py','agent_runtime.py','skill_runtime.py','semantic_dispatch.py','run_context.py','runtime_models.py','manifest_reader.py','node_resolver.py','call_slicer.py','phase8_preseed.py','phase8_reuse.py','phase8_skip_binding.py'],
  'gate-evaluation': ['gate_evaluator.py','gate_library.py','gate_result_registry.py'],
  'model-transport': ['claude_transport.py','json_extract.py'],
  'deterministic-components': ['deterministic_components.py','assumption_applier.py','section_assembler.py','phase8_canonical_pack.py','unit_cost_budget.py','budget_request.py','interface_contract.py','final_export_writer.py','docx_exporter.py','decomposed_drafting.py','checkpoint_publisher.py','instrument_profile.py','consortium_composition.py','dependency_normalizer.py'],
  'graph-substrate': ['graph_canonical_pack.py','graph_claim_verifier.py','graph_compiler.py','graph_config.py','graph_determinism_check.py','graph_projector.py','graph_schema.py','vault_reader.py','vault_scaffold.py','agnosticism_lint.py'],
  'shared-foundation': ['atomic_write.py','paths.py','versions.py','upstream_inputs.py','persistence_policy.py','working_assumptions.py','claim_status.py','source_index.py','leakage_scan.py','fingerprints.py'],
};

const buckets = {};
const put = (key, ids) => { (buckets[key] = buckets[key] || []).push(...ids); };

// runner top level, split semantically
const runnerIds = new Set(G['runner']);
for (const [key, files] of Object.entries(RUNNER)) {
  const ids = files.map((f) => 'file:runner/' + f);
  for (const id of ids) {
    if (!runnerIds.has(id)) throw new Error('unknown runner file: ' + id);
  }
  put(key, ids);
}

// directory groups mapped wholesale
put('gate-evaluation', G['runner/predicates']);
put('model-transport', G['runner/transport']);
put('graph-substrate', G['runner/dev_graph']);
put('workflow-specification', G['.claude/workflows']);
put('operator-tooling', G['tools']);
put('constitution', G['(root)']);
for (const g of ['harness','harness/commands','harness/gold_sets','harness/labeling','harness/materiality_sets','harness/profiles','harness/regression_baselines']) {
  put('evaluation-harness', G[g]);
}

const META = {
  'constitution': ['Constitution & Project Root', 'The repository constitution (CLAUDE.md) — the highest interpretive authority above every prompt, skill, workflow and agent instruction — together with the project build and dependency metadata that defines the package.'],
  'workflow-specification': ['Workflow Specification Spine', 'The declarative binding authority under .claude/workflows/system_orchestration: the compiled manifest that binds nodes to agents, skills, gate conditions and deterministic components, the agent and skill catalogues, the gate rules library, the eight per-phase node specs with their Phase-8 substeps, and the artifact schema specification with its 22 canonical artifact schemas.'],
  'orchestration-runtime': ['Orchestration Runtime Stack', 'The three-layer execution stack with exactly one caller each — DAGScheduler dispatching nodes, run_agent() sequencing a node body, run_skill() invoking Claude — plus the CLI entry point, manifest and node resolution, run-context persistence, runtime result contracts, the Step-0 call slicer and the Phase-8 reuse, preseed and skip-binding resolvers.'],
  'gate-evaluation': ['Gate Evaluation', 'Gate machinery owned exclusively by the scheduler: the gate evaluator (the single code-level caller of evaluate_gate), the gate rule library, the gate result registry, and the ten modules of atomic predicates that decide coverage, criteria, cycles, files, schemas, source refs, timelines and upstream gate passes.'],
  'model-transport': ['Model Transport', 'The transport boundary to the language model: the shared claude_transport adapter driving the local claude CLI in TAPM and cli-prompt modes, alternative Bedrock and OpenAI-compatible backends, transport configuration and capability negotiation, the tool-executor and tool loop, and the non-repairing JSON response extractor.'],
  'deterministic-components': ['Deterministic Components', 'Claude-free, node-body-scoped passes that read declared artifacts and write canonical ones under a byte-equal-replay or pure-lookup guarantee — distinct in kind from skills, which are defined by invoking a model: the component binding substrate plus the section assembler, assumption applier, canonical-pack deriver, unit-cost budget deriver, budget request builder, dependency normaliser, consortium-composition evaluator, instrument profile resolver, checkpoint publisher and the DOCX and final-export writers.'],
  'graph-substrate': ['Graph Substrate', 'The deliberately programme-agnostic knowledge-graph layer: the bidirectional Obsidian-vault to docs/ compiler and projector pair, the claim verifier and determinism-check auditors, the graph schema and config, the vault reader and scaffold, the dev_graph package that builds revisions, impact, packages and shadow snapshots over the repository own artifacts, and the agnosticism lint that proves no project vocabulary leaks in.'],
  'shared-foundation': ['Shared Foundation', 'Low-level primitives every other layer rests on, led by atomic_write (33 importers) and paths (17): atomic artifact writing, canonical path resolution, version and upstream-input resolution, the diagnostic persistence policy, the shared working-assumptions reader, the four-value Confirmed/Inferred/Assumed/Unresolved status vocabulary, content fingerprinting for gate staleness, the Tier 3 source-index verifier and the anonymity leakage scan.'],
  'evaluation-harness': ['Evaluation Harness', 'The out-of-band QA track behind a strict one-way boundary — it reads engine artifacts and imports runner, and the engine never imports it, with zero runner-to-harness edges in the graph: verdict, provenance, routing and judge substrate, coverage, grounding, faithfulness and contradiction graders, the claim ledger, evidence packs, calibration and regression machinery, the blind pre-evaluation lane, CLI command drivers, and the per-instrument rubric, scorecard, profile and gold-set assets. Its results are advisory and never run-blocking.'],
  'operator-tooling': ['Operator Tooling', 'Standalone operator scripts that import the engine but are never imported by it: dev-graph and Part B candidate builders, run phase-cost derivation, run-manifest preservation, a gate-result schema_id backfill, graph staging promotion and the prose detector.'],
};

const ORDER = ['constitution','workflow-specification','orchestration-runtime','gate-evaluation','deterministic-components','model-transport','graph-substrate','shared-foundation','evaluation-harness','operator-tooling'];

const layers = ORDER.map((k) => {
  const ids = buckets[k];
  if (!ids || ids.length === 0) throw new Error('empty layer ' + k);
  return { id: 'layer:' + k, name: META[k][0], description: META[k][1], nodeIds: ids };
});

// ---- validation ----
const seen = new Map();
for (const L of layers) {
  for (const id of L.nodeIds) {
    if (seen.has(id)) throw new Error('DUPLICATE ' + id + ' in ' + L.id + ' and ' + seen.get(id));
    seen.set(id, L.id);
  }
}
const all = new Set(nodes.map((n) => n.id));
const missing = [...all].filter((id) => !seen.has(id));
const extra = [...seen.keys()].filter((id) => !all.has(id));
if (missing.length) throw new Error('MISSING ' + missing.length + ': ' + missing.slice(0, 10).join(', '));
if (extra.length) throw new Error('EXTRA ' + extra.length + ': ' + extra.slice(0, 10).join(', '));

fs.mkdirSync('.ua/intermediate', { recursive: true });
fs.writeFileSync('.ua/intermediate/layers.json', JSON.stringify(layers, null, 2), 'utf8');
console.log('layers=' + layers.length + ' assigned=' + seen.size + '/' + all.size);
for (const L of layers) console.log('  ' + L.id.padEnd(36) + L.nodeIds.length);
