async function loadJson(path, options = {}) {
  const res = await fetch(path, {cache: 'no-store', ...options});
  return await res.json();
}

function setActionResult(text) {
  document.getElementById('action-result').textContent = text;
}

async function refreshAuth() {
  const payload = await loadJson('/auth/refresh', {method: 'POST'});
  setActionResult(JSON.stringify(payload, null, 2));
  await boot();
}

async function boot() {
  const meta = await loadJson('/meta');
  const health = await loadJson('/health');
  const model = await loadJson('/config-model');
  const auth = await loadJson('/auth/status');
  document.getElementById('version').textContent = `Version: ${meta.version}`;
  document.getElementById('health').textContent = `Gateway: ${health.gateway} | Panel: ${health.panel} | Workspace: ${health.workspace_root}`;
  document.getElementById('model').textContent = `Model: ${model.model || '(unset)'} | Provider: ${model.provider || '(unset)'}`;
  document.getElementById('auth').textContent = `Auth: ${auth.status} | Refresh: ${auth.can_refresh ? 'yes' : 'no'} | Expires in: ${auth.expires_in ?? 'n/a'}`;
}

document.getElementById('refresh-auth').addEventListener('click', () => {
  refreshAuth().catch(err => setActionResult(`Refresh failed: ${err}`));
});

boot().catch(err => {
  document.getElementById('health').textContent = `UI error: ${err}`;
});
