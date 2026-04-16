from __future__ import annotations

import os
import urllib.request
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from hermes_ui.auth_bridge import clear_session, complete_login, get_status, refresh_session, start_login
from hermes_ui.provider_shim import chat_completions as shim_chat_completions
from hermes_ui.provider_shim import list_models as shim_list_models

API_BASE = os.environ.get('HERMES_API_UPSTREAM', 'http://127.0.0.1:8642')
API_KEY = os.environ.get('API_SERVER_KEY', '')
STATIC_DIR = Path('/opt/hermes-ha-addon/hermes_ui/static')
CONFIG_PATH = Path(os.environ.get('HERMES_HOME', '/data')) / 'config.yaml'
PANEL_BASE = f"http://{os.environ.get('DASHBOARD_HOST', '127.0.0.1')}:{os.environ.get('DASHBOARD_PORT', '9119')}"
ADDON_VERSION = os.environ.get('ADDON_VERSION', '0.3.0')

app = FastAPI(title='Hermes Agent V2 UI')


def _proxy_raw(base_url: str, method: str, path: str, body: bytes | None = None, content_type: str | None = None) -> Response:
    url = f'{base_url}{path}'
    headers: dict[str, str] = {}
    if base_url == API_BASE and API_KEY:
        headers['Authorization'] = f'Bearer {API_KEY}'
    if content_type:
        headers['Content-Type'] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = resp.read()
            media_type = resp.headers.get('Content-Type', 'application/json')
            return Response(content=payload, status_code=resp.getcode(), media_type=media_type)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'upstream_unavailable:{type(exc).__name__}')


def _proxy_gateway(method: str, path: str, body: bytes | None = None, content_type: str | None = None) -> Response:
    return _proxy_raw(API_BASE, method, path, body, content_type)


def _proxy_panel(method: str, path: str, body: bytes | None = None, content_type: str | None = None) -> Response:
    return _proxy_raw(PANEL_BASE, method, path, body, content_type)


@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / 'index.html').read_text(encoding='utf-8')


@app.get('/app.js')
def app_js() -> FileResponse:
    return FileResponse(STATIC_DIR / 'app.js', media_type='application/javascript')


@app.get('/styles.css')
def styles_css() -> FileResponse:
    return FileResponse(STATIC_DIR / 'styles.css', media_type='text/css')


@app.get('/meta')
def meta() -> JSONResponse:
    return JSONResponse({
        'version': ADDON_VERSION,
        'panel_websocket_proxy': False,
    })


@app.get('/health')
def health() -> JSONResponse:
    gateway = 'starting'
    panel = 'disabled' if os.environ.get('ENABLE_DASHBOARD', 'true') != 'true' else 'starting'
    try:
        response = _proxy_gateway('GET', '/health')
        if 200 <= response.status_code < 300:
            gateway = 'ready'
    except Exception:
        gateway = 'starting'
    if os.environ.get('ENABLE_DASHBOARD', 'true') == 'true':
        try:
            response = _proxy_panel('GET', '/docs')
            if 200 <= response.status_code < 500:
                panel = 'ready'
        except Exception:
            panel = 'starting'
    return JSONResponse({'status': 'ok', 'gateway': gateway, 'panel': panel, 'workspace_root': os.environ.get('WORKSPACE_ROOT', '/share/hermes/workspace')})


@app.get('/config-model')
def config_model() -> JSONResponse:
    try:
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8')) or {}
        model = cfg.get('model') or {}
        if isinstance(model, dict):
            return JSONResponse({'model': str(model.get('default', '')), 'provider': str(model.get('provider', ''))})
        return JSONResponse({'model': str(model), 'provider': ''})
    except Exception:
        return JSONResponse({'model': '', 'provider': ''})


@app.get('/auth/status')
def auth_status() -> JSONResponse:
    return JSONResponse(get_status())


@app.post('/auth/start')
def auth_start() -> JSONResponse:
    status, payload = start_login()
    return JSONResponse(payload, status_code=status)


@app.post('/auth/exchange')
async def auth_exchange(request: Request) -> JSONResponse:
    body = await request.json()
    status, payload = complete_login(body.get('code'), body.get('state'))
    return JSONResponse(payload, status_code=status)


@app.post('/auth/refresh')
def auth_refresh() -> JSONResponse:
    status, payload = refresh_session()
    return JSONResponse(payload, status_code=status)


@app.post('/auth/logout')
def auth_logout() -> JSONResponse:
    return JSONResponse(clear_session())


@app.get('/shim/v1/models')
def shim_models() -> JSONResponse:
    return JSONResponse(shim_list_models())


@app.post('/shim/v1/chat/completions')
async def shim_chat(request: Request) -> JSONResponse:
    body = await request.json()
    status, payload = shim_chat_completions(body)
    return JSONResponse(payload, status_code=status)


@app.get('/panel')
def panel_root() -> RedirectResponse:
    return RedirectResponse('/panel/')


@app.api_route('/panel/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
async def panel_proxy(path: str, request: Request) -> Response:
    body = await request.body()
    qs = request.url.query
    upstream_path = '/' + path + (f'?{qs}' if qs else '')
    return _proxy_panel(request.method, upstream_path, body if body else None, request.headers.get('content-type'))


@app.api_route('/api/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
async def api_proxy(path: str, request: Request) -> Response:
    body = await request.body()
    qs = request.url.query
    upstream_path = '/' + path + (f'?{qs}' if qs else '')
    return _proxy_gateway(request.method, upstream_path, body if body else None, request.headers.get('content-type'))
