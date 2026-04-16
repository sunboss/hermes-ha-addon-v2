from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from hermes_ui.auth_bridge import _load as _load_auth_state

SHIM_MODEL_NAME = os.environ.get('OPENAI_SHIM_MODEL', 'gpt-5.4')
HF_BASE_URL = os.environ.get('HF_BASE_URL', 'https://api-inference.huggingface.co/v1').rstrip('/')
HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY', '')
OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', '').rstrip('/')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENAI_CODEX_RESPONSES_URL = os.environ.get('OPENAI_CODEX_RESPONSES_URL', 'https://chatgpt.com/backend-api/codex/responses')
OPENAI_CODEX_USER_AGENT = os.environ.get('OPENAI_CODEX_USER_AGENT', 'Mozilla/5.0 HermesAgentHAV2/0.2')


def _normalize_model(model: str | None) -> str:
    value = (model or '').strip()
    return value or SHIM_MODEL_NAME


def _choose_provider(model: str) -> str:
    if OPENAI_BASE_URL and OPENAI_API_KEY:
        return 'openai_compat'
    if OPENROUTER_API_KEY:
        return 'openrouter'
    if HUGGINGFACE_API_KEY:
        return 'huggingface'
    return 'codex_web'


def _openai_compat_chat(base_url: str, api_key: str, model: str, request_payload: dict[str, Any], extra_headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
    messages = request_payload.get('messages') or []
    if not messages:
        return 400, {'error': {'message': 'At least one message is required.', 'type': 'invalid_request_error'}}

    upstream: dict[str, Any] = {
        'model': model,
        'messages': messages,
        'stream': False,
    }
    for key in ('temperature', 'top_p', 'max_tokens', 'stop'):
        if key in request_payload:
            upstream[key] = request_payload[key]

    req = urllib.request.Request(
        f'{base_url}/chat/completions',
        data=json.dumps(upstream).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            **(extra_headers or {}),
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
            return resp.getcode(), payload if isinstance(payload, dict) else {'error': {'message': 'invalid_upstream_payload', 'type': 'upstream_error'}}
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode('utf-8'))
        except Exception:
            payload = {'error': {'message': f'upstream_http_{exc.code}', 'type': 'upstream_error'}}
        return exc.code, payload if isinstance(payload, dict) else {'error': {'message': 'upstream_error', 'type': 'upstream_error'}}
    except Exception as exc:
        return 502, {'error': {'message': f'upstream_failure:{type(exc).__name__}', 'type': 'upstream_error'}}


def _extract_text_from_codex(payload: dict[str, Any]) -> str:
    output = payload.get('output') or []
    chunks: list[str] = []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get('content') or []
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get('text'), str):
                        chunks.append(part['text'])
    if chunks:
        return ''.join(chunks)
    if isinstance(payload.get('output_text'), str):
        return payload['output_text']
    return ''


def _codex_web_chat(model: str, request_payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    auth = _load_auth_state()
    session = auth.get('session') if isinstance(auth.get('session'), dict) else None
    if not session or not session.get('access_token'):
        return 401, {'error': {'message': 'web_login_session_missing', 'type': 'auth_error'}}
    messages = request_payload.get('messages') or []
    if not messages:
        return 400, {'error': {'message': 'At least one message is required.', 'type': 'invalid_request_error'}}
    prompt = '\n'.join(
        f"{message.get('role', 'user')}: {message.get('content', '')}"
        for message in messages
        if isinstance(message, dict)
    )
    upstream = {
        'model': model,
        'input': prompt,
    }
    req = urllib.request.Request(
        OPENAI_CODEX_RESPONSES_URL,
        data=json.dumps(upstream).encode('utf-8'),
        headers={
            'Authorization': f"Bearer {session['access_token']}",
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': OPENAI_CODEX_USER_AGENT,
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        return exc.code, {'error': {'message': f'codex_http_{exc.code}', 'type': 'upstream_error'}}
    except Exception as exc:
        return 502, {'error': {'message': f'codex_failure:{type(exc).__name__}', 'type': 'upstream_error'}}
    assistant_text = _extract_text_from_codex(payload if isinstance(payload, dict) else {})
    return 200, {
        'id': payload.get('id') if isinstance(payload, dict) else f'chatcmpl-web-{int(time.time())}',
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': model,
        'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': assistant_text}, 'finish_reason': 'stop'}],
        'usage': payload.get('usage', {}) if isinstance(payload, dict) else {},
    }


def list_models() -> dict[str, Any]:
    return {'object': 'list', 'data': [{'id': SHIM_MODEL_NAME, 'object': 'model', 'owned_by': 'custom'}]}


def chat_completions(request_payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    model = _normalize_model(request_payload.get('model'))
    provider = _choose_provider(model)
    if provider == 'openai_compat':
        return _openai_compat_chat(OPENAI_BASE_URL, OPENAI_API_KEY, model, request_payload)
    if provider == 'openrouter':
        return _openai_compat_chat(
            'https://openrouter.ai/api/v1',
            OPENROUTER_API_KEY,
            model,
            request_payload,
            {'HTTP-Referer': 'https://github.com/sunboss/hermes-ha-addon-v2', 'X-Title': 'Hermes Agent HA Add-on V2'},
        )
    if provider == 'huggingface':
        return _openai_compat_chat(HF_BASE_URL, HUGGINGFACE_API_KEY, model, request_payload)
    return _codex_web_chat(model, request_payload)
