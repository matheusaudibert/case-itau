# Node 24 traz o npm 11, a mesma versão que gerou o package-lock.json.
# Com o npm 10 (Node 22), o `npm ci` recusa o lockfile.
FROM node:24-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npx ng build --configuration production

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/estoque-frontend/browser /usr/share/nginx/html

EXPOSE 80
