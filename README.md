# Hermes Agent HA Add-on V2

A rebuilt Home Assistant add-on for Hermes Agent with:
- explicit HA directory mapping (`/data` internal state, `/share/hermes/workspace` user workspace)
- supervised multi-process runtime
- no `/opt/data` dependency during steady state
- safer auth/session storage
- built-in provider shim and optional dashboard proxy

## Design goals

1. Keep Hermes internal runtime state inside `/data` only.
2. Expose a real HA-visible workspace via `/share/hermes/workspace`.
3. Avoid shell-sourcing generated env files.
4. Supervise child services instead of fire-and-forget background processes.
5. Treat `/opt/data` only as a one-time migration source.

## Directory model

- `/data` — internal runtime state managed by the add-on
- `/share/hermes/workspace` — user-visible workspace
- `/config/hermes` — optional user overrides

## What changed from the old architecture

- `map:` now explicitly exposes HA directories users expect.
- `/data` is private state only; workspace moved to `/share/hermes/workspace`.
- `/opt/data` is migration-only, not runtime.
- A Python supervisor is PID 1.
- The UI server no longer hardcodes `/data` paths outside `HERMES_HOME` semantics.
- The auth bridge now uses atomic writes and enforces pending-login expiry.
- A local shim can route requests to OpenAI-compatible endpoints, OpenRouter, Hugging Face, or Codex web-login.

## Current feature set

- Gateway supervision
- Optional `hermes dashboard` supervision and `/panel/*` HTTP proxy
- `/api/*` gateway proxy
- `/shim/v1/models`
- `/shim/v1/chat/completions`
- `/auth/status`, `/auth/start`, `/auth/exchange`, `/auth/logout`
- Config override file at `/config/hermes/config.override.yaml`

## Notes

- `/panel/*` is currently HTTP proxy only. If the upstream dashboard depends on websocket features in specific views, that should be added in a later revision.
- The add-on defaults to `auth_mode=api_key`. Web login is available when OAuth client settings are provided.

See `docs/ARCHITECTURE.md` for full details.
