FROM python:3.12-alpine AS build
WORKDIR /app
COPY . .
ARG SITE_URL=http://localhost:8080
ARG REPOSITORY_URL=https://github.com/
ENV SITE_URL=${SITE_URL} REPOSITORY_URL=${REPOSITORY_URL}
RUN python3 scripts/build.py && python3 scripts/check_site.py

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
