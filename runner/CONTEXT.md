# Orchestration runtime

The engine that executes the constitutional phase workflow as a gated graph of nodes. `CLAUDE.md`
defines these concepts; this file only pins the words used for them.

## Language

### Workflow

**Phase**:
One of the eight canonical, ordered stages of proposal preparation (CLAUDE.md §7).
_Avoid_: stage, step

**Node**:
One executable unit of the compiled workflow manifest, belonging to a phase.
_Avoid_: task, step, job

**Run**:
One execution of the workflow graph, identified by a run id.

**Gate**:
A deterministic check over artifacts on disk that decides whether a node may start (entry gate) or is
released (exit gate). Only the scheduler evaluates gates.
_Avoid_: check, validation, review

**Predicate**:
One deterministic condition a gate is made of.

**Gate result**:
The recorded outcome of one gate evaluation, including the fingerprints of the inputs it read.

**Fingerprint**:
The content hash of an artifact a gate read. A gate result stays fresh only while its fingerprints
still match.
_Avoid_: checksum, version

**Released**:
The state of a node whose exit gate passed.
_Avoid_: done, complete, passed

**Blocked**:
The state of a node stopped at its entry gate or at its exit; the cause is its failure origin.

**Failure origin**:
Where a node failed: its entry gate, its agent body, or its exit gate. Exactly one per failure.

**Hard block**:
The downstream freeze of every Phase 8 node when the budget gate fails.
_Avoid_: soft fail, hold

### Execution layers

**Agent**:
The execution component that carries out a node's body by sequencing skills and deterministic
components. Never an authority.
_Avoid_: worker, assistant

**Skill**:
One atomic Claude invocation governed by a skill specification. A skill never invokes another skill.
_Avoid_: tool, prompt, step

**Deterministic component**:
A Claude-free part of a node body that writes canonical artifacts with a determinism guarantee
(byte-equal replay or pure lookup). It is not a skill.
_Avoid_: helper, script

**Transport**:
The route by which a skill reaches Claude.
_Avoid_: API, backend (for this layer)

**Call Slicer**:
The deterministic pre-Claude pass that bounds call inputs to the selected call before any skill runs.

**Tool-augmented prompt mode (TAPM)**:
A skill invocation in which Claude reads its declared inputs from disk instead of receiving them in
the prompt.

### Artifacts and honesty

**Canonical pack**:
A deterministic reference artifact holding the exact source names (objectives, work packages,
partners, deliverables) that drafting must use verbatim.

**Reuse**:
Carrying a prior run's artifact forward under operator-approved reuse policy, bound by fingerprints.
_Avoid_: preseed

**Preseed**:
An operator copying a manually prepared Phase 8 section into its canonical place before the node
runs. It is not reuse.
_Avoid_: reuse, import

**Honest block**:
The default: a claim that cannot be grounded in Tiers 1–4 is Unresolved, and its section blocks.
_Avoid_: failure

**Working assumption**:
An unconfirmed fact the operator consciously declares in Tier 3, turning an honest block into an
Assumed claim (a conscious green).
_Avoid_: default, guess

### Graph track

**Dev graph**:
A rebuildable operational index over authoritative records. It is never source truth.
_Avoid_: knowledge graph, database

**Vault**:
A per-project set of linked notes that is compiled into Tier 3 data.

**Promotion**:
Moving compiled Tier 3 data from staging into the authoritative docs tree.
_Avoid_: sync, publish

## Relationships

- A **run** dispatches **nodes**; each node is **released** or **blocked** by its **gates**, which only the scheduler evaluates.
- An **agent** executes a node body through **skills** (Claude) and **deterministic components** (no Claude); skills reach Claude through the **transport**.
- **Reuse** and **preseed** are the only two ways an artifact from outside the current run enters it; they are never the same thing.
