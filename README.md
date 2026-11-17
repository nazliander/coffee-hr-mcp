# coffee-hr

Example HR MCP server for Northfield Coffee, a fictional coffee bean company, built with [FastMCP](https://github.com/PrefectHQ/fastmcp).

It provides:

- Tools: `list_employees`, `request_pto` and `hr_dashboard` (an MCP App with metrics, a chart and a staff table).
- A payroll tool group mounted under the `payroll` namespace (`payroll_salary_report`, `payroll_employee_salary`), visible only to tokens with the `hr:comp:read` scope.
- Resources: the PTO policy (`hr://policies/pto`) and a template for employee profiles (`hr://employees/{employee_id}`).
- A prompt: `onboarding_checklist(name, department)`.
- JWT authentication, using your identity provider when `JWKS_URI` is set and local test keys otherwise.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker with Compose (optional, for the container setup)

## Setup

```bash
uv sync
```

This creates `.venv` and installs the locked dependencies from `uv.lock`, including the dev tools.

The project was created with:

```bash
uv init coffee-hr
uv add "fastmcp[apps]==4.2.0"
uv add --dev ruff
```

## Run locally

```bash
uv run server.py
```

The server listens on `http://localhost:8000/mcp`. Without `JWKS_URI` it prints two test tokens at startup:

- `HR_TOKEN` has the `hr:comp:read` scope.
- `STAFF_TOKEN` has no scopes.

Send either one as `Authorization: Bearer <token>`.

To compare what the two tokens can do:

```bash
uv run demo_auth.py
```

To preview the dashboard in a browser:

```bash
uv run fastmcp dev apps server.py
```

To add the server to Claude Desktop over stdio:

```bash
uv run fastmcp install claude-desktop server.py
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `JWKS_URI` | JWKS endpoint of your identity provider. If unset, local test keys are used. | unset |
| `JWT_ISSUER` | Expected token issuer. | `https://idp.example.com` |

The expected audience is `hr-mcp`.

## Linting and formatting

[Ruff](https://docs.astral.sh/ruff/) handles linting, formatting and import sorting. The rules are configured in `pyproject.toml`.

```bash
uv run ruff check .
```

```bash
uv run ruff format .
```

To apply automatic fixes, including import sorting:

```bash
uv run ruff check --fix .
```

## Docker

```bash
docker compose up --build
```

The image installs the locked dependencies with `uv sync --locked --no-dev`, so Ruff and other dev tools are not included. To use your identity provider, uncomment the `environment` block in `docker-compose.yml` and set `JWKS_URI` and `JWT_ISSUER`.

## Updating dependencies

```bash
uv lock --upgrade-package fastmcp
```

FastMCP and Prefab change between releases, so check the changelog before upgrading.
