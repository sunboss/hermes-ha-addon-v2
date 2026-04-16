# Architecture

## Runtime model

The add-on runs two long-lived services under a Python supervisor:

1. Hermes gateway
2. Ingress UI / local auth bridge / optional shim API

The supervisor is PID 1 and is responsible for:
- starting services in dependency order
- restarting or terminating cleanly on failure
- propagating signals
- writing runtime status to `/data/runtime/services.json`

## Storage model

### `/data`
Private add-on state only:
- `.env`
- `config.yaml`
- `auth/session.json`
- `logs/`
- `sessions/`
- `memories/`
- `skills/`
- `runtime/`

### `/share/hermes/workspace`
User-visible working directory for generated files, scripts, exports, and inputs.

### `/config/hermes`
Optional user override directory.
- `config.override.yaml` can override generated Hermes config

## Migration rule

`/opt/data` is never used as the steady-state runtime home.
If legacy files are found there, the bootstrap performs a one-time migration into `/data`
and writes a migration marker.

## Why this is better than v1

- No shell `source /data/.env`
- No hidden dependence on `/opt/data`
- No mixed internal/user workspace
- No fire-and-forget child processes
- HA directory mapping is explicit and matches user expectations
