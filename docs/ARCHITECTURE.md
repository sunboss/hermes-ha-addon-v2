# Architecture

## Runtime model

The add-on runs supervised long-lived services under a Python supervisor:

1. Hermes gateway
2. Hermes UI (FastAPI)
3. Hermes dashboard (optional, if supported by upstream image)

The supervisor is PID 1 and is responsible for:
- starting services in dependency order
- propagating signals
- terminating sibling processes on failure
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
User-visible workspace for scripts, exports, imports, and generated files.

### `/config/hermes`
Optional user override directory.
- `config.override.yaml` can override generated Hermes config

## Migration rule

`/opt/data` is never used as the steady-state runtime home.
If legacy files are found there, the bootstrap performs a one-time migration into `/data`
and writes a migration marker.

## Provider and auth model

The UI exposes a local shim at `/shim/v1/*`.
Selection order:
1. `OPENAI_BASE_URL` + `OPENAI_API_KEY`
2. `OPENROUTER_API_KEY`
3. `HUGGINGFACE_API_KEY`
4. Codex web login session

The auth bridge stores session state at `/data/auth/session.json` using atomic writes and 0600 permissions.
Pending OAuth login state has a hard 15-minute expiry.

## Why this is better than v1

- No shell `source /data/.env`
- No hidden dependence on `/opt/data`
- No mixed internal/user workspace
- No fire-and-forget child processes
- HA directory mapping is explicit and matches user expectations
- Basic shim routing is integrated instead of split across ad hoc wrappers
