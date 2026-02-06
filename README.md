# Valtimo ExApp for Nextcloud

Nextcloud ExApp (External Application) that integrates [Valtimo](https://www.valtimo.nl/) BPM and case management.

## About This App

This is a **Nextcloud ExApp** that packages the Valtimo BPM platform as a containerized application managed by Nextcloud's AppAPI. When you install this app, Nextcloud will automatically deploy and manage the Valtimo container.

**For Valtimo documentation, see:** https://docs.valtimo.nl/

## What is Valtimo?

Valtimo is an open-source low-code platform for Business Process Automation, built on Camunda. It is designed for Dutch municipalities and government organizations as part of the [Common Ground](https://commonground.nl/) ecosystem.

Key features:
- BPMN workflow engine (Camunda-based)
- Case management with ZGW API compliance
- Form builder (Form.io-based dynamic forms)
- Document generation
- Integration with Common Ground components

## What This App Does

- Packages Valtimo as a Nextcloud ExApp
- Nextcloud automatically manages the container lifecycle
- Provides BPM and case management directly within Nextcloud
- Integrates with Nextcloud's AppAPI for seamless deployment

## Requirements

- Nextcloud 30 or higher
- AppAPI app installed and configured with a deploy daemon
- Docker environment for ExApp containers

### External Dependencies

Valtimo requires additional services for full functionality:

| Service | Purpose | Required |
|---------|---------|----------|
| PostgreSQL | Database | Yes |
| Keycloak | Authentication (OIDC) | Yes |
| RabbitMQ | Message broker | Optional |

## Installation

### Via Nextcloud App Store

1. Ensure AppAPI is installed and configured
2. Search for "Valtimo" in the Nextcloud app store
3. Click Install - Nextcloud will pull and start the container

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

Configure via Nextcloud Admin Settings or environment variables:

| Variable | Description |
|----------|-------------|
| `SPRING_DATASOURCE_URL` | JDBC PostgreSQL connection string |
| `SPRING_DATASOURCE_USERNAME` | Database username |
| `SPRING_DATASOURCE_PASSWORD` | Database password |
| `KEYCLOAK_AUTH_SERVER_URL` | Keycloak authentication server URL |
| `KEYCLOAK_REALM` | Keycloak realm name |

## Development

### Building the Docker Image

```bash
# Build locally
make build

# Push to registry
make push

# Test locally
make test
```

### Project Structure

```
valtimo/
├── appinfo/
│   └── info.xml          # ExApp manifest
├── ex_app/
│   └── lib/
│       └── main.py       # FastAPI wrapper for AppAPI
├── Dockerfile            # Container definition
├── entrypoint.sh         # Container startup
├── requirements.txt      # Python dependencies
└── Makefile              # Build automation
```

## Architecture

This ExApp uses a FastAPI wrapper that:

1. Implements AppAPI lifecycle endpoints (`/heartbeat`, `/init`, `/enabled`)
2. Starts and manages the Valtimo Spring Boot application
3. Proxies requests to the Valtimo backend
4. Reports health status back to Nextcloud

## Related Projects

| Project | Description | Links |
|---------|-------------|-------|
| **Valtimo** | BPM and case management platform | [Website](https://www.valtimo.nl/) / [Docs](https://docs.valtimo.nl/) / [GitHub](https://github.com/valtimo-platform) |
| **Nextcloud AppAPI** | External app framework | [GitHub](https://github.com/nextcloud/app_api) / [Docs](https://docs.nextcloud.com/server/latest/developer_manual/exapp_development/) |
| **OpenZaak** | ZGW API backend | [GitHub](https://github.com/open-zaak/open-zaak) |
| **OpenKlant** | Customer interaction registry | [GitHub](https://github.com/maykinmedia/open-klant) |

## License

AGPL-3.0 - See [LICENSE](LICENSE) for details.

## Author

[Conduction B.V.](https://conduction.nl) - info@conduction.nl
