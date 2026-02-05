# Valtimo for Nextcloud

Nextcloud integration app for [Valtimo](https://www.valtimo.nl/) BPM and case management.

## About This App

This is a **Nextcloud wrapper app** that provides integration between Nextcloud and an external Valtimo server. It does not contain the Valtimo platform itself - it connects your Nextcloud instance to a running Valtimo deployment.

**For Valtimo documentation, see:** https://docs.valtimo.nl/

## What This App Does

- Adds a Valtimo entry to the Nextcloud navigation
- Provides a UI within Nextcloud for managing cases and workflows
- Integrates Valtimo case management with Nextcloud files and users
- Bridges the Common Ground / ZGW ecosystem with Nextcloud

## What is Valtimo?

[Valtimo](https://www.valtimo.nl/) is an open-source BPM (Business Process Management) and case management platform for Dutch municipalities and government organizations. It is part of the [Common Ground](https://commonground.nl/) ecosystem.

Key features of Valtimo:
- **BPMN Workflow Engine** - Built on Camunda for process orchestration
- **Case Management** - ZGW API-compliant case handling
- **Document Generation** - Template-based document creation
- **Form Builder** - Form.io-based dynamic forms
- **SSO Integration** - Keycloak-based authentication

## Requirements

- Nextcloud 28 or higher
- PHP 8.0 or higher
- A running [Valtimo](https://docs.valtimo.nl/getting-started/first-dive/) server instance

## Installation

### From the Nextcloud App Store

Search for "Valtimo" in your Nextcloud app store and click Install.

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/ConductionNL/valtimo/releases)
2. Extract to your Nextcloud `apps` or `custom_apps` directory
3. Enable the app: `occ app:enable valtimo`

## Configuration

After installation, configure the Valtimo server URL in the Nextcloud admin settings.

## Development

```bash
# Install dependencies
composer install
npm install

# Build frontend
npm run build

# Watch for changes
npm run watch

# Run linting
composer phpcs
npm run lint
```

## Related Projects

| Project | Description | Links |
|---------|-------------|-------|
| **Valtimo** | BPM and case management platform | [Website](https://www.valtimo.nl/) / [Docs](https://docs.valtimo.nl/) / [GitHub](https://github.com/valtimo-platform) |
| **OpenZaak** | ZGW API backend (cases, documents) | [GitHub](https://github.com/open-zaak/open-zaak) / [Docs](https://open-zaak.readthedocs.io/) |
| **OpenKlant** | Customer interaction registry | [GitHub](https://github.com/maykinmedia/open-klant) |
| **Open Register** | Nextcloud register management | [GitHub](https://github.com/ConductionNL/openregister) |

## License

AGPL-3.0 - See [LICENSE](LICENSE) for details.

## Author

[Conduction B.V.](https://conduction.nl) - info@conduction.nl
