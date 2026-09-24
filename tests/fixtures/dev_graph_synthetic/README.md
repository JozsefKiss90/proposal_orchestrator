# Synthetic dev-graph fixture

A call-neutral repository skeleton for the dev-graph tests. It holds one synthetic
instrument registry entry (Tier 2A), and a Tier 3 set with three participants, two
objectives, one work package, tasks T01 to T03, one deliverable, one milestone and two source
materials; the work package is constrained by source two. A three-section candidate sits under `docs/tier5_deliverables/candidates/`
with four claims (one with a verified span into source one) and one commitment.

No real proposal text and no instance nouns. Tests copy this tree into a temporary
directory before building a snapshot, and mutate the copy for rejection cases.

The builder derives every edge from record structure. Tier 3 declares no
predicates of its own. The Tier 2A instrument entry and the selected call are
held for the later profile and policy tickets; the snapshot builder does not
index them.

The candidate is not imported in the fixture. Tests call `import_document` on
their copy, which writes the immutable record under
`docs/tier4_orchestration_state/dev_graph/documents/`, and then build.

The package tests ask for evidence around `T03` under each view policy. They tag a
source with `historical_feedback` on their copy to exercise the blind view, and add
assessment and artifact-version nodes to a built snapshot through `Snapshot.from_graph`
because no fixture record produces those types yet.
