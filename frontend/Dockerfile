# Build stage: the Node toolchain never reaches the final image.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage: static files only, non-root (nginx-unprivileged listens on 8080).
FROM nginxinc/nginx-unprivileged:1.27.5-alpine
# Same reason as the backend: take Alpine security fixes newer than the base image, then drop back to the nginx user.
USER root
RUN apk upgrade --no-cache
USER 101
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
