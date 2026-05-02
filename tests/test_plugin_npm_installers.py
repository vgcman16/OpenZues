from __future__ import annotations

import asyncio
import json
import subprocess
import tarfile
from pathlib import Path

from openzues.services.plugin_npm_installers import (
    CliNpmHookPackInstaller,
    CliNpmPluginInstaller,
)


def _write_package_archive(
    tmp_path: Path,
    *,
    name: str,
    package_json: dict[str, object],
    plugin_manifest: dict[str, object] | None = None,
) -> Path:
    package_dir = tmp_path / name / "package"
    package_dir.mkdir(parents=True)
    (package_dir / "package.json").write_text(json.dumps(package_json), encoding="utf-8")
    if plugin_manifest is not None:
        (package_dir / "openclaw.plugin.json").write_text(
            json.dumps(plugin_manifest),
            encoding="utf-8",
        )
    (package_dir / "index.js").write_text("export default {};\n", encoding="utf-8")
    archive_path = tmp_path / f"{name}.tgz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in package_dir.rglob("*"):
            archive.add(path, arcname=Path("package") / path.relative_to(package_dir))
    return archive_path


def test_cli_npm_plugin_installer_packs_and_extracts_plugin(tmp_path: Path) -> None:
    archive_path = _write_package_archive(
        tmp_path,
        name="demo-plugin",
        package_json={"name": "@acme/demo-plugin", "version": "1.2.3"},
        plugin_manifest={"id": "demo-plugin", "version": "1.2.3"},
    )
    calls: list[list[str]] = []

    def fake_runner(args, timeout_seconds):
        del timeout_seconds
        calls.append(list(args))
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps(
                [
                    {
                        "filename": str(archive_path),
                        "name": "@acme/demo-plugin",
                        "version": "1.2.3",
                        "integrity": "sha512-demo",
                        "shasum": "demo-shasum",
                    }
                ]
            ),
            stderr="",
        )

    installer = CliNpmPluginInstaller(
        data_dir=tmp_path / "data",
        npm_executable="npm",
        runner=fake_runner,
    )

    result = asyncio.run(installer.install(spec="@acme/demo-plugin"))

    assert calls[0][:4] == ["npm", "pack", "--json", "@acme/demo-plugin"]
    assert result["ok"] is True
    assert result["pluginId"] == "demo-plugin"
    assert result["version"] == "1.2.3"
    assert result["npmResolution"] == {
        "resolvedName": "@acme/demo-plugin",
        "resolvedVersion": "1.2.3",
        "resolvedSpec": "@acme/demo-plugin@1.2.3",
        "integrity": "sha512-demo",
        "shasum": "demo-shasum",
    }
    assert Path(str(result["targetDir"]), "openclaw.plugin.json").is_file()


def test_cli_npm_hook_pack_installer_packs_and_extracts_hook_pack(tmp_path: Path) -> None:
    archive_path = _write_package_archive(
        tmp_path,
        name="demo-hooks",
        package_json={
            "name": "@acme/demo-hooks",
            "version": "2.0.0",
            "openclaw": {"hooks": ["command-audit"]},
        },
    )

    def fake_runner(args, timeout_seconds):
        del timeout_seconds
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps(
                [
                    {
                        "filename": str(archive_path),
                        "name": "@acme/demo-hooks",
                        "version": "2.0.0",
                        "integrity": "sha512-hooks",
                    }
                ]
            ),
            stderr="",
        )

    installer = CliNpmHookPackInstaller(
        data_dir=tmp_path / "data",
        npm_executable="npm",
        runner=fake_runner,
    )

    result = asyncio.run(installer.install(spec="@acme/demo-hooks"))

    assert result["ok"] is True
    assert result["hookPackId"] == "demo-hooks"
    assert result["version"] == "2.0.0"
    assert result["hooks"] == ["command-audit"]
    assert result["npmResolution"] == {
        "name": "@acme/demo-hooks",
        "version": "2.0.0",
        "resolvedSpec": "@acme/demo-hooks@2.0.0",
        "integrity": "sha512-hooks",
        "shasum": None,
    }
    assert Path(str(result["targetDir"]), "package.json").is_file()
