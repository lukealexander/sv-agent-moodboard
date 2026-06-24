ARG NODE_VERSION=22

# ── dev ──────────────────────────────────────────────────────────────────────
FROM node:${NODE_VERSION}-slim AS dev

WORKDIR /app

COPY package.json .
RUN npm install

# Source is mounted at runtime; copy here for CI
COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]

# ── build ────────────────────────────────────────────────────────────────────
FROM node:${NODE_VERSION}-slim AS build

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

# Env vars must be passed at build time (VITE_ prefix bakes them in)
ARG VITE_LOCAL_DEV
ARG VITE_API_BASE_URL
ARG VITE_COGNITO_DOMAIN
ARG VITE_COGNITO_CLIENT_ID
ARG VITE_COGNITO_USER_POOL_ID
ARG VITE_COGNITO_REDIRECT_URI

ENV VITE_LOCAL_DEV=$VITE_LOCAL_DEV \
    VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_COGNITO_DOMAIN=$VITE_COGNITO_DOMAIN \
    VITE_COGNITO_CLIENT_ID=$VITE_COGNITO_CLIENT_ID \
    VITE_COGNITO_USER_POOL_ID=$VITE_COGNITO_USER_POOL_ID \
    VITE_COGNITO_REDIRECT_URI=$VITE_COGNITO_REDIRECT_URI

RUN npm run build

# ── prod ─────────────────────────────────────────────────────────────────────
FROM nginx:alpine AS prod

COPY --from=build /app/dist /usr/share/nginx/html

# SPA fallback: all routes serve index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
