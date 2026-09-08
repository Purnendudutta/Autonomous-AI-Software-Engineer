# ─── Sandbox Image ────────────────────────────────────────────────────────────
# Minimal image for isolated code execution.
#
# Security properties:
#   - Non-root user
#   - No network access (enforced by Docker run flags in sandbox.py)
#   - CPU and memory limits set at container run time
#   - Read-only system filesystem (workspace is a tmpfs mount)
#   - No privilege escalation
#
# Phase 6 will extend this image with language-specific runtimes.

FROM python:3.12-slim

# Install only essential runtime tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --gid 1001 sandbox && \
    useradd --uid 1001 --gid sandbox --shell /bin/sh --no-create-home sandbox

# Workspace will be mounted at /workspace
WORKDIR /workspace

# Disable pip cache to reduce attack surface
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

USER sandbox

# Default entrypoint — overridden per-run by the backend's sandbox.py
ENTRYPOINT ["/bin/sh", "-c"]
CMD ["echo 'Sandbox ready'"]
