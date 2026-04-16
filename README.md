# Hermes Agent HA Add-on V2

Version: 0.3.0

A rebuilt Home Assistant add-on for Hermes Agent with:
- explicit HA directory mapping (`/data` internal state, `/share/hermes/workspace` user workspace)
- supervised multi-process runtime
- no `/opt/data` dependency during steady state
- safer auth/session storage
- built-in provider shim and optional dashboard proxy
- auth refresh endpoint and versioned CI/release scaffolding

## Design goals

1. Keep Hermes internal runtime state inside `/data` only.
2. Expose a real HA-visible workspace via `/share/hermes/workspace`.
3. Avoid shell-sourcing generated env files.
4. Supervise child services instead of fire-and-forget background processes.
5. Treat `/opt/data` only as a one-time migration source.

## Current feature set

- Gateway supervision
- Optional `hermes dashboard` supervision and `/panel/*` HTTP proxy
- `/api/*` gateway proxy
- `/shim/v1/models`
- `/shim/v1/chat/completions`
- `/auth/status`, `/auth/start`, `/auth/exchange`, `/auth/refresh`, `/auth/logout`
- Config override file at `/config/hermes/config.override.yaml`
- GitHub Actions CI
- Release workflow for version tags

## Current limitation

- `/panel/*` websocket proxy is not implemented yet.
- The UI exposes this explicitly via `/meta -> panel_websocket_proxy: false`.

## Docs

- `docs/ARCHITECTURE.md`
- `INSTALL.md`
- `CHANGELOG.md`
