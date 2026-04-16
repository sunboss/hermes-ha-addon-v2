from __future__ import annotations

import json
import os
import secrets
import shutil
from pathlib import Path
from typing import Any

import yaml

DATA = Path('/data')
OPT_DATA = Path('/opt/data')
CONFIG_DIR = Path('/config/hermes')
MIGRATION_MARKER = DATA / 'runtime' / 'migration_v1_done'


def _mkdirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def _read_options() -> dict[str, Any]:
    path = DATA / 'options.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(content, encoding='utf-8')
    os.chmod(tmp, mode)
    tmp.replace(path)


def migrate_legacy_opt_data() -> None:
    if MIGRATION_MARKER.exists() or not OPT_DATA.exists():
        return
    candidates = ['auth.json', 'config.yaml', '.env', 'SOUL.md', 'auth', 'sessions', 'memories', 'skills']
    for name in candidates:
        src = OPT_DATA / name
        dst = DATA / name
        if not src.exists() or dst.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    _atomic_write(MIGRATION_MARKER, 'done\n', mode=0o644)


def build_env(options: dict[str, Any]) -> dict[str, str]:
    return {
        'HASS_URL': 'http://supervisor/core',
        'SUPERVISOR_TOKEN': os.environ.get('SUPERVISOR_TOKEN', ''),
        'HASS_TOKEN': os.environ.get('SUPERVISOR_TOKEN', ''),
        'API_SERVER_ENABLED': 'true',
        'API_SERVER_HOST': '127.0.0.1',
        'API_SERVER_PORT': '8642',
        'API_SERVER_KEY': secrets.token_urlsafe(24),
        'API_SERVER_MODEL_NAME': str(options.get('llm_model') or 'gpt-5.4'),
        'AUTH_MODE': str(options.get('auth_mode') or 'api_key'),
        'AUTH_PROVIDER': str(options.get('auth_provider') or 'openai_web'),
        'AUTH_STORAGE_PATH': str(DATA / 'auth'),
        'OPENAI_BASE_URL': str(options.get('openai_base_url') or ''),
        'OPENAI_API_KEY': str(options.get('openai_api_key') or ''),
        'OPENROUTER_API_KEY': str(options.get('openrouter_api_key') or ''),
        'HUGGINGFACE_API_KEY': str(options.get('huggingface_api_key') or ''),
        'HF_BASE_URL': str(options.get('hf_base_url') or 'https://api-inference.huggingface.co/v1'),
        'OPENAI_OAUTH_CLIENT_ID': str(options.get('openai_oauth_client_id') or ''),
        'OPENAI_OAUTH_REDIRECT_URI': str(options.get('openai_oauth_redirect_uri') or 'http://127.0.0.1:1455/auth/callback'),
        'OPENAI_OAUTH_SCOPES': str(options.get('openai_oauth_scopes') or 'openid profile email offline_access'),
        'OPENAI_SHIM_MODEL': str(options.get('llm_model') or 'gpt-5.4'),
        'WORKSPACE_ROOT': str(options.get('workspace_root') or '/share/hermes/workspace'),
        'HERMES_API_UPSTREAM': 'http://127.0.0.1:8642',
        'ENABLE_DASHBOARD': 'true' if bool(options.get('enable_dashboard', True)) else 'false',
    }


def write_env_file(env: dict[str, str]) -> Path:
    path = DATA / '.env'
    lines = ['# Managed by Hermes Agent V2']
    for key in sorted(env):
        value = str(env[key]).replace('\\', '\\\\').replace('"', '\\"')
        lines.append(f'{key}="{value}"')
    _atomic_write(path, '\n'.join(lines) + '\n')
    return path


def write_auth_state(env: dict[str, str]) -> None:
    path = Path(env['AUTH_STORAGE_PATH']) / 'session.json'
    if path.exists():
        return
    payload = {
        'mode': env['AUTH_MODE'],
        'provider': env['AUTH_PROVIDER'],
        'status': 'not_required' if env['AUTH_MODE'] == 'api_key' else 'needs_login',
        'session': None,
        'pending_login': None,
        'updated_at': None,
    }
    _atomic_write(path, json.dumps(payload, indent=2, sort_keys=True) + '\n')


def write_config(options: dict[str, Any], env: dict[str, str]) -> Path:
    path = DATA / 'config.yaml'
    config: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = yaml.safe_load(path.read_text(encoding='utf-8'))
            if isinstance(loaded, dict):
                config = loaded
        except Exception:
            config = {}

    provider = 'openai-codex'
    base_url = 'https://chatgpt.com/backend-api/codex'
    if env['OPENAI_BASE_URL'] and env['OPENAI_API_KEY']:
        provider = 'openai'
        base_url = env['OPENAI_BASE_URL']
    elif env['OPENROUTER_API_KEY']:
        provider = 'openrouter'
        base_url = 'https://openrouter.ai/api/v1'
    elif env['HUGGINGFACE_API_KEY'] and env['HF_BASE_URL']:
        provider = 'openai'
        base_url = env['HF_BASE_URL']

    config['model'] = {
        'default': str(options.get('llm_model') or 'gpt-5.4'),
        'provider': provider,
        'base_url': base_url,
    }
    terminal = config.setdefault('terminal', {})
    terminal['backend'] = 'local'
    terminal['cwd'] = env['WORKSPACE_ROOT']

    platforms = config.setdefault('platforms', {})
    homeassistant = platforms.setdefault('homeassistant', {})
    homeassistant['enabled'] = True
    extra = homeassistant.setdefault('extra', {})
    extra['watch_all'] = bool(options.get('watch_all', False))
    extra['cooldown_seconds'] = int(options.get('cooldown_seconds', 30))
    extra['watch_domains'] = list(options.get('watch_domains') or [])
    extra['watch_entities'] = list(options.get('watch_entities') or [])
    extra['ignore_entities'] = list(options.get('ignore_entities') or [])

    override_path = Path(str(options.get('config_override_path') or '/config/hermes/config.override.yaml'))
    if override_path.exists():
        try:
            override = yaml.safe_load(override_path.read_text(encoding='utf-8')) or {}
            if isinstance(override, dict):
                config = _deep_merge(config, override)
        except Exception:
            pass

    _atomic_write(path, yaml.safe_dump(config, sort_keys=False, allow_unicode=True), mode=0o644)
    return path


def prepare() -> dict[str, Any]:
    options = _read_options()
    workspace = Path(str(options.get('workspace_root') or '/share/hermes/workspace'))
    _mkdirs(
        DATA,
        DATA / 'auth',
        DATA / 'logs',
        DATA / 'sessions',
        DATA / 'memories',
        DATA / 'skills',
        DATA / 'runtime',
        CONFIG_DIR,
        workspace,
        workspace / 'exports',
        workspace / 'imports',
        workspace / 'scripts',
    )
    migrate_legacy_opt_data()
    env = build_env(options)
    write_env_file(env)
    write_auth_state(env)
    config_path = write_config(options, env)
    return {
        'options': options,
        'env': env,
        'config_path': str(config_path),
        'workspace_root': env['WORKSPACE_ROOT'],
        'ui_port': int(os.environ.get('ADDON_UI_PORT', '8099')),
        'dashboard_host': os.environ.get('DASHBOARD_HOST', '127.0.0.1'),
        'dashboard_port': int(os.environ.get('DASHBOARD_PORT', '9119')),
        'enable_dashboard': env['ENABLE_DASHBOARD'] == 'true',
    }
