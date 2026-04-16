# Hermes Agent HA Add-on V2

A rebuilt Home Assistant add-on for Hermes Agent with:
- explicit HA directory mapping (`/data` internal state, `/share/hermes/workspace` user workspace)
- supervised multi-process runtime
- no `/opt/data` dependency during steady state
- safer auth/session storage
- simpler ingress UI focused on reliability

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

See `docs/ARCHITECTURE.md` for full details.
