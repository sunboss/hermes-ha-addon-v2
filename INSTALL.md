# Install

## Home Assistant

1. Open Settings -> Add-ons -> Add-on Store.
2. Add the repository:
   `https://github.com/sunboss/hermes-ha-addon-v2`
3. Install `Hermes Agent V2`.
4. Start with these defaults:
   - `workspace_root: /share/hermes/workspace`
   - `auth_mode: api_key` unless you are wiring web login
   - `enable_dashboard: true`
5. Open the add-on web UI.

## Notes

- Internal runtime state is kept in `/data`.
- User-visible working files are kept in `/share/hermes/workspace`.
- Optional overrides go in `/config/hermes/config.override.yaml`.
- `/opt/data` is migration-only and should not be used for new setups.

## Current limitation

`/panel/*` is currently proxied over HTTP only. If the upstream dashboard requires websocket transport for a specific feature, that feature is not yet supported in this release.
