async function loadJson(path) {
  const res = await fetch(path, {cache: 'no-store'});
  return await res.json();
}

async function boot() {
  const health = await loadJson('/health');
  const model = await loadJson('/config-model');
  const auth = await loadJson('/auth/status');
  document.getElementById('health').textContent = `Gateway: ${health.gateway} | Workspace: ${health.workspace_root}`;
  document.getElementById('model').textContent = `Model: ${model.model || '(unset)'} | Provider: ${model.provider || '(unset)'}`;
  document.getElementById('auth').textContent = `Auth: ${auth.status}`;
}

boot().catch(err => {
  document.getElementById('health').textContent = `UI error: ${err}`;
});
