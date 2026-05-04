# ── ArcWarden v3.0 — Dockerfile ───────────────────────────────────────────────
# Multi-stage build: keeps the final image lean (~500 MB)
#
# Stage 1 (builder): install Python deps + build Next.js UI
# Stage 2 (runtime): copy artifacts, run uvicorn

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — builder
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Install Node.js 20 (for demo-ui build)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# ── Python dependencies (cached layer) ───────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Next.js UI build ──────────────────────────────────────────────────────────
COPY demo-ui/package*.json ./demo-ui/
RUN cd demo-ui && npm ci --prefer-offline

COPY demo-ui/ ./demo-ui/
RUN cd demo-ui && npm run build


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="Eric Warma"
LABEL description="ArcWarden v3.0 — Autonomous Security Oracle"
LABEL version="3.0.0"

# Install Node.js 20 (needed to run Next.js in production)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --gid 1001 arcwarden \
 && useradd  --uid 1001 --gid arcwarden --shell /bin/bash --create-home arcwarden

WORKDIR /app

# ── Copy Python site-packages from builder ────────────────────────────────────
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# ── Copy application source ───────────────────────────────────────────────────
COPY --chown=arcwarden:arcwarden . .

# ── Copy built Next.js artifacts ──────────────────────────────────────────────
COPY --from=builder --chown=arcwarden:arcwarden /build/demo-ui/.next      ./demo-ui/.next
COPY --from=builder --chown=arcwarden:arcwarden /build/demo-ui/node_modules ./demo-ui/node_modules

# ── Runtime directories ───────────────────────────────────────────────────────
RUN mkdir -p /app/db /app/logs /app/ecosystem \
 && chown -R arcwarden:arcwarden /app/db /app/logs /app/ecosystem

USER arcwarden

# ── Ports ─────────────────────────────────────────────────────────────────────
# 8000 — FastAPI (ArcWarden API)
# 3001 — Next.js (demo UI)
EXPOSE 8000 3001

# ── Healthcheck ───────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Default command — API only (UI is a separate service in docker-compose) ───
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
