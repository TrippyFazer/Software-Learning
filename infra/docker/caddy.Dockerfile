# Caddy image with the React bundle baked in. Build context: repository root.
#
# Multi-stage build: Node exists only at build time; the shipped image is
# just Caddy + static files. No node process runs in production.

FROM node:22-slim AS webbuild
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM caddy:2
COPY infra/docker/Caddyfile /etc/caddy/Caddyfile
COPY --from=webbuild /web/dist /srv/www
