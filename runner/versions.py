"""
Version constants matching the compiled manifest and gate rules library.

These are used by gate_pass_recorded to verify that a stored GateResult
was produced under the same manifest and library version as the current run.
A version mismatch indicates a stale artifact from a prior compilation.

Keep in sync with the header block of:
  .claude/workflows/system_orchestration/gate_rules_library.yaml
  .claude/workflows/system_orchestration/manifest.compile.yaml
"""

MANIFEST_VERSION: str = "1.1"
LIBRARY_VERSION: str = "1.0"
CONSTITUTION_VERSION: str = "21430b0"
