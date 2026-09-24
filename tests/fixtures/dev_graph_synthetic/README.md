# Synthetic dev-graph fixture

A call-neutral repository skeleton for the dev-graph tests. It holds one synthetic
instrument registry entry (Tier 2A), and a Tier 3 set with three participants, two
objectives, one work package, tasks T01 to T03, one deliverable and one milestone.

No real proposal text and no instance nouns. Tests copy this tree into a temporary
directory before building a snapshot, and mutate the copy for rejection cases.

The builder derives every edge from record structure. Tier 3 declares no
predicates of its own. The Tier 2A instrument entry and the selected call are
held for the later profile and policy tickets; the snapshot builder does not
index them.
