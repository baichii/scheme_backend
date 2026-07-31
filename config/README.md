# Backend configuration

This directory is the authoritative source for backend-managed configuration.
Frontend pages must not edit these files or depend on their private sections.

`index.yaml` explicitly registers every Backend-owned configuration document.
The Frontend keeps an independent bundled snapshot for Offline mode.

Current groups:

- `environment_templates/`: environment connection templates.
- `scenario_types/`: scenario types, supported sides, and compatible environment templates.

Toolbox definitions, node icons, and side flags are Frontend presentation assets
and must not be added to this directory.
