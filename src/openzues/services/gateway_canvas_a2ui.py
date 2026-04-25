from __future__ import annotations

import posixpath
from dataclasses import dataclass
from urllib.parse import unquote

A2UI_PATH = "/__openclaw__/a2ui"
CANVAS_WS_PATH = "/__openclaw__/ws"


@dataclass(frozen=True)
class CanvasA2uiAsset:
    content: bytes
    content_type: str


_A2UI_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OpenClaw Canvas A2UI</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    body { margin: 0; min-height: 100vh; background: #050b14; color: #eef7ff; }
    main { display: grid; gap: 16px; place-items: center; min-height: 100vh; padding: 32px; }
    .openclaw-a2ui-host {
      max-width: 760px;
      padding: 28px;
      border: 1px solid #1d3854;
      border-radius: 24px;
      background: #0a1624;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      background: #8bffca;
      color: #03100b;
      font-weight: 700;
    }
    code { color: #8bffca; }
  </style>
</head>
<body>
  <main>
    <section class="openclaw-a2ui-host">
      <p>OpenClaw Canvas A2UI scaffold is available.</p>
      <p>Use <code>window.openclawA2UI.sendUserAction(...)</code> to post node canvas actions.</p>
      <p>Bridge handler: <code>openclawCanvasA2UIAction</code>.</p>
      <button type="button" id="a2ui-demo-action">Send demo action</button>
    </section>
  </main>
  <script src="./a2ui.bundle.js"></script>
  <script>
    document.getElementById("a2ui-demo-action")?.addEventListener("click", () => {
      window.openclawA2UI?.sendUserAction?.({ type: "demo.hello" });
    });
  </script>
</body>
</html>
"""

_A2UI_BUNDLE_JS = """(() => {
  const handlerNames = ["openclawCanvasA2UIAction"];

  function postToNode(payload) {
    try {
      const raw = typeof payload === "string" ? payload : JSON.stringify(payload);
      for (const name of handlerNames) {
        const iosHandler = globalThis.webkit?.messageHandlers?.[name];
        if (iosHandler && typeof iosHandler.postMessage === "function") {
          iosHandler.postMessage(raw);
          return true;
        }
        const androidHandler = globalThis[name];
        if (androidHandler && typeof androidHandler.postMessage === "function") {
          androidHandler.postMessage(raw);
          return true;
        }
      }
    } catch {}
    return false;
  }

  function sendUserAction(userAction) {
    const id = userAction?.id || globalThis.crypto?.randomUUID?.() || String(Date.now());
    return postToNode({ userAction: { ...userAction, id } });
  }

  try {
    const cap = new URLSearchParams(globalThis.location?.search || "").get("oc_cap");
    const proto = globalThis.location?.protocol === "https:" ? "wss" : "ws";
    const capQuery = cap ? "?oc_cap=" + encodeURIComponent(cap) : "";
    const reloadSocket = new WebSocket(
      proto + "://" + globalThis.location.host + "/__openclaw__/ws" + capQuery,
    );
    reloadSocket.onmessage = (event) => {
      if (String(event.data || "") === "reload") {
        globalThis.location.reload();
      }
    };
  } catch {}

  globalThis.openclawA2UI = { postToNode, sendUserAction };
  globalThis.OpenClaw = globalThis.OpenClaw || {};
  globalThis.OpenClaw.postMessage = postToNode;
  globalThis.OpenClaw.sendUserAction = sendUserAction;
  globalThis.openclawPostMessage = postToNode;
  globalThis.openclawSendUserAction = sendUserAction;
})();
"""

_A2UI_ASSETS = {
    "index.html": CanvasA2uiAsset(
        content=_A2UI_INDEX_HTML.encode("utf-8"),
        content_type="text/html; charset=utf-8",
    ),
    "a2ui.bundle.js": CanvasA2uiAsset(
        content=_A2UI_BUNDLE_JS.encode("utf-8"),
        content_type="application/javascript; charset=utf-8",
    ),
}


def get_canvas_a2ui_asset(asset_path: str | None) -> CanvasA2uiAsset | None:
    normalized = _normalize_a2ui_asset_path(asset_path)
    if normalized is None:
        return None
    return _A2UI_ASSETS.get(normalized)


def inject_canvas_live_reload(html: str) -> str:
    snippet = f"""
<script>
(() => {{
  const handlerNames = ["openclawCanvasA2UIAction"];
  function postToNode(payload) {{
    try {{
      const raw = typeof payload === "string" ? payload : JSON.stringify(payload);
      for (const name of handlerNames) {{
        const iosHandler = globalThis.webkit?.messageHandlers?.[name];
        if (iosHandler && typeof iosHandler.postMessage === "function") {{
          iosHandler.postMessage(raw);
          return true;
        }}
        const androidHandler = globalThis[name];
        if (androidHandler && typeof androidHandler.postMessage === "function") {{
          androidHandler.postMessage(raw);
          return true;
        }}
      }}
    }} catch {{}}
    return false;
  }}
  function sendUserAction(userAction) {{
    const id =
      (userAction && typeof userAction.id === "string" && userAction.id.trim()) ||
      (globalThis.crypto?.randomUUID?.() ?? String(Date.now()));
    const action = {{ ...userAction, id }};
    return postToNode({{ userAction: action }});
  }}
  globalThis.OpenClaw = globalThis.OpenClaw ?? {{}};
  globalThis.OpenClaw.postMessage = postToNode;
  globalThis.OpenClaw.sendUserAction = sendUserAction;
  globalThis.openclawPostMessage = postToNode;
  globalThis.openclawSendUserAction = sendUserAction;

  try {{
    const cap = new URLSearchParams(location.search).get("oc_cap");
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const capQuery = cap ? "?oc_cap=" + encodeURIComponent(cap) : "";
    const ws = new WebSocket(proto + "://" + location.host + "{CANVAS_WS_PATH}" + capQuery);
    ws.onmessage = (ev) => {{
      if (String(ev.data || "") === "reload") location.reload();
    }};
  }} catch {{}}
}})();
</script>
""".strip()
    marker = "</body>"
    index = html.lower().rfind(marker)
    if index >= 0:
        return f"{html[:index]}\n{snippet}\n{html[index:]}"
    return f"{html}\n{snippet}\n"


def _normalize_a2ui_asset_path(asset_path: str | None) -> str | None:
    raw_path = unquote(asset_path or "").replace("\\", "/").lstrip("/")
    if raw_path in {"", "."}:
        return "index.html"

    normalized = posixpath.normpath(raw_path)
    if normalized in {"", "."}:
        return "index.html"
    if normalized == ".." or normalized.startswith("../") or normalized.startswith("/"):
        return None
    return normalized
