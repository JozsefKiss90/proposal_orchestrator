# Graph Substrate — generic contract + deterministic vault reader (milestone 2, ticket 1)

This document is the human-readable contract for the milestone-2 graph substrate:
the **additive-superset schema**, the **`graph.config.yaml` binding contract**, and
the **deterministic vault reader**. It is the prefactor the compiler (tickets 3/6),
projector (ticket 4), and pack-from-graph (ticket 7) build on — the same
"substrate first" pattern milestone 1 used.

The authoritative, enforced definitions live in code:

| Concern | Module | Exception |
|---|---|---|
| Schema (vocab, Appendix-B lookup, front-matter validation) | `runner/graph_schema.py` | `GraphSchemaError` |
| `graph.config.yaml` binding contract | `runner/graph_config.py` | `GraphConfigError` |
| Deterministic vault reader | `runner/vault_reader.py` | `VaultReadError` |

Everything here is **project-agnostic** (D15): the schema and reader carry no
project bindings; the per-project `graph.config.yaml` carries them all. `MSCA/methodology_graph/`
is reference instance #1.

---

## 1. Additive-superset schema (D7)

The methodology-graph front-matter contract is extended to an **additive superset**.
Two invariants hold, verified by `tests/runner/test_vault_reader.py::test_all_87_methodology_nodes_validate_unchanged`:

1. Every one of the existing **87** methodology nodes still validates unchanged.
2. **No new required field** is introduced.

### 1.1 `node_type` vocabulary (23 = 15 + 8)

**Existing methodology types (15)** — generic methodology-graph categories, kept as-is:
`meta`, `governance`, `dashboard`, `source`, `architecture`, `state_of_the_art`,
`methodology_route`, `methodology_problem`, `decision_method`, `infrastructure_layer`,
`risk`, `swot`, `partner`, `concept`, `research_questions`.

**New Tier-3/4/5-binding types (8)** — introduced by milestone 2:
`proposal_section` (one per Part B sub-section — the headline authoring move),
`objective`, `outcome`, `impact`, `work_package`, `timeline`, `budget`,
`phase_gate_state` (the Tier-4 docs→graph mirror target).

> `risk` is **not** duplicated into the binding set — the existing methodology
> `risk` type already binds the Tier 3 risk register.

A node whose `node_type` is outside this set fails closed (naming the node).

### 1.2 Required core vs additive-optional

- **Required core (the whole required set):** `id`, `title`, `node_type`, `evidence_strength`.
  These are the load-bearing identity/provenance fields. The generic layer requires
  *only* these, so it bakes in no instance-#1 assumptions; an instance's own governance
  may require more (the 87 methodology nodes carry ~25 fields), but the substrate does not.
- **Additive-optional binding fields (new):** `tier`, `phase`, `artifact_path`, `sub_section_id`.
  A node that omits them is valid. When present, they are type-validated
  (`tier ∈ {tier1, tier2a, tier2b, tier3, tier4, tier5}`; `phase` an int or string label;
  `artifact_path`/`sub_section_id` non-empty strings).

### 1.3 Appendix-B mapping (`evidence_strength` → status), a pure lookup

Provenance is carried end-to-end via a **dict lookup — no inference**:

| `evidence_strength` | validation status (§12.2) |
|---|---|
| `source_grounded` | **Confirmed** |
| `synthesis` | **Inferred** |
| `inference` | **Inferred** |
| `unconfirmed` | **Unresolved** (not finalizable) |

Only `source_grounded` yields `Confirmed`; a `synthesis`/`inference`/`unconfirmed`
node can never land as a Confirmed fact — exactly what the drafting gates rely on.
`unconfirmed` maps to `Unresolved` (the un-declared default); the β assumption-applier
may later flip an *operator-declared* `Unresolved → Assumed` (D11) — a separate,
declared, deterministic step, **not** the reader's inference.

---

## 2. `graph.config.yaml` binding contract (D15)

The config binds a per-project vault's folders / `node_type`s → target tier and
canonical `docs/**` `artifact_path`, **generically**.

```yaml
project_id: any-opaque-instance-id      # required; not interpreted as content
vault_path: methodology_graph           # optional; node root relative to this file
bindings:
  - match: { node_type: proposal_section }
    tier: tier5
    artifact_path: docs/tier5_deliverables/proposal_sections
  - match: { folder: "04_methodological_routes" }
    tier: tier3                          # source-only (no artifact_path)
  - match: { folder: "11_objectives", node_type: objective }
    tier: tier3
    artifact_path: docs/tier3_project_instantiation/architecture_inputs/objectives.json
```

- A binding **matches** a node when *every* selector present in `match` matches:
  `folder` by path prefix (relative to the vault root), `node_type` exactly. An absent
  selector is a wildcard; a `match` with neither `folder` nor `node_type` fails closed.
- Bindings are scanned in file order; the **first** match wins — place specific
  bindings before general ones.
- `artifact_path` is optional. A binding without one is **source-only** (the compiler
  reads such nodes but writes no canonical artifact for them).
- `tier` is required and must be a known tier; a `match.node_type` must be a known
  `node_type`. Malformed bindings fail closed, naming `bindings[i]`.

The generic layer validates only the config *shape*; the concrete bindings live in
each project's file. The MSCA instance's real `graph.config.yaml` is authored when
the vault home is fixed (ticket 2) and extraction needs it (tickets 3/6/8).

---

## 3. Deterministic vault reader (D9-prefactor)

`read_vault(vault_dir, config=None) -> Vault` (in `runner/vault_reader.py`):

- **Pure & deterministic** — no Claude, no domain reasoning, no timestamps. Same vault
  ⇒ same parse (nodes ordered by relative path; wikilinks de-duplicated in first-seen order).
- Parses each `.md`: the **leading** front-matter block only (a `node_type:` inside a
  body code fence is *not* front-matter), the body prose, and wikilinks with **Obsidian
  basename resolution** — `[[Target]]`, `[[Target|Display]]`, `[[folder/Target#Heading]]`
  all resolve to the node whose file basename (or declared `alias`) is `Target`.
- Returns an indexed `Vault`: `by_id`, `by_basename`, alias resolution (`resolve_link`),
  config binding lookup (`binding_for`), and `dangling_links()`.
- **Fails closed, never silent** — a node with missing/malformed/unclosed front-matter,
  invalid YAML, a schema violation, or a duplicate `id`/basename raises `VaultReadError`
  **naming the node**. It never crashes and never silently skips a node.
- Dangling wikilinks are **recorded, not fatal** (a missing target is a graph-quality
  signal the compiler decides on, not a parse error). Dot-directories (`.obsidian`,
  `.trash`, …) are skipped as tooling, not graph content.

---

## 4. What ticket 1 deliberately does **not** do

No extraction, no output, no writes to `docs/**`. This is the read/validate substrate
only. Regenerating Tier 3 (ticket 3) and Part B section JSON (ticket 6) from the vault,
and the pack-from-graph deriver (ticket 7), are built on top of this reader.

---

## 5. Topology + stable paths (D8 / ticket 2 — resolved)

The embedded `MSCA/` git repo (gitlink, no `.gitmodules`) was **absorbed** into the
parent repo: `MSCA/**` is now tracked as ordinary files. Submodule was rejected —
the standalone vault is local-only (no remote), and the vault is the tightly-coupled
authoring surface of *this* repo. Full rationale + reversibility:
`docs/tier4_orchestration_state/decision_log/graph-topology-d8-absorb_2026-07-16.json`;
provenance: `docs/tier4_orchestration_state/reinstantiation_provenance.json`
(`topology_resolution_d8`). The pre-absorb history (pin SHA `b4d9e57`) is archived in
`MSCA-preabsorb-b4d9e57.bundle` (reproducible via `git clone`).

| Concern | Stable path (documented, in-tree) |
|---|---|
| Reference instance #1 vault (reader / `--from-graph` node root) | `MSCA/methodology_graph/` |
| Generic template home (ticket 5) | `templates/obsidian_graph_vault/` |

The reader takes the vault directory as an argument (path-agnostic by design), so the
paths above are documentation + defaults, not literals baked into the reader — the
agnosticism requirement (D15).
