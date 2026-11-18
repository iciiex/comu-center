# Kiloos Club — MODE: P demo image (FastAPI + SQLite on a persistent disk).
# The repo layout must be preserved: app/ finds db/migrations relative to itself.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md LICENSE.md ./
COPY app ./app
COPY db ./db
RUN pip install -e .

# Database + private evidence live on the mounted disk, never in the image.
# KILOOS_ENV, KILOOS_SECRET and KILOOS_DEMO_STAFF_CODE are supplied by the host.
ENV KILOOS_ENV=demo \
    KILOOS_DB=/var/data/kiloos.sqlite \
    KILOOS_EVIDENCE_DIR=/var/data/evidence \
    PORT=10000

EXPOSE 10000
# One worker only: rate-limit/session state is in memory and SQLite has a single writer.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
