FROM node:18-alpine AS build

WORKDIR /app

# Install dependencies first for better layer caching
COPY package.json package-lock.json* ./
RUN npm ci --silent

COPY . .

# Vite will pick up VITE_API_URL from the .env file automatically

RUN npm run build

# ── Production stage ─────────────────────────────────────────────────────────
FROM node:18-alpine

WORKDIR /app

# Install serve globally
RUN npm install -g serve

COPY --from=build /app/dist /app/dist

EXPOSE 8080

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:8080/ || exit 1

# Cloud Run requires listening on $PORT (default 8080)
CMD ["serve", "-s", "dist", "-l", "8080"]
