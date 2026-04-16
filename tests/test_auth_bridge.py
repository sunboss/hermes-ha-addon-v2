from datetime import timedelta

from hermes_agent_v2.hermes_ui import auth_bridge


def test_default_status_has_no_session(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_bridge, 'SESSION_PATH', tmp_path / 'session.json')
    monkeypatch.setattr(auth_bridge, 'AUTH_STORAGE_PATH', tmp_path)
    status = auth_bridge.get_status()
    assert status['has_session'] is False


def test_pending_login_expiry_is_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_bridge, 'SESSION_PATH', tmp_path / 'session.json')
    monkeypatch.setattr(auth_bridge, 'AUTH_STORAGE_PATH', tmp_path)
    monkeypatch.setattr(auth_bridge, 'AUTH_MODE', 'web_login')
    monkeypatch.setattr(auth_bridge, 'AUTH_PROVIDER', 'openai_web')
    monkeypatch.setattr(auth_bridge, 'OPENAI_OAUTH_CLIENT_ID', 'client')
    monkeypatch.setattr(auth_bridge, 'OPENAI_OAUTH_REDIRECT_URI', 'http://localhost/callback')
    monkeypatch.setattr(auth_bridge, 'OPENAI_OAUTH_SCOPES', 'openid profile')
    status_code, payload = auth_bridge.start_login()
    assert status_code == 200
    state = auth_bridge._load()
    pending = state['pending_login']
    expired = auth_bridge._now() - timedelta(minutes=1)
    pending['expires_at'] = expired.isoformat()
    state['pending_login'] = pending
    auth_bridge._save(state)
    status_code, payload = auth_bridge.complete_login('code', pending['state'])
    assert status_code == 400
    assert payload['error'] == 'pending_login_expired'
