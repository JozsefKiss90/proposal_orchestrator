# =============================================================================
# Proposal Orchestrator — Production Container
# =============================================================================
# Multi-stage build:
#   Stage 1 (builder): installs Python dependencies into a virtualenv
#   Stage 2 (runtime): copies only the virtualenv + application code
#
# Runtime uses the Bedrock Converse API (boto3) via IAM instance profile.
# No internet access is required at runtime.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL maintainer="Proposal Orchestrator" \
      description="Horizon Europe proposal orchestration engine" \
      version="1.0"

# Non-root user for runtime
RUN groupadd -r orchestrator && useradd -r -g orchestrator orchestrator

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Application root inside the container
WORKDIR /app

# Copy application code and data
COPY CLAUDE.md ./
COPY pyproject.toml ./
COPY runner/ ./runner/
COPY docs/ ./docs/
COPY .claude/agents/ ./.claude/agents/
COPY .claude/skills/ ./.claude/skills/
COPY .claude/workflows/ ./.claude/workflows/

# Create .git directory marker so find_repo_root() can locate the repo root.
# The runner requires both CLAUDE.md and .git/ to exist in the root.
RUN mkdir -p .git

# Create writable directories for runtime state
RUN mkdir -p .claude/runs .claude/cache .claude/logs \
    && chown -R orchestrator:orchestrator /app

USER orchestrator

# Health check: verify imports and config resolution
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from runner.transport.config import resolve_provider_config; resolve_provider_config()" || exit 1

ENTRYPOINT ["python", "-m", "runner"]
