# 01 — Record the loaded environment and compatibility surface

Status: ready-for-agent
Blocked by: none
Candidate: none (no candidate is installed or pinned by this ticket)
Surface: development session, read-only
Effort: claude-workflow-efficiency
PRD: ../PRD.md

## Problem

Every compatibility and overlap judgement in the handoff rests on an environment nobody has recorded. The
repository shows what is present on disk. It does not show what loads.

Four specific gaps block the pilots.

1. The Matt Pocock skill set appears under both `.claude/skills/` and `.agents/skills/`. Whether both
   copies load in one session is unknown, so the duplicate-overhead claim is unproven in either direction.
2. A user-level `serena` MCP server is configured and failed to connect in at least one session. Its
   enabled tool footprint is unknown, and Headroom can register its own Serena.
3. `.claude/settings.json` sets `enableAllProjectMcpServers`, which loads `mcpvault`,
   `smart-connections` and `filesystem`. User-level plugins and MCP servers were never audited.
4. No startup context footprint is recorded, so no later measurement has a floor to subtract.

## Outcome

A committed environment record that a later ticket can cite. It states what loads, what is merely present,
and where the four execution boundaries lie.

## Scope

Inspection and recording only. Read configuration, resolve what the running session reports, and write the
record. Nothing is installed, enabled, disabled or reconfigured.

## Inputs

- Repository instructions: `CLAUDE.md`, `AGENTS.md`.
- Configured tracker: `.claude/skills/setup-matt-pocock-skills/issue-tracker-local.md`.
- Project configuration: `.mcp.json`, `.claude/settings.json`, `skills-lock.json`, `.claude/skills/`, `.agents/skills/`.
- User-level configuration and plugin discovery, inspected in place.
- The running session's own reports for version, authentication mode, model and context footprint.

## Deliverables

- `evidence/01-environment-record.md` under this effort directory.
- A boundary table naming the development session, the orchestrator runtime, the harness and judge, and
  the blind assessor, with the mechanism that separates each from the others.

## Acceptance criteria

- [ ] Records operating system, and whether sessions run native Windows or WSL.
- [ ] Records Claude Code version, authentication mode, and the active model and effort settings.
- [ ] Records effective skill resolution: for each duplicated skill name, which copy the session resolves,
      with the evidence used to determine it.
- [ ] Answers the duplicate-skill-overhead question with evidence, including a finding of no duplication if
      that is what the evidence shows.
- [ ] Records every MCP server reaching a session, separated into user-level and project-level, including
      `serena` and its observed connection behaviour.
- [ ] Records configured hooks and enabled plugins at both user and project level.
- [ ] Records the startup context footprint, with the method and its limits.
- [ ] Distinguishes, for every entry, present on disk from loaded in a session.
- [ ] Names the four execution boundaries and the mechanism separating each, including the assessor flags
      `--tools ""` and `--strict-mcp-config` and the out-of-repository working directory.
- [ ] Contains no credential, token, or personal filesystem path. Paths are repository-relative or redacted.
- [ ] No installation, enablement, or configuration change was made.

## Verification evidence

A second session repeats the record. Agreement, or any divergence with its cause, is appended to the
record. Divergence is a finding, not a failure.

## Cost and data handling

Negligible subscription usage. No new network endpoint, no new service, no separately metered spend. No
secret or personal path is copied into a planning artifact.

## Collisions

This ticket finds and reports collisions. It resolves none. Invocation-name collisions and duplicate MCP
registrations are recorded for tickets 04, 06 and 07 to act on.

## Rollback

The deliverable is a document. Reverting the file is the whole rollback.

## Non-goals

- Installing, enabling or disabling any plugin, skill or MCP server.
- Deleting an apparently duplicate skill copy. Reducing apparent duplication does not authorize deletion.
- Auditing candidate upstream repositories. That belongs to each candidate ticket.
- Measuring task usage. That is ticket 02.

## Comments
