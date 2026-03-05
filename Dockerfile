# Valtimo ExApp for Nextcloud
# Wraps Valtimo BPM/case management with AppAPI integration
#
# Build: docker build -t ghcr.io/conductionnl/valtimo-exapp:latest .

# Get Valtimo from official Ritense image
FROM ritense/valtimo-backend:12.0.0 AS valtimo-base

# Runtime: Eclipse Temurin JRE + Python for ExApp wrapper
FROM eclipse-temurin:17-jre-jammy

# Install Python and runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        tini \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install ExApp Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy Valtimo JAR from upstream image
COPY --from=valtimo-base /app.jar /app/valtimo.jar

WORKDIR /app

# Copy ExApp wrapper
COPY ex_app/ ex_app/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create app directories
RUN mkdir -p /app/config /app/logs

# Environment
ENV APP_HOST=0.0.0.0
ENV APP_PORT=23000
ENV PYTHONUNBUFFERED=1
ENV VALTIMO_PORT=8080
ENV JAVA_OPTS="-Xmx512m -Xms256m"

# Spring Boot defaults (override via docker-compose env vars)
ENV SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/valtimo
ENV SPRING_DATASOURCE_USERNAME=nextcloud
ENV SPRING_DATASOURCE_PASSWORD=!ChangeMe!
ENV SERVER_PORT=8080

# Keycloak (required)
ENV KEYCLOAK_AUTH_SERVER_URL=http://localhost:8081
ENV KEYCLOAK_REALM=valtimo

EXPOSE 23000 8080

ENTRYPOINT ["/usr/bin/tini", "--", "./entrypoint.sh"]
