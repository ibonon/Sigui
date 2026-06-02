# ── Sigui demo-ui — Dockerfile ────────────────────────────────────────────
# Minimal Next.js production image using node:20-slim
# The .next build is expected to already exist (built in the parent Dockerfile
# builder stage), so this image just serves it via `next start`.

FROM node:20-slim

LABEL maintainer="Eric Warma"
LABEL description="Sigui v3.0 — Next.js Command Center UI"

# Non-root user
RUN groupadd --gid 1001 nextjs \
 && useradd  --uid 1001 --gid nextjs --shell /bin/bash --create-home nextjs

WORKDIR /app

# Copy package manifests first (layer cache)
COPY --chown=nextjs:nextjs package*.json ./

# Install production dependencies only
RUN npm ci --omit=dev --prefer-offline

# Copy application source and built artefacts
COPY --chown=nextjs:nextjs . .

# Build the Next.js app (standalone output not required — standard build)
RUN npm run build

USER nextjs

EXPOSE 3000

# Health check — Next.js responds on /
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', r => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"

ENV NODE_ENV=production
ENV PORT=3000

CMD ["npm", "run", "start"]
