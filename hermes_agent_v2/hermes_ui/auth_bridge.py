from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

AUTH_MODE = os.environ.get('AUTH_MODE', 'api_key')
AUTH_PROVIDER = os.environ.get('AUTH_PROVIDER', 'openai_web')
AUTH_STORAGE_PATH = Path(os.environ.get('AUTH_STORAGE_PATH', '/data/auth'))
SESSION_PATH = AUTH_STORAGE_PATH / 'session.json'
OPENAI_OAUTH_CLIENT_ID = os.environ.get('OPENAI_OAUTH_CLIENT_ID', '').strip()
OPENAI_OAUTH_REDIRECT_URI = os.environ.get('OPENAI_OAUTH_REDIRECT_URI', 'http://127.0.0.1:1455/auth/callback').strip()
OPENAI_OAUTH_SCOPES = os.environ.get('OPENAI_OAUTH_SCOPES', 'openid profile email offline_access').strip()
OPENAI_AUTH_URL = 'https://auth.openai.com/authorize'
OPENAI_TOKEN_URL = 'https://auth.openai.com/oauth/token'


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _default_state() -> dict[str, Any]:
    return {
        'mode': AUTH_MODE,
        'provider': AUTH_PROVIDER,
        'status': 'not_required' if AUTH_MODE == 'api_key' else 'needs_login',
        'session': None,
        'pending_login': None,
        'updated_at': None,
    }


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def _load() -> dict[str, Any]:
    if not SESSION_PATH.exists():
        return _default_state()
    try:
        loaded = json.loads(SESSION_PATH.read_text(encoding='utf-8'))
        return loaded if isinstance(loaded, dict) else _default_state()
    except Exception:
        return _default_state()


def _save(state: dict[str, Any]) -> None:
    state['updated_at'] = _now().isoformat()
    _atomic_write(SESSION_PATH, state)


def _oauth_ready() -> bool:
    return bool(OPENAI_OAUTH_CLIENT_ID and OPENAI_OAUTH_REDIRECT_URI and OPENAI_OAUTH_SCOPES)


def _expires_in_seconds(expires_at: str | None) -> int | None:
    if not expires_at:
        return None
    try:
        dt = datetime.fromisoformat(expires_at)
    except ValueError:
        return None
    return int((dt - _now()).total_seconds())


def get_status() -> dict[str, Any]:
    state = _load()
    session = state.get('session') if isinstance(state.get('session'), dict) else None
    status = state.get('status') or ('not_required' if AUTH_MODE == 'api_key' else 'needs_login')
    expires_at = session.get('expires_at') if session else None
    expires_in = _expires_in_seconds(expires_at)
    return {
        'mode': AUTH_MODE,
        'provider': AUTH_PROVIDER,
        'status': status,
        'ready': AUTH_MODE == 'api_key' or status == 'authenticated',
        'oauth_configured': _oauth_ready(),
        'has_session': bool(session),
        'account_id': session.get('account_id') if session else None,
        'expires_at': expires_at,
        'expires_in': expires_in,
        'can_refresh': bool(session and session.get('refresh_token')),
        'updated_at': state.get('updated_at'),
    }


def start_login() -> tuple[int, dict[str, Any]]:
    if AUTH_MODE != 'web_login':
        return 400, {'error': 'web_login_not_enabled'}
    if AUTH_PROVIDER != 'openai_web':
        return 501, {'error': 'provider_not_supported'}
    if not _oauth_ready():
        return 400, {'error': 'oauth_config_missing'}

    state = _load()
    verifier = secrets.token_urlsafe(72)
    created_at = _now()
    pending = {
        'state': secrets.token_urlsafe(24),
        'code_verifier': verifier,
        'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('='),
        'redirect_uri': OPENAI_OAUTH_REDIRECT_URI,
        'scopes': OPENAI_OAUTH_SCOPES,
        'created_at': created_at.isoformat(),
        'expires_at': (created_at + timedelta(minutes=15)).isoformat(),
    }
    state['pending_login'] = pending
    state['status'] = 'awaiting_callback'
    _save(state)

    params = urllib.parse.urlencode({
        'response_type': 'code',
        'client_id': OPENAI_OAUTH_CLIENT_ID,
        'redirect_uri': OPENAI_OAUTH_REDIRECT_URI,
        'scope': OPENAI_OAUTH_SCOPES,
        'state': pending['state'],
        'code_challenge': pending['code_challenge'],
        'code_challenge_method': 'S256',
    })
    return 200, {'auth_url': f'{OPENAI_AUTH_URL}?{params}'}


def _exchange_token(form_data: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(form_data).encode('utf-8')
    req = urllib.request.Request(
        OPENAI_TOKEN_URL,
        data=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('token_response_not_object')
    return payload


def _store_session(state: dict[str, Any], token_payload: dict[str, Any]) -> dict[str, Any]:
    access_token = token_payload.get('access_token')
    if not access_token:
        raise ValueError('missing_access_token')
    expires_in = int(token_payload.get('expires_in', 0) or 0)
    old_session = state.get('session') if isinstance(state.get('session'), dict) else {}
    session = {
        'access_token': access_token,
        'refresh_token': token_payload.get('refresh_token') or old_session.get('refresh_token'),
        'token_type': token_payload.get('token_type') or 'Bearer',
        'scope': token_payload.get('scope') or OPENAI_OAUTH_SCOPES,
        'account_id': token_payload.get('account_id') or old_session.get('account_id'),
        'obtained_at': _now().isoformat(),
        'expires_at': (_now() + timedelta(seconds=expires_in)).isoformat() if expires_in else None,
    }
    state['session'] = session
    state['pending_login'] = None
    state['status'] = 'authenticated'
    _save(state)
    return session


def complete_login(code: str | None, state_value: str | None) -> tuple[int, dict[str, Any]]:
    state = _load()
    pending = state.get('pending_login') if isinstance(state.get('pending_login'), dict) else None
    if not pending:
        return 400, {'error': 'no_pending_login'}

    expires_at = datetime.fromisoformat(str(pending['expires_at']))
    if _now() > expires_at:
        state['pending_login'] = None
        state['status'] = 'needs_login'
        _save(state)
        return 400, {'error': 'pending_login_expired'}

    if not code or state_value != pending.get('state'):
        return 400, {'error': 'state_mismatch_or_missing_code'}

    try:
        token_payload = _exchange_token({
            'grant_type': 'authorization_code',
            'client_id': OPENAI_OAUTH_CLIENT_ID,
            'code': code,
            'redirect_uri': pending['redirect_uri'],
            'code_verifier': pending['code_verifier'],
        })
    except urllib.error.HTTPError as exc:
        return 502, {'error': 'token_exchange_failed', 'status_code': exc.code}
    except Exception:
        return 502, {'error': 'token_exchange_failed'}

    try:
        _store_session(state, token_payload)
    except ValueError:
        return 502, {'error': 'token_exchange_incomplete'}
    return 200, {'ok': True, 'status': get_status()}


def refresh_session() -> tuple[int, dict[str, Any]]:
    state = _load()
    session = state.get('session') if isinstance(state.get('session'), dict) else None
    if AUTH_MODE != 'web_login':
        return 400, {'error': 'web_login_not_enabled'}
    if not session:
        return 400, {'error': 'session_missing'}
    refresh_token = session.get('refresh_token')
    if not refresh_token:
        return 400, {'error': 'refresh_token_missing'}
    try:
        token_payload = _exchange_token({
            'grant_type': 'refresh_token',
            'client_id': OPENAI_OAUTH_CLIENT_ID,
            'refresh_token': refresh_token,
        })
    except urllib.error.HTTPError as exc:
        return 502, {'error': 'refresh_failed', 'status_code': exc.code}
    except Exception:
        return 502, {'error': 'refresh_failed'}
    try:
        _store_session(state, token_payload)
    except ValueError:
        return 502, {'error': 'refresh_incomplete'}
    return 200, {'ok': True, 'status': get_status()}


def clear_session() -> dict[str, Any]:
    state = _load()
    state['session'] = None
    state['pending_login'] = None
    state['status'] = 'not_required' if AUTH_MODE == 'api_key' else 'needs_login'
    _save(state)
    return get_status()
