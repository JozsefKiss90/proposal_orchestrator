---
skill_id: call-requirements-extraction
purpose_summary: >
  Extract binding topic-specific requirements from work programme and call extract
  documents, producing structured output with a source section reference for every
  extracted element.
used_by_agents:
  - call_analyzer
reads_from:
  - docs/tier2b_topic_and_call_sources/work_programmes/
  - docs/tier2b_topic_and_call_sources/call_extracts/
writes_to:
  - docs/tier2b_topic_and_call_sources/extracted/
constitutional_constraints:
  - "Must not invent call requirements not present in source documents"
  - "Must carry source section references for every extracted element"
  - "Must apply Confirmed/Inferred/Assumed/Unresolved status"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
