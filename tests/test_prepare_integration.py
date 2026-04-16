import json
from pathlib import Path

from hermes_agent_v2 import bootstrap


def test_prepare_creates_workspace_and_runtime_files(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    config_dir = tmp_path / 'config' / 'hermes'
    workspace = tmp_path / 'share' / 'hermes' / 'workspace'
    options = {
        'workspace_root': str(workspace),
        'llm_model': 'gpt-5.4',
        'enable_dashboard': True,
    }
    data.mkdir(parents=True)
    (data / 'options.json').write_text(json.dumps(options), encoding='utf-8')

    monkeypatch.setattr(bootstrap, 'DATA', data)
    monkeypatch.setattr(bootstrap, 'CONFIG_DIR', config_dir)
    monkeypatch.setattr(bootstrap, 'OPT_DATA', tmp_path / 'opt-data-missing')
    monkeypatch.setattr(bootstrap, 'MIGRATION_MARKER', data / 'runtime' / 'migration_v1_done')

    settings = bootstrap.prepare()

    assert settings['workspace_root'] == str(workspace)
    assert (workspace / 'exports').is_dir()
    assert (workspace / 'imports').is_dir()
    assert (workspace / 'scripts').is_dir()
    assert (data / '.env').exists()
    assert (data / 'config.yaml').exists()
    assert (data / 'auth' / 'session.json').exists()


def test_prepare_merges_config_override(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    config_dir = tmp_path / 'config' / 'hermes'
    workspace = tmp_path / 'share' / 'hermes' / 'workspace'
    override_path = config_dir / 'config.override.yaml'
    options = {
        'workspace_root': str(workspace),
        'config_override_path': str(override_path),
        'llm_model': 'gpt-5.4',
    }
    data.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    workspace.mkdir(parents=True)
    (data / 'options.json').write_text(json.dumps(options), encoding='utf-8')
    override_path.write_text('model:\n  provider: custom-provider\nextra_key: true\n', encoding='utf-8')

    monkeypatch.setattr(bootstrap, 'DATA', data)
    monkeypatch.setattr(bootstrap, 'CONFIG_DIR', config_dir)
    monkeypatch.setattr(bootstrap, 'OPT_DATA', tmp_path / 'opt-data-missing')
    monkeypatch.setattr(bootstrap, 'MIGRATION_MARKER', data / 'runtime' / 'migration_v1_done')

    bootstrap.prepare()

    config_text = (data / 'config.yaml').read_text(encoding='utf-8')
    assert 'custom-provider' in config_text
    assert 'extra_key: true' in config_text
