# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim@sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205 AS build
WORKDIR /frontend
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY src ./src
COPY index.html tsconfig.json vite.config.ts vercel.json ./
COPY .env.production ./
ARG VITE_API_BASE_URL=https://api.staging.test:18443/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL VITE_USE_MOCK_API=false VITE_REQUIRE_AUTH=true
RUN npm run build

FROM nginx:1.30.6-alpine@sha256:47928bf67eb62a1863cb08d9ecb52d3e704304ba614eaee17884204677702951 AS proxy
COPY --from=build /frontend/dist /srv/frontend
USER 101:101
ENTRYPOINT ["nginx", "-g", "daemon off;"]
