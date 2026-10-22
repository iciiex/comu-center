# Foundation image for the provider-independent core.
# NOTE: this image runs the config/health CLI only — there is no HTTP server yet.
# An HTTP adapter (e.g. FastAPI) is a later, separately justified step (see docs/roadmap.md).
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Non-root runtime user (least privilege)
RUN groupadd --system invar && useradd --system --gid invar --home-dir /app invar

COPY pyproject.toml README.md LICENSE.md ./
COPY src ./src
RUN pip install --no-cache-dir . && chown -R invar:invar /app

USER invar

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD ["python", "-m", "invar_comms", "health"]

CMD ["python", "-m", "invar_comms", "config-check"]
