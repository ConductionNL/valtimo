<p align="center">
  <img src="img/app.svg" alt="Valtimo logo" width="80" height="80">
</p>

<h1 align="center">Valtimo</h1>

<p align="center">
  <strong>BPM workflow engine and case management for Nextcloud — powered by Camunda, ZGW-compliant, Common Ground compatible</strong>
</p>

<p align="center">
  <a href="https://github.com/ConductionNL/valtimo/releases"><img src="https://img.shields.io/github/v/release/ConductionNL/valtimo" alt="Latest release"></a>
  <a href="https://github.com/ConductionNL/valtimo/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-EUPL--1.2-blue" alt="License"></a>
</p>

---

> **DISCLAIMER**
>
> **Valtimo** is developed and maintained by [**Ritense**](https://www.ritense.com/). This Nextcloud app is a thin ExApp wrapper that packages Valtimo for deployment via Nextcloud's AppAPI. **Conduction B.V. does not provide support, licensing, guarantees, warranties, or services for the Valtimo platform itself.**
>
> For **support**, **licensing**, **pricing**, or **professional services**, contact Ritense directly:
>
> - Website: [https://www.ritense.com/](https://www.ritense.com/)
> - Valtimo platform: [https://www.valtimo.nl/](https://www.valtimo.nl/)
> - Documentation: [https://docs.valtimo.nl/](https://docs.valtimo.nl/)
> - Source code: [https://github.com/valtimo-platform/valtimo](https://github.com/valtimo-platform/valtimo)

## What is Valtimo?

[Valtimo](https://www.valtimo.nl/) is an open-source low-code platform for Business Process Automation, built on top of the [Camunda](https://camunda.com/) BPMN engine. Developed by [Ritense](https://www.ritense.com/), it is designed for Dutch municipalities and government organizations as part of the [Common Ground](https://commonground.nl/) ecosystem.

Key capabilities of the Valtimo platform:

- **BPMN Workflow Engine** -- Visual process modeling and execution powered by Camunda
- **Case Management** -- Structured case handling with ZGW API compliance
- **Form Builder** -- Dynamic forms based on Form.io for user tasks and data capture
- **Document Generation** -- Automated document creation from templates and case data
- **Common Ground Integration** -- Native support for ZGW APIs, Haal Centraal, and other Dutch government standards

## What This App Does

This is a **Nextcloud ExApp** (External Application) that wraps the Valtimo platform as a containerized application managed by Nextcloud's AppAPI:

- Packages Valtimo as a Docker container managed by Nextcloud
- Nextcloud automatically handles the container lifecycle (start, stop, health monitoring)
- Provides BPM and case management capabilities directly within the Nextcloud environment
- Implements AppAPI lifecycle endpoints for seamless integration

This wrapper does **not** modify or extend Valtimo itself. It provides the integration layer between Nextcloud's AppAPI and the upstream Valtimo application.

## Requirements

| Requirement | Details |
|-------------|---------|
| Nextcloud | 30 or higher |
| AppAPI | Installed and configured with a deploy daemon |
| Docker | Environment for ExApp containers |
| PostgreSQL | Database for Valtimo (required) |
| Keycloak | OIDC authentication provider (required) |
| RabbitMQ | Message broker (optional) |

## Installation

### Via Nextcloud App Store

1. Ensure the **AppAPI** app is installed and configured with a deploy daemon
2. Search for **"Valtimo"** in the Nextcloud External Apps section
3. Click **Install** -- Nextcloud will pull and start the container

### Manual Registration

```bash
# Register the ExApp with AppAPI
docker exec -u www-data nextcloud php occ app_api:app:register \
    valtimo your_daemon_name \
    --info-xml /path/to/appinfo/info.xml \
    --force-scopes

# Enable the ExApp
docker exec -u www-data nextcloud php occ app_api:app:enable valtimo
```

## Configuration

Configure via Nextcloud Admin Settings or environment variables on the ExApp container:

| Variable | Description |
|----------|-------------|
| `SPRING_DATASOURCE_URL` | JDBC PostgreSQL connection string (e.g., `jdbc:postgresql://host:5432/valtimo`) |
| `SPRING_DATASOURCE_USERNAME` | Database username |
| `SPRING_DATASOURCE_PASSWORD` | Database password |
| `KEYCLOAK_URL` | Keycloak server URL (e.g., `http://keycloak:8080`) |
| `KEYCLOAK_REALM` | Keycloak realm name (default: `commonground`) |
| `KEYCLOAK_CLIENT_ID` | OIDC client ID for this app (default: `valtimo`) |
| `KEYCLOAK_CLIENT_SECRET` | OIDC client secret for this app |

## Architecture

This ExApp uses a FastAPI wrapper that bridges Nextcloud's AppAPI with the Valtimo Spring Boot application:

1. **Lifecycle management** -- Implements AppAPI endpoints (`/heartbeat`, `/init`, `/enabled`) for container orchestration
2. **Application startup** -- Starts and manages the Valtimo Spring Boot process inside the container
3. **Request proxying** -- Routes incoming requests from Nextcloud to the Valtimo backend
4. **Health reporting** -- Monitors the Valtimo process and reports status back to Nextcloud

```
valtimo/
├── appinfo/
│   └── info.xml          # ExApp manifest (routes, env vars, metadata)
├── ex_app/
│   └── lib/
│       └── main.py       # FastAPI wrapper for AppAPI integration
├── Dockerfile            # Container definition
├── entrypoint.sh         # Container startup script
├── requirements.txt      # Python dependencies
└── Makefile              # Build automation
```

## Links

| Resource | URL |
|----------|-----|
| Valtimo website | [https://www.valtimo.nl/](https://www.valtimo.nl/) |
| Valtimo documentation | [https://docs.valtimo.nl/](https://docs.valtimo.nl/) |
| Valtimo source code | [https://github.com/valtimo-platform/valtimo](https://github.com/valtimo-platform/valtimo) |
| Ritense (developer) | [https://www.ritense.com/](https://www.ritense.com/) |
| This wrapper (GitHub) | [https://github.com/ConductionNL/valtimo](https://github.com/ConductionNL/valtimo) |
| Nextcloud AppAPI | [https://github.com/nextcloud/app_api](https://github.com/nextcloud/app_api) |
| AppAPI docs | [https://docs.nextcloud.com/server/latest/developer_manual/exapp_development/](https://docs.nextcloud.com/server/latest/developer_manual/exapp_development/) |

## License

EUPL-1.2 -- See [LICENSE](LICENSE) for details.

## Authors

**Wrapper app:** [Conduction B.V.](https://conduction.nl) -- info@conduction.nl

**Valtimo platform:** [Ritense](https://www.ritense.com/) -- see the [Valtimo GitHub organization](https://github.com/valtimo-platform) for contributors
