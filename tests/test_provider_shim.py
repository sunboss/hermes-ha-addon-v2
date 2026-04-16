from hermes_agent_v2.hermes_ui import provider_shim


def test_choose_provider_prefers_openai_compat(monkeypatch):
    monkeypatch.setattr(provider_shim, 'OPENAI_BASE_URL', 'https://example.com/v1')
    monkeypatch.setattr(provider_shim, 'OPENAI_API_KEY', 'key')
    monkeypatch.setattr(provider_shim, 'OPENROUTER_API_KEY', '')
    monkeypatch.setattr(provider_shim, 'HUGGINGFACE_API_KEY', '')
    assert provider_shim._choose_provider('gpt-5.4') == 'openai_compat'


def test_choose_provider_falls_back_to_codex(monkeypatch):
    monkeypatch.setattr(provider_shim, 'OPENAI_BASE_URL', '')
    monkeypatch.setattr(provider_shim, 'OPENAI_API_KEY', '')
    monkeypatch.setattr(provider_shim, 'OPENROUTER_API_KEY', '')
    monkeypatch.setattr(provider_shim, 'HUGGINGFACE_API_KEY', '')
    assert provider_shim._choose_provider('gpt-5.4') == 'codex_web'
