// app.js  —  Hermes Agent HA Add-on: Launcher UI Client
// =====================================================
// Version: 0.9.11 (Hermes upstream v2026.4.13 / v0.9.0)
//
// This page is a minimal launcher: two big buttons (official Hermes
// dashboard + ttyd terminal) and a status strip (model, gateway health).
// All heavy lifting — chat, auth, prompt history — moved to the upstream
// `hermes dashboard` web UI which we reverse-proxy at /panel/** via
// server.py.
//
// URL routing handled by server.py (NOT direct browser-to-gateway):
//   ./health        → local liveness + gateway ping
//   ./config-model  → reads /data/config.yaml → {model, provider}
//   ./models        → shim / gateway fallback
//   ./panel/        → upstream `hermes dashboard` (FastAPI)
//   ./ttyd/         → ttyd terminal WebSocket proxy

// Global error handler — catches runtime errors and uncaught promise rejections.
// Shows the red banner so users know JS is broken even when the file loaded fine.
window.onerror = function (msg, src, line, col, err) {
  var banner = document.getElementById("js-error-banner");
  if (banner) {
    banner.textContent =
      "Hermes UI 运行出错（" +
      (err && err.message ? err.message : msg) +
      "）。请强制刷新（Ctrl+Shift+R）或查看浏览器控制台（F12）。";
    banner.hidden = false;
  }
  return false; // don't suppress default console logging
};
window.onunhandledrejection = function (e) {
  console.error("[Hermes UI] unhandled promise rejection:", e.reason);
};

const uiText = {
  statuses: {
    checking: "检查中…",
    detecting: "识别中…",
    ready: "已就绪",
    gatewayStarting: "网关启动中…",
    unhealthy: "异常",
    unavailable: "不可用",
  },
  messages: {
    gatewayReady: "Hermes 网关已连通，全部接口可用。",
    gatewayStarting: "UI 已就绪，Hermes 网关还在初始化，稍候会自动刷新。",
    gatewayUnhealthy: "网关返回了非预期状态，可能需要查看日志排查。",
    gatewayUnreachable: "无法连接 Hermes 网关，请检查 add-on 日志后重试。",
  },
};

const modelNameEl = document.getElementById("model-name");
const modelProviderEl = document.getElementById("model-provider");
const healthStatusEl = document.getElementById("health-status");
const healthDetailEl = document.getElementById("health-detail");
const addonVersionEl = document.getElementById("addon-version");
const addonVersionDetailEl = document.getElementById("addon-version-detail");
const terminalCardEl = document.getElementById("launch-terminal");

function setText(el, text) {
  if (el) el.textContent = text;
}

function setHealth(state, label, detail) {
  if (healthStatusEl) {
    healthStatusEl.textContent = label;
    healthStatusEl.dataset.state = state;
  }
  if (healthDetailEl) {
    healthDetailEl.textContent = detail || "";
  }
}

async function loadModels() {
  // Prefer /config-model: it reads Hermes config.yaml directly and returns
  // both the default model name and the provider (openai-codex, huggingface,
  // openrouter, etc.). Falls back to /models (gateway /v1/models) when
  // /config-model is unavailable.
  try {
    const response = await fetch("./config-model");
    if (response.ok) {
      const data = await response.json();
      const modelId = data && data.model ? String(data.model) : "";
      const provider = data && data.provider ? String(data.provider) : "";
      if (modelId) {
        setText(modelNameEl, modelId);
        setText(modelProviderEl, provider ? provider : "");
        return;
      }
    }
  } catch (_) {
    /* fall through */
  }

  try {
    const response = await fetch("./models");
    if (!response.ok) {
      setText(modelNameEl, uiText.statuses.unavailable);
      return;
    }
    const data = await response.json();
    if (Array.isArray(data.data) && data.data.length > 0 && data.data[0].id) {
      setText(modelNameEl, data.data[0].id);
      setText(modelProviderEl, "");
      return;
    }
    setText(modelNameEl, uiText.statuses.unavailable);
  } catch (_) {
    setText(modelNameEl, uiText.statuses.unavailable);
  }
}

async function checkHealth() {
  try {
    const response = await fetch("./health");
    if (!response.ok) {
      throw new Error("HTTP " + response.status);
    }
    const data = await response.json();
    if (data.status === "ok") {
      if (data.gateway === "ready") {
        setHealth("ready", uiText.statuses.ready, uiText.messages.gatewayReady);
      } else {
        setHealth(
          "warning",
          uiText.statuses.gatewayStarting,
          uiText.messages.gatewayStarting
        );
        // Retry in 5s so the status auto-updates once the gateway is up.
        setTimeout(checkHealth, 5000);
      }
      return;
    }
    setHealth("error", uiText.statuses.unhealthy, uiText.messages.gatewayUnhealthy);
  } catch (_) {
    setHealth("error", uiText.statuses.unavailable, uiText.messages.gatewayUnreachable);
  }
}

async function loadMeta() {
  try {
    const response = await fetch("./meta");
    if (!response.ok) {
      throw new Error("HTTP " + response.status);
    }
    const data = await response.json();
    setText(addonVersionEl, data && data.version ? `v${data.version}` : "未知");
    const wsReady = data && data.panel_websocket_proxy ? "面板 WS 已启用" : "面板 WS 未启用";
    setText(addonVersionDetailEl, wsReady);
  } catch (_) {
    setText(addonVersionEl, "未知");
    setText(addonVersionDetailEl, "版本信息读取失败");
  }
}

function init() {
  // Seed neutral "checking..." labels — these also work when JS is blocked
  // because index.html already has Chinese placeholder text.
  setText(modelNameEl, uiText.statuses.detecting);
  setText(modelProviderEl, "");
  setText(addonVersionEl, uiText.statuses.detecting);
  setText(addonVersionDetailEl, "正在读取版本信息…");
  setHealth("checking", uiText.statuses.checking, "正在连接 Hermes 网关…");
  if (terminalCardEl) {
    terminalCardEl.addEventListener("click", function (event) {
      if (terminalCardEl.getAttribute("aria-disabled") === "true") {
        event.preventDefault();
      }
    });
  }
  Promise.all([loadModels(), loadMeta(), checkHealth()]);
}

init();
