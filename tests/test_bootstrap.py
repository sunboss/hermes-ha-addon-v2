from pathlib import Path

from hermes_agent_v2 import bootstrap


def test_build_env_uses_share_workspace():
    env = bootstrap.build_env({})
    assert env['WORKSPACE_ROOT'] == '/share/hermes/workspace'


def test_deep_merge_overrides_nested_values():
    base = {'a': {'b': 1, 'c': 2}, 'x': 1}
    override = {'a': {'c': 9}, 'x': 5}
    merged = bootstrap._deep_merge(base, override)
    assert merged == {'a': {'b': 1, 'c': 9}, 'x': 5}
