from __future__ import annotations

import json
from pathlib import Path

from openzues.services.codex_desktop import CodexDesktopService


def write_desktop_package(base: Path, version: str, *, contents: bytes = b"codex") -> Path:
    executable = (
        base / f"OpenAI.Codex_{version}_x64__2p2nqsd0c76g0" / "app" / "resources" / "codex.exe"
    )
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_bytes(contents)
    return executable


def test_discover_picks_latest_desktop_package_and_session(tmp_path) -> None:
    packages_root = tmp_path / "packages"
    logs_root = tmp_path / "logs"
    runtime_root = tmp_path / "runtime"
    write_desktop_package(packages_root, "26.405.1000.0", contents=b"old")
    latest_executable = write_desktop_package(packages_root, "26.406.3494.0", contents=b"new")
    log_path = logs_root / "2026" / "04" / "10" / "codex-desktop-test.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join(
            [
                "2026-04-10T04:14:59.674Z info [AppServerConnection] "
                "Starting app-server connection hostId=local transport=stdio",
                "2026-04-10T04:15:00.336Z info [StdioConnection] "
                "stdio_transport_spawned executablePath="
                '"C:\\\\Program Files\\\\WindowsApps\\\\OpenAI.Codex_26.406.3494.0'
                '_x64__2p2nqsd0c76g0\\\\app\\\\resources\\\\codex.exe"',
                "2026-04-10T04:15:02.136Z info [AppServerConnection] "
                "Current reported app-server version: "
                "currentVersion=0.119.0-alpha.11 hostId=local",
                "2026-04-10T04:15:02.136Z info [AppServerConnection] Codex CLI initialized",
            ]
        ),
        encoding="utf-8",
    )

    service = CodexDesktopService(
        runtime_root=runtime_root,
        package_root=packages_root,
        logs_root=logs_root,
    )
    discovery = service.discover()

    assert discovery.source_path == latest_executable
    assert discovery.source_kind == "package"
    assert discovery.staged_ready is False
    assert discovery.package_version == "26.406.3494.0"
    assert discovery.session.transport == "stdio"
    assert discovery.session.app_server_version == "0.119.0-alpha.11"
    assert discovery.session.initialized is True
    assert discovery.session.spawned_executable is not None


def test_resolve_launch_stages_binary_without_windowsapps_dependency(tmp_path, monkeypatch) -> None:
    packages_root = tmp_path / "packages"
    runtime_root = tmp_path / "runtime"
    executable = write_desktop_package(packages_root, "26.406.3494.0", contents=b"binary")
    service = CodexDesktopService(
        runtime_root=runtime_root,
        package_root=packages_root,
        logs_root=tmp_path / "logs",
    )
    monkeypatch.setattr(service, "probe_executable", lambda _: "codex-cli 0.119.0-alpha.11")

    launch = service.resolve_launch()
    staged_path = Path(launch.command)

    assert staged_path.exists()
    assert staged_path.read_bytes() == executable.read_bytes()
    assert launch.args == "-a never -s workspace-write app-server"
    assert "Staged from" in launch.note
    assert "sandbox workspace-write" in launch.note
    assert "approval never" in launch.note
    metadata = json.loads((staged_path.parent / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["source_path"] == str(executable.resolve())


def test_resolve_launch_respects_custom_execution_policy(tmp_path, monkeypatch) -> None:
    packages_root = tmp_path / "packages"
    runtime_root = tmp_path / "runtime"
    write_desktop_package(packages_root, "26.406.3494.0", contents=b"binary")
    service = CodexDesktopService(
        runtime_root=runtime_root,
        package_root=packages_root,
        logs_root=tmp_path / "logs",
        approval_policy="on-request",
        sandbox_mode="danger-full-access",
    )
    monkeypatch.setattr(service, "probe_executable", lambda _: "codex-cli 0.119.0-alpha.11")

    launch = service.resolve_launch()

    assert launch.args == "-a on-request -s danger-full-access app-server"
    assert launch.approval_policy == "on-request"
    assert launch.sandbox_mode == "danger-full-access"
