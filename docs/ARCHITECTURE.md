# Architecture

Version: 0.4.0

## Runtime model

The add-on runs supervised long-lived services under a Python supervisor:
1. Hermes gateway
2. Hermes UI (FastAPI)
3. Hermes dashboard (optional, if supported by upstream image)

## Auth model

The auth bridge stores session state at `/data/auth/session.json` using atomic writes and 0600 permissions.
Supported lifecycle:
- start login
- exchange auth code
- refresh existing session
- logout

Pending OAuth login state has a hard 15-minute expiry.

## Provider shim

The local shim at `/shim/v1/*` selects providers in this order:
1. OpenAI-compatible endpoint
2. OpenRouter
3. Hugging Face Inference
4. Codex web-login session
