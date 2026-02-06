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

# Get Valtimo from official Ritense image
FROM ritense/valtimo-backend:12.0.0 AS valtimo-base

# Production image - use Eclipse Temurin JRE (matches upstream)
FROM eclipse-temurin:17-jre-jammy

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for ExApp wrapper
RUN pip3 install --no-cache-dir \
    "fastapi>=0.109.0" \
    "uvicorn>=0.27.0" \
    "httpx>=0.26.0"

# Copy Valtimo JAR from upstream image
COPY --from=valtimo-base /app.jar /app/valtimo.jar

# Set up application directory
WORKDIR /app

# Copy ExApp wrapper
COPY ex_app /app/ex_app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create app directories
RUN mkdir -p /app/config /app/logs

# Environment variables (set by AppAPI)
ENV APP_HOST=0.0.0.0
ENV APP_PORT=9000
ENV PYTHONUNBUFFERED=1

# Valtimo configuration
ENV VALTIMO_PORT=8080
ENV JAVA_OPTS="-Xmx512m -Xms256m"

# Spring Boot / Valtimo defaults (override via AppAPI env vars)
ENV SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/valtimo
ENV SPRING_DATASOURCE_USERNAME=valtimo
ENV SPRING_DATASOURCE_PASSWORD=valtimo
ENV SERVER_PORT=8080

# Keycloak configuration (required)
ENV KEYCLOAK_AUTH_SERVER_URL=http://localhost:8081
ENV KEYCLOAK_REALM=valtimo

# Expose ports: 9000 for AppAPI, 8080 for Valtimo
EXPOSE 9000 8080

# Health check - just verify the wrapper is responding (any status is ok during init)
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD curl -s http://localhost:${APP_PORT:-9000}/heartbeat | grep -q status || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
