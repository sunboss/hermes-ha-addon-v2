from fastapi.testclient import TestClient

from hermes_agent_v2.hermes_ui import server


def test_meta_exposes_version():
    client = TestClient(server.app)
    response = client.get('/meta')
    assert response.status_code == 200
    data = response.json()
    assert 'version' in data


def test_meta_declares_panel_websocket_capability():
    client = TestClient(server.app)
    response = client.get('/meta')
    assert response.status_code == 200
    data = response.json()
    assert data['panel_websocket_proxy'] is True
