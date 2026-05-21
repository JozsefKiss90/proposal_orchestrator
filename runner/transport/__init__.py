"""
Transport abstraction layer for the Proposal Orchestrator.

This package provides backend-agnostic LLM transport infrastructure.
Currently contains only the local tool execution layer (TAPM
compatibility); actual LLM backend adapters will be added in a
subsequent migration phase.

Constitutional authority:
    Subordinate to CLAUDE.md.  This package does not evaluate gates,
    invoke agents, write canonical artifacts, or modify scheduler state.
"""
