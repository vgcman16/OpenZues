from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

NpmCommandRunner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _safe_segment(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip(".-")
    return normalized or "package"


def _unscoped_package_name(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith("@") and "/" in value:
        return value.rsplit("/", 1)[-1] or None
    return value


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _default_runner(
    args: Sequence[str],
    timeout_seconds: float,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        list(args),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )


def _is_not_found_output(output: str) -> bool:
    lowered = output.lower()
    return "404" in lowered or "not found" in lowered or "e404" in lowered


def _safe_extract_tarball(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination_root):
                raise ValueError(f"unsafe archive member: {member.name}")
        archive.extractall(destination, filter="data")  # noqa: S202


def _find_package_root(extracted_dir: Path) -> Path:
    package_dir = extracted_dir / "package"
    if package_dir.is_dir():
        return package_dir
    package_jsons = sorted(extracted_dir.rglob("package.json"), key=lambda path: len(path.parts))
    if package_jsons:
        return package_jsons[0].parent
    return extracted_dir


@dataclass(slots=True)
class _PackedPackage:
    package_dir: Path
    metadata: dict[str, Any]


class _BaseNpmPackInstaller:
    def __init__(
        self,
        *,
        data_dir: Path,
        npm_executable: str | None = None,
        runner: NpmCommandRunner | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._data_dir = data_dir
        self._npm_executable = npm_executable
        self._runner = runner or _default_runner
        self._timeout_seconds = timeout_seconds

    async def _pack(self, spec: str) -> tuple[_PackedPackage | None, dict[str, object] | None]:
        return await asyncio.to_thread(self._pack_sync, spec)

    def _pack_sync(self, spec: str) -> tuple[_PackedPackage | None, dict[str, object] | None]:
        npm = self._npm_executable or shutil.which("npm")
        if not npm:
            return None, {
                "ok": False,
                "code": "npm_runtime_unavailable",
                "error": "npm executable not found on PATH.",
            }
        with tempfile.TemporaryDirectory(prefix="openzues-npm-pack-") as temp_name:
            temp_dir = Path(temp_name)
            completed = self._runner(
                [npm, "pack", "--json", spec, "--pack-destination", str(temp_dir)],
                self._timeout_seconds,
            )
            output = "\n".join(
                part for part in (completed.stdout, completed.stderr) if part
            ).strip()
            if completed.returncode != 0:
                code = (
                    "npm_package_not_found"
                    if _is_not_found_output(output)
                    else "npm_pack_failed"
                )
                return None, {
                    "ok": False,
                    "code": code,
                    "error": output or f"npm pack failed for {spec}.",
                }
            try:
                parsed = json.loads(completed.stdout or "[]")
            except ValueError:
                parsed = []
            row = parsed[0] if isinstance(parsed, list) and parsed else {}
            metadata = row if isinstance(row, dict) else {}
            filename = _optional_string(metadata.get("filename"))
            if filename is None:
                return None, {
                    "ok": False,
                    "code": "npm_pack_failed",
                    "error": f"npm pack did not report an archive for {spec}.",
                }
            archive_path = Path(filename)
            if not archive_path.is_absolute():
                archive_path = temp_dir / archive_path
            if not archive_path.is_file():
                return None, {
                    "ok": False,
                    "code": "npm_pack_failed",
                    "error": f"npm pack archive not found: {archive_path}",
                }
            extracted_dir = temp_dir / "extracted"
            try:
                _safe_extract_tarball(archive_path, extracted_dir)
            except (OSError, tarfile.TarError, ValueError) as exc:
                return None, {
                    "ok": False,
                    "code": "npm_pack_failed",
                    "error": f"failed to extract npm package: {exc}",
                }
            package_root = _find_package_root(extracted_dir)
            stable_dir = Path(tempfile.mkdtemp(prefix="openzues-npm-package-"))
            stable_package = stable_dir / "package"
            shutil.copytree(package_root, stable_package)
            return _PackedPackage(package_dir=stable_package, metadata=metadata), None

    def _resolution(
        self,
        spec: str,
        package_json: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, str]:
        name = _optional_string(metadata.get("name")) or _optional_string(
            package_json.get("name")
        )
        version = _optional_string(metadata.get("version")) or _optional_string(
            package_json.get("version")
        )
        resolution: dict[str, str] = {}
        if name:
            resolution["resolvedName"] = name
        if version:
            resolution["resolvedVersion"] = version
        if name and version:
            resolution["resolvedSpec"] = f"{name}@{version}"
        else:
            resolution["resolvedSpec"] = spec
        for source_key, target_key in (
            ("integrity", "integrity"),
            ("shasum", "shasum"),
        ):
            value = _optional_string(metadata.get(source_key))
            if value:
                resolution[target_key] = value
        return resolution

    def _replace_target(
        self,
        source_dir: Path,
        target_dir: Path,
        *,
        mode: str,
    ) -> dict[str, object] | None:
        if target_dir.exists():
            if mode != "update":
                return {
                    "ok": False,
                    "code": "already_exists",
                    "error": f"install target already exists: {target_dir}",
                }
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target_dir)
        return None


class CliNpmPluginInstaller(_BaseNpmPackInstaller):
    async def install(self, *, spec: str, mode: str = "install") -> dict[str, object]:
        packed, error = await self._pack(spec)
        if error is not None:
            return error
        assert packed is not None
        try:
            package_json = _read_json_object(packed.package_dir / "package.json")
            manifest = _read_json_object(packed.package_dir / "openclaw.plugin.json")
            plugin_id = _optional_string(manifest.get("id"))
            if plugin_id is None:
                return {
                    "ok": False,
                    "code": "missing_openclaw_extensions",
                    "error": "package.json missing openclaw.plugin.json",
                }
            target_dir = self._data_dir / "plugins" / "npm" / _safe_segment(plugin_id)
            replace_error = self._replace_target(packed.package_dir, target_dir, mode=mode)
            if replace_error is not None:
                return replace_error
            version = _optional_string(manifest.get("version")) or _optional_string(
                package_json.get("version")
            )
            return {
                "ok": True,
                "pluginId": plugin_id,
                "targetDir": str(target_dir),
                "version": version,
                "npmResolution": self._resolution(spec, package_json, packed.metadata),
            }
        finally:
            shutil.rmtree(packed.package_dir.parent, ignore_errors=True)


class CliNpmHookPackInstaller(_BaseNpmPackInstaller):
    async def install(
        self,
        *,
        spec: str,
        mode: str = "install",
        dryRun: bool = False,
    ) -> dict[str, object]:
        packed, error = await self._pack(spec)
        if error is not None:
            return error
        assert packed is not None
        try:
            package_json = _read_json_object(packed.package_dir / "package.json")
            package_name = _optional_string(package_json.get("name"))
            hook_id = _unscoped_package_name(package_name) or _safe_segment(spec)
            openclaw = package_json.get("openclaw")
            openclaw_payload = openclaw if isinstance(openclaw, dict) else {}
            raw_hooks = openclaw_payload.get("hooks")
            hooks = [str(value) for value in raw_hooks] if isinstance(raw_hooks, list) else []
            target_dir = self._data_dir / "hooks" / _safe_segment(hook_id)
            if not dryRun:
                replace_error = self._replace_target(packed.package_dir, target_dir, mode=mode)
                if replace_error is not None:
                    return replace_error
            version = _optional_string(package_json.get("version"))
            resolution = self._resolution(spec, package_json, packed.metadata)
            return {
                "ok": True,
                "hookPackId": hook_id,
                "targetDir": str(target_dir),
                "version": version,
                "hooks": hooks,
                "npmResolution": {
                    "name": resolution.get("resolvedName"),
                    "version": resolution.get("resolvedVersion"),
                    "resolvedSpec": resolution.get("resolvedSpec"),
                    "integrity": resolution.get("integrity"),
                    "shasum": resolution.get("shasum"),
                },
            }
        finally:
            shutil.rmtree(packed.package_dir.parent, ignore_errors=True)
