from hermes_agent_v2.hermes_ui import server


def test_build_panel_ws_url_uses_ws_scheme_and_preserves_query():
    url = server._build_panel_ws_url('socket.io/', 'transport=websocket&sid=123')
    assert url == 'ws://127.0.0.1:9119/socket.io/?transport=websocket&sid=123'
