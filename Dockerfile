# Valtimo ExApp for Nextcloud
# Wraps Valtimo BPM/case management with AppAPI integration
#
# Valtimo is a less-code platform for Business Process Automation built on Camunda.
# It requires:
# - PostgreSQL or MySQL database
# - Keycloak for authentication
# - RabbitMQ for messaging (optional)
#
# See: https://docs.valtimo.nl/

# Stage 1: Python builder (Alpine for small pip install layer)
FROM alpine:3.22 AS python-builder

RUN apk add --no-cache python3 py3-pip python3-dev gcc musl-dev libffi-dev

WORKDIR /build
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages --prefix=/python-packages -r requirements.txt

# Stage 2: Get Valtimo JAR from official Ritense image
FROM ritense/valtimo-backend:13.17.0 AS valtimo-base

# Stage 3: Production image - Eclipse Temurin JRE with Python
FROM eclipse-temurin:17-jre-jammy

# Install Python runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=python-builder /usr/lib/python3.* /usr/lib/python3.10/
COPY --from=python-builder /usr/bin/python3 /usr/bin/python3
COPY --from=python-builder /usr/lib/libpython3* /usr/lib/
COPY --from=python-builder /usr/lib/libffi* /usr/lib/
COPY --from=python-builder /python-packages/lib/python3.12/site-packages/ /usr/lib/python3.10/site-packages/
COPY --from=python-builder /python-packages/bin/ /usr/bin/

# Copy Valtimo JAR from upstream image
COPY --from=valtimo-base /app.jar /app/valtimo.jar

# Set up application directory
WORKDIR /app

# Copy ExApp wrapper
COPY ex_app/ ex_app/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create app directories
RUN mkdir -p /app/config /app/logs

# Environment variables (set by AppAPI)
ENV APP_HOST=0.0.0.0
ENV APP_PORT=23000
ENV PYTHONUNBUFFERED=1

# Valtimo configuration
ENV JAVA_OPTS="-Xmx512m -Xms256m"

# Spring Boot / Valtimo defaults (override via AppAPI env vars)
ENV SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/valtimo
ENV SPRING_DATASOURCE_USERNAME=valtimo
ENV SPRING_DATASOURCE_PASSWORD=valtimo
ENV SERVER_PORT=8080

# Keycloak configuration (required)
ENV KEYCLOAK_AUTH_SERVER_URL=http://localhost:8081
ENV KEYCLOAK_REALM=valtimo

# Expose ports: 23000 for AppAPI, 8080 for Valtimo
EXPOSE 23000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD curl -s http://localhost:${APP_PORT:-23000}/heartbeat | grep -q status || exit 1

ENTRYPOINT ["./entrypoint.sh"]
