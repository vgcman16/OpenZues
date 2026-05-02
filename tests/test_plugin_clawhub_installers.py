from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from openzues.services.plugin_clawhub_installers import CliClawHubPluginInstaller


def _write_plugin_archive(
    tmp_path: Path,
    *,
    plugin_id: str = "demo",
    version: str = "1.2.3",
) -> bytes:
    archive_path = tmp_path / "demo.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "package.json",
            json.dumps({"name": "@acme/demo", "version": version}),
        )
        archive.writestr(
            "openclaw.plugin.json",
            json.dumps({"id": plugin_id, "version": version}),
        )
        archive.writestr("dist/index.js", "export default {};\n")
    return archive_path.read_bytes()


def test_cli_clawhub_plugin_installer_downloads_verifies_and_installs_plugin(
    tmp_path: Path,
) -> None:
    archive_bytes = _write_plugin_archive(tmp_path)
    archive_hash = hashlib.sha256(archive_bytes).hexdigest()
    json_calls: list[tuple[str, dict[str, str]]] = []
    download_calls: list[tuple[str, dict[str, str]]] = []

    async def fake_fetch_json(
        path: str,
        *,
        search: dict[str, str] | None = None,
    ) -> dict[str, object]:
        json_calls.append((path, dict(search or {})))
        if path == "/api/v1/packages/demo":
            return {
                "package": {
                    "name": "demo",
                    "displayName": "Demo",
                    "family": "code-plugin",
                    "channel": "official",
                    "isOfficial": True,
                    "createdAt": 0,
                    "updatedAt": 0,
                    "latestVersion": "1.2.3",
                }
            }
        if path == "/api/v1/packages/demo/versions/1.2.3":
            return {
                "package": {
                    "name": "demo",
                    "displayName": "Demo",
                    "family": "code-plugin",
                },
                "version": {
                    "version": "1.2.3",
                    "createdAt": 0,
                    "changelog": "",
                    "sha256hash": archive_hash,
                },
            }
        raise AssertionError(f"unexpected ClawHub JSON path: {path}")

    async def fake_download(
        path: str,
        *,
        search: dict[str, str] | None = None,
    ) -> bytes:
        download_calls.append((path, dict(search or {})))
        return archive_bytes

    installer = CliClawHubPluginInstaller(
        data_dir=tmp_path / "data",
        base_url="https://clawhub.ai",
        fetch_json=fake_fetch_json,
        download_bytes=fake_download,
        now=lambda: datetime(2026, 5, 1, tzinfo=UTC),
    )

    result = asyncio.run(installer.install(spec="clawhub:demo", mode="install"))

    assert result["ok"] is True
    assert result["pluginId"] == "demo"
    assert result["targetDir"] == str(tmp_path / "data" / "plugins" / "clawhub" / "demo")
    assert result["version"] == "1.2.3"
    assert result["packageName"] == "demo"
    assert result["clawhub"] == {
        "source": "clawhub",
        "clawhubUrl": "https://clawhub.ai",
        "clawhubPackage": "demo",
        "clawhubFamily": "code-plugin",
        "clawhubChannel": "official",
        "version": "1.2.3",
        "integrity": result["clawhub"]["integrity"],
        "resolvedAt": "2026-05-01T00:00:00Z",
    }
    assert str(result["clawhub"]["integrity"]).startswith("sha256-")
    assert Path(str(result["targetDir"]), "openclaw.plugin.json").is_file()
    assert json_calls == [
        ("/api/v1/packages/demo", {}),
        ("/api/v1/packages/demo/versions/1.2.3", {}),
    ]
    assert download_calls == [
        ("/api/v1/packages/demo/download", {"version": "1.2.3"}),
    ]


def test_cli_clawhub_plugin_installer_accepts_unpadded_sri_hash(
    tmp_path: Path,
) -> None:
    archive_bytes = _write_plugin_archive(tmp_path)
    sri_hash = "sha256-" + base64.b64encode(hashlib.sha256(archive_bytes).digest()).decode(
        "ascii"
    ).rstrip("=")

    async def fake_fetch_json(
        path: str,
        *,
        search: dict[str, str] | None = None,
    ) -> dict[str, object]:
        del search
        if path == "/api/v1/packages/demo":
            return {
                "package": {
                    "name": "demo",
                    "displayName": "Demo",
                    "family": "code-plugin",
                    "channel": "official",
                    "isOfficial": True,
                    "createdAt": 0,
                    "updatedAt": 0,
                    "latestVersion": "1.2.3",
                }
            }
        return {
            "version": {
                "version": "1.2.3",
                "createdAt": 0,
                "changelog": "",
                "sha256hash": sri_hash,
            }
        }

    async def fake_download(
        path: str,
        *,
        search: dict[str, str] | None = None,
    ) -> bytes:
        del path, search
        return archive_bytes

    installer = CliClawHubPluginInstaller(
        data_dir=tmp_path / "data",
        fetch_json=fake_fetch_json,
        download_bytes=fake_download,
    )

    result = asyncio.run(installer.install(spec="clawhub:demo"))

    assert result["ok"] is True
    assert result["pluginId"] == "demo"
