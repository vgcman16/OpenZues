import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.services.gateway_canvas_documents import (
    build_canvas_document_entry_url,
    create_canvas_document,
    load_canvas_document_manifest,
    resolve_canvas_document_assets,
    resolve_canvas_document_dir,
    resolve_canvas_http_path_to_local_path,
)
from openzues.services.gateway_canvas_live_reload import CanvasLiveReloadWatcher
from openzues.services.gateway_node_registry import GatewayNodeConnect
from openzues.settings import Settings


class _CanvasNodeConnection:
    conn_id = "conn-canvas-node"

    def send_gateway_event(self, event: str, payload: object) -> None:
        del event, payload


def test_canvas_document_entry_url_encodes_special_path_segments() -> None:
    url = build_canvas_document_entry_url(
        "cv_example",
        "bundle#1/entry%20 point?.html",
    )

    assert url == (
        "/__openclaw__/canvas/documents/cv_example/"
        "bundle%231/entry%2520%20point%3F.html"
    )


def test_canvas_http_path_resolves_inside_managed_documents(tmp_path: Path) -> None:
    resolved = resolve_canvas_http_path_to_local_path(
        "/__openclaw__/canvas/documents/cv_example/collection.media/index.html",
        state_dir=tmp_path,
    )

    assert resolved == (
        tmp_path / "canvas" / "documents" / "cv_example" / "collection.media" / "index.html"
    )


def test_canvas_http_path_rejects_traversal_document_ids(tmp_path: Path) -> None:
    resolved = resolve_canvas_http_path_to_local_path(
        "/__openclaw__/canvas/documents/../collection.media/index.html",
        state_dir=tmp_path,
    )

    assert resolved is None


def test_create_canvas_document_materializes_inline_html_and_manifest(
    tmp_path: Path,
) -> None:
    document = create_canvas_document(
        {
            "id": "status-card",
            "kind": "html_bundle",
            "title": " Preview ",
            "entrypoint": {"type": "html", "value": "<div>Front</div>"},
        },
        state_dir=tmp_path,
    )

    document_dir = resolve_canvas_document_dir("status-card", state_dir=tmp_path)

    assert document["id"] == "status-card"
    assert document["title"] == "Preview"
    assert document["localEntrypoint"] == "index.html"
    assert document["entryUrl"] == (
        "/__openclaw__/canvas/documents/status-card/index.html"
    )
    assert (document_dir / "index.html").read_text(encoding="utf-8") == "<div>Front</div>"
    assert (document_dir / "manifest.json").is_file()


def test_create_canvas_document_replaces_stable_document_id(tmp_path: Path) -> None:
    create_canvas_document(
        {
            "id": "status-card",
            "kind": "html_bundle",
            "entrypoint": {"type": "html", "value": "<div>first</div>"},
        },
        state_dir=tmp_path,
    )
    document = create_canvas_document(
        {
            "id": "status-card",
            "kind": "html_bundle",
            "entrypoint": {"type": "html", "value": "<div>second</div>"},
        },
        state_dir=tmp_path,
    )

    index_html = (
        resolve_canvas_document_dir(str(document["id"]), state_dir=tmp_path) / "index.html"
    ).read_text(encoding="utf-8")

    assert index_html == "<div>second</div>"
    assert "first" not in index_html


def test_create_canvas_document_copies_workspace_path_entrypoint(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    (workspace_dir / "player").mkdir(parents=True)
    (workspace_dir / "player" / "index.html").write_text("<div>ok</div>", encoding="utf-8")

    document = create_canvas_document(
        {
            "kind": "html_bundle",
            "entrypoint": {"type": "path", "value": "player/index.html"},
        },
        state_dir=tmp_path / "state",
        workspace_dir=workspace_dir,
    )

    document_dir = resolve_canvas_document_dir(
        str(document["id"]),
        state_dir=tmp_path / "state",
    )

    assert document["localEntrypoint"] == "index.html"
    assert document["entryUrl"] == (
        f"/__openclaw__/canvas/documents/{document['id']}/index.html"
    )
    assert (document_dir / "index.html").read_text(encoding="utf-8") == "<div>ok</div>"


def test_create_canvas_document_wraps_local_pdf_entrypoint(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    (workspace_dir / "demo.pdf").write_text("%PDF-1.4", encoding="utf-8")

    document = create_canvas_document(
        {
            "kind": "document",
            "entrypoint": {"type": "path", "value": "demo.pdf"},
        },
        state_dir=tmp_path / "state",
        workspace_dir=workspace_dir,
    )

    index_html = (
        resolve_canvas_document_dir(str(document["id"]), state_dir=tmp_path / "state")
        / "index.html"
    ).read_text(encoding="utf-8")

    assert document["localEntrypoint"] == "index.html"
    assert document["entryUrl"] == (
        f"/__openclaw__/canvas/documents/{document['id']}/index.html"
    )
    assert 'type="application/pdf"' in index_html
    assert 'data="demo.pdf"' in index_html


def test_create_canvas_document_copies_assets_and_resolves_asset_urls(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    (workspace_dir / "collection.media").mkdir(parents=True)
    (workspace_dir / "collection.media" / "audio.mp3").write_text("audio", encoding="utf-8")

    document = create_canvas_document(
        {
            "kind": "html_bundle",
            "entrypoint": {
                "type": "html",
                "value": (
                    '<audio controls><source src="collection.media/audio.mp3" '
                    'type="audio/mpeg" /></audio>'
                ),
            },
            "assets": [
                {
                    "logicalPath": "collection.media/audio.mp3",
                    "sourcePath": "collection.media/audio.mp3",
                    "contentType": "audio/mpeg",
                }
            ],
        },
        state_dir=tmp_path / "state",
        workspace_dir=workspace_dir,
    )

    document_dir = resolve_canvas_document_dir(
        str(document["id"]),
        state_dir=tmp_path / "state",
    )
    asset_path = document_dir / "collection.media" / "audio.mp3"

    assert asset_path.read_text(encoding="utf-8") == "audio"
    assert document["assets"] == [
        {
            "logicalPath": "collection.media/audio.mp3",
            "contentType": "audio/mpeg",
        }
    ]
    assert resolve_canvas_document_assets(document, state_dir=tmp_path / "state") == [
        {
            "logicalPath": "collection.media/audio.mp3",
            "contentType": "audio/mpeg",
            "localPath": asset_path,
            "url": (
                f"/__openclaw__/canvas/documents/{document['id']}/"
                "collection.media/audio.mp3"
            ),
        }
    ]
    assert resolve_canvas_document_assets(
        document,
        base_url="http://127.0.0.1:19003/",
        state_dir=tmp_path / "state",
    )[0]["url"] == (
        f"http://127.0.0.1:19003/__openclaw__/canvas/documents/{document['id']}/"
        "collection.media/audio.mp3"
    )


def test_create_canvas_document_wraps_remote_pdf_url(tmp_path: Path) -> None:
    document = create_canvas_document(
        {
            "kind": "document",
            "entrypoint": {"type": "url", "value": "https://example.com/demo.pdf"},
        },
        state_dir=tmp_path,
    )

    index_html = (
        resolve_canvas_document_dir(str(document["id"]), state_dir=tmp_path) / "index.html"
    ).read_text(encoding="utf-8")

    assert document["localEntrypoint"] == "index.html"
    assert document["externalUrl"] == "https://example.com/demo.pdf"
    assert document["entryUrl"] == (
        f"/__openclaw__/canvas/documents/{document['id']}/index.html"
    )
    assert 'type="application/pdf"' in index_html
    assert 'data="https://example.com/demo.pdf"' in index_html


def test_create_canvas_document_wraps_image_path_entrypoint(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    (workspace_dir / "photo.png").write_bytes(b"png")

    document = create_canvas_document(
        {
            "kind": "image",
            "entrypoint": {"type": "path", "value": "photo.png"},
        },
        state_dir=tmp_path / "state",
        workspace_dir=workspace_dir,
    )

    document_dir = resolve_canvas_document_dir(
        str(document["id"]),
        state_dir=tmp_path / "state",
    )
    index_html = (document_dir / "index.html").read_text(encoding="utf-8")

    assert document["localEntrypoint"] == "index.html"
    assert (document_dir / "photo.png").read_bytes() == b"png"
    assert '<img src="photo.png"' in index_html


def test_create_canvas_document_passes_through_non_pdf_url(tmp_path: Path) -> None:
    document = create_canvas_document(
        {
            "kind": "url_embed",
            "entrypoint": {"type": "url", "value": "https://example.com/app"},
        },
        state_dir=tmp_path,
    )

    assert document["entryUrl"] == "https://example.com/app"
    assert document["externalUrl"] == "https://example.com/app"
    assert "localEntrypoint" not in document


def test_load_canvas_document_manifest_reads_saved_manifest(tmp_path: Path) -> None:
    document = create_canvas_document(
        {
            "id": "status-card",
            "kind": "html_bundle",
            "entrypoint": {"type": "html", "value": "<div>saved</div>"},
        },
        state_dir=tmp_path,
    )

    assert load_canvas_document_manifest("status-card", state_dir=tmp_path) == document
    assert load_canvas_document_manifest("missing", state_dir=tmp_path) is None


def test_create_app_serves_managed_canvas_document_paths(tmp_path: Path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    document = create_canvas_document(
        {
            "id": "served-card",
            "kind": "html_bundle",
            "entrypoint": {"type": "html", "value": "<div>served</div>"},
        },
        state_dir=app_settings.data_dir,
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        response = client.get(str(document["entryUrl"]))
        traversal_response = client.get(
            "/__openclaw__/canvas/documents/%2E%2E/collection.media/index.html"
        )

    assert response.status_code == 200
    assert "<div>served</div>" in response.text
    assert traversal_response.status_code == 404


def test_create_app_serves_a2ui_canvas_scaffold_and_blocks_traversal(
    tmp_path: Path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        scaffold_response = client.get("/__openclaw__/a2ui/")
        bundle_response = client.get("/__openclaw__/a2ui/a2ui.bundle.js")
        traversal_response = client.get("/__openclaw__/a2ui/%2E%2E/package.json")

    assert scaffold_response.status_code == 200
    assert "openclaw-a2ui-host" in scaffold_response.text
    assert "openclawCanvasA2UIAction" in scaffold_response.text
    assert bundle_response.status_code == 200
    assert "openclawA2UI" in bundle_response.text
    assert traversal_response.status_code == 404


def test_create_app_exposes_canvas_live_reload_websocket_path(tmp_path: Path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        http_response = client.get("/__openclaw__/ws")
        bundle_response = client.get("/__openclaw__/a2ui/a2ui.bundle.js")
        with client.websocket_connect("/__openclaw__/ws?oc_cap=test-cap") as websocket:
            websocket.send_text("noop")

    assert http_response.status_code == 426
    assert http_response.text == "upgrade required"
    assert "/__openclaw__/ws" in bundle_response.text


def test_canvas_live_reload_broadcast_reaches_connected_websocket(tmp_path: Path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        with client.websocket_connect("/__openclaw__/ws?oc_cap=test-cap") as websocket:
            asyncio.run(client.app.state.canvas_live_reload_hub.publish({"type": "canvas/reload"}))
            assert websocket.receive_text() == "reload"


async def test_canvas_live_reload_watcher_debounces_file_change_events(
    tmp_path: Path,
) -> None:
    canvas_root = tmp_path / "canvas"
    canvas_root.mkdir()
    (canvas_root / "index.html").write_text("<html>one</html>", encoding="utf-8")
    events: list[dict[str, object]] = []

    async def publish_reload(event: dict[str, object]) -> None:
        events.append(event)

    watcher = CanvasLiveReloadWatcher(
        state_dir=tmp_path,
        publish_reload=publish_reload,
        debounce_seconds=0.01,
    )

    try:
        assert await watcher.scan_once() is False

        (canvas_root / "index.html").write_text(
            "<html>two plus reload</html>",
            encoding="utf-8",
        )
        assert await watcher.scan_once() is True
        (canvas_root / "app.js").write_text("console.log('ready')", encoding="utf-8")
        assert await watcher.scan_once() is True
        await asyncio.sleep(0.03)

        assert events == [{"type": "canvas/reload"}]
    finally:
        await watcher.close()


def test_create_app_canvas_watcher_publishes_reload_to_websocket(tmp_path: Path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        with client.websocket_connect("/__openclaw__/ws?oc_cap=test-cap") as websocket:
            index_path = app_settings.data_dir / "canvas" / "index.html"
            index_path.write_text("<html>changed</html>", encoding="utf-8")

            async def scan_and_flush_reload() -> None:
                await client.app.state.canvas_live_reload_watcher.scan_once()
                await client.app.state.canvas_live_reload_watcher.flush_pending_reload()

            asyncio.run(scan_and_flush_reload())
            assert websocket.receive_text() == "reload"


def test_create_app_injects_live_reload_hook_into_canvas_html(tmp_path: Path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    document = create_canvas_document(
        {
            "id": "live-card",
            "kind": "html_bundle",
            "entrypoint": {"type": "html", "value": "<div>live</div>"},
        },
        state_dir=app_settings.data_dir,
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        document_response = client.get(str(document["entryUrl"]))
        root_response = client.get("/__openclaw__/canvas/")

    assert document_response.status_code == 200
    assert "<div>live</div>" in document_response.text
    assert "/__openclaw__/ws" in document_response.text
    assert "location.reload" in document_response.text
    assert "/__openclaw__/ws" in root_response.text
    assert "location.reload" in root_response.text


def test_create_app_serves_canvas_host_root_and_blocks_traversal(tmp_path: Path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bare_root_response = client.get("/__openclaw__/canvas")
        root_response = client.get("/__openclaw__/canvas/")
        index_response = client.get("/__openclaw__/canvas/index.html")
        traversal_response = client.get("/__openclaw__/canvas/%2E%2E/package.json")

    assert bare_root_response.status_code == 200
    assert bare_root_response.text == root_response.text
    assert root_response.status_code == 200
    assert "OpenClaw Canvas" in root_response.text
    assert "openclawSendUserAction" in root_response.text
    assert index_response.status_code == 200
    assert index_response.text == root_response.text
    assert traversal_response.status_code == 404


def test_create_app_serves_canvas_through_scoped_capability_paths(tmp_path: Path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    session = app.state.gateway_node_service.registry.register(
        _CanvasNodeConnection(),
        GatewayNodeConnect(
            client_id="live-canvas-node",
            device_id="canvas-node-1",
            platform="ios",
            canvas_host_url="http://127.0.0.1:8884",
        ),
    )
    session.canvas_capability = "cap-live"
    session.canvas_capability_expires_at_ms = 4_102_444_800_000

    with TestClient(app, client=("testclient", 50000)) as client:
        scoped_root_response = client.get(
            "/__openclaw__/cap/cap-live/__openclaw__/canvas/"
        )
        scoped_a2ui_response = client.get(
            "/__openclaw__/cap/cap-live/__openclaw__/a2ui/"
        )
        invalid_response = client.get("/__openclaw__/cap/not-live/__openclaw__/canvas/")
        with client.websocket_connect(
            "/__openclaw__/cap/cap-live/__openclaw__/ws"
        ) as websocket:
            asyncio.run(client.app.state.canvas_live_reload_hub.publish({"type": "canvas/reload"}))
            scoped_reload = websocket.receive_text()

    assert scoped_root_response.status_code == 200
    assert "OpenClaw Canvas" in scoped_root_response.text
    assert scoped_a2ui_response.status_code == 200
    assert "openclaw-a2ui-host" in scoped_a2ui_response.text
    assert invalid_response.status_code == 401
    assert scoped_reload == "reload"
