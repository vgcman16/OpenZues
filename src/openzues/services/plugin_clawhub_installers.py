from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlencode

import httpx

from openzues import __version__

_DEFAULT_CLAWHUB_URL = "https://clawhub.ai"
_DEFAULT_TIMEOUT_SECONDS = 30.0
_GENERATED_ARCHIVE_METADATA_FILE = "_meta.json"
_MAX_ARCHIVE_BYTES_ZIP = 256 * 1024 * 1024
_MAX_ENTRIES = 50_000
_MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
_MAX_ENTRY_BYTES = 256 * 1024 * 1024


class ClawHubJsonFetcher(Protocol):
    async def __call__(
        self,
        path: str,
        *,
        search: dict[str, str] | None = None,
    ) -> dict[str, object]: ...


class ClawHubArchiveDownloader(Protocol):
    async def __call__(
        self,
        path: str,
        *,
        search: dict[str, str] | None = None,
    ) -> bytes: ...


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _safe_segment(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip(".-")
    return normalized or "package"


def _json_object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _format_sha256_integrity(bytes_value: bytes) -> str:
    digest = hashlib.sha256(bytes_value).digest()
    return _format_sha256_digest(digest)


def _format_sha256_digest(digest: bytes) -> str:
    return f"sha256-{base64.b64encode(digest).decode('ascii')}"


def _normalize_sha256_integrity(value: str) -> str | None:
    trimmed = value.strip()
    if not trimmed:
        return None
    prefixed_base64 = re.match(r"^sha256-([A-Za-z0-9+/]+={0,1})$", trimmed)
    if prefixed_base64:
        encoded = prefixed_base64.group(1)
        if len(encoded) % 4:
            encoded += "=" * (4 - len(encoded) % 4)
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except ValueError:
            return None
        if len(decoded) == 32:
            return f"sha256-{base64.b64encode(decoded).decode('ascii')}"
        return None
    prefixed_hex = re.match(r"^sha256:([A-Fa-f0-9]{64})$", trimmed)
    if prefixed_hex:
        return _format_sha256_digest(bytes.fromhex(prefixed_hex.group(1)))
    if re.match(r"^[A-Fa-f0-9]{64}$", trimmed):
        return _format_sha256_digest(bytes.fromhex(trimmed))
    return None


def _normalize_sha256_hex(value: str) -> str | None:
    trimmed = value.strip()
    if re.match(r"^[A-Fa-f0-9]{64}$", trimmed):
        return trimmed.lower()
    return None


def _normalize_relative_path(value: object) -> str | None:
    if not isinstance(value, str) or len(value) == 0:
        return None
    if value.strip() != value or "\\" in value or value.startswith("/"):
        return None
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        return None
    return value


def _describe_invalid_relative_path(value: object) -> str:
    if not isinstance(value, str):
        return f"non-string value of type {type(value).__name__}"
    if len(value) == 0:
        return "empty string"
    if value.strip() != value:
        return f'path "{value}" has leading or trailing whitespace'
    if "\\" in value:
        return f'path "{value}" contains backslashes'
    if value.startswith("/"):
        return f'path "{value}" is absolute'
    segments = value.split("/")
    if any(segment == "" for segment in segments):
        return f'path "{value}" contains an empty segment'
    if any(segment in {".", ".."} for segment in segments):
        return f'path "{value}" contains dot segments'
    return f'path "{value}" failed validation for an unknown reason'


def _describe_invalid_sha256(value: object) -> str:
    if not isinstance(value, str):
        return f"non-string value of type {type(value).__name__}"
    if len(value) == 0:
        return "empty string"
    if len(value.strip()) == 0:
        return "whitespace-only string"
    return f'value "{value}" is not a 64-character hexadecimal SHA-256 digest'


@dataclass(frozen=True)
class _ClawHubSpec:
    name: str
    version: str | None = None


@dataclass(frozen=True)
class _ArchiveFile:
    path: str
    sha256: str


@dataclass(frozen=True)
class _ArchiveVerification:
    kind: str
    integrity: str | None = None
    files: tuple[_ArchiveFile, ...] = ()


class _ClawHubHttpError(RuntimeError):
    def __init__(self, *, path: str, status: int, body: str) -> None:
        super().__init__(f"ClawHub {path} failed ({status}): {body}")
        self.path = path
        self.status = status
        self.body = body


class CliClawHubPluginInstaller:
    def __init__(
        self,
        *,
        data_dir: Path,
        base_url: str | None = None,
        token: str | None = None,
        fetch_json: ClawHubJsonFetcher | None = None,
        download_bytes: ClawHubArchiveDownloader | None = None,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        runtime_version: str | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._data_dir = data_dir
        self._base_url = _normalize_base_url(base_url)
        self._token = token
        self._fetch_json = fetch_json
        self._download_bytes = download_bytes
        self._timeout_seconds = timeout_seconds
        self._runtime_version = runtime_version or _resolve_compatibility_host_version()
        self._now = now or (lambda: datetime.now(UTC))

    async def install(self, *, spec: str, mode: str = "install") -> dict[str, object]:
        parsed = _parse_clawhub_spec(spec)
        if parsed is None:
            return {
                "ok": False,
                "code": "invalid_spec",
                "error": f"invalid ClawHub plugin spec: {spec}",
            }
        try:
            detail = await self._request_json(_package_detail_path(parsed.name))
        except _ClawHubHttpError as exc:
            return _map_package_request_error(exc)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        package = _json_object(detail.get("package"))
        requested_version = _resolve_requested_version(package, parsed.version)
        if requested_version is None:
            return {
                "ok": False,
                "code": "no_installable_version",
                "error": (
                    f'ClawHub package "{_optional_string(package.get("name")) or "unknown"}" '
                    "has no installable version."
                ),
            }
        canonical_name = _optional_string(package.get("name")) or parsed.name
        try:
            version_detail = await self._request_json(
                _package_version_path(canonical_name, requested_version)
            )
        except _ClawHubHttpError as exc:
            return _map_version_request_error(
                exc,
                name=canonical_name,
                version=requested_version,
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        version_payload = _json_object(version_detail.get("version"))
        resolved_version = _optional_string(version_payload.get("version")) or requested_version
        verification_result = _resolve_archive_verification(
            version_payload=version_payload,
            package_name=canonical_name,
            version=resolved_version,
        )
        if verification_result.get("ok") is False:
            return verification_result
        compatibility = _json_object(version_payload.get("compatibility")) or _json_object(
            package.get("compatibility")
        )
        validation_error = _validate_package(
            package=package,
            compatibility=compatibility,
            runtime_version=self._runtime_version,
        )
        if validation_error is not None:
            return validation_error
        verification = verification_result.get("verification")
        if not isinstance(verification, _ArchiveVerification):
            return {
                "ok": False,
                "code": "missing_archive_integrity",
                "error": (
                    f'ClawHub version metadata for "{canonical_name}@{resolved_version}" '
                    "is missing sha256hash and usable files[] metadata for fallback "
                    "archive verification."
                ),
            }

        try:
            archive_bytes = await self._request_archive(
                _package_download_path(parsed.name),
                search={"version": resolved_version},
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        observed_integrity = _format_sha256_integrity(archive_bytes)
        if (
            verification.kind == "archive-integrity"
            and observed_integrity != verification.integrity
        ):
            return {
                "ok": False,
                "code": "archive_integrity_mismatch",
                "error": (
                    f'ClawHub archive integrity mismatch for "{parsed.name}@{resolved_version}": '
                    f"expected {verification.integrity}, got {observed_integrity}."
                ),
            }

        with tempfile.TemporaryDirectory(prefix="openzues-clawhub-") as temp_name:
            archive_path = Path(temp_name) / f"{_safe_segment(parsed.name)}.zip"
            archive_path.write_bytes(archive_bytes)
            if verification.kind == "file-list":
                fallback_result = _verify_archive_files(
                    archive_path=archive_path,
                    package_name=canonical_name,
                    package_version=resolved_version,
                    files=verification.files,
                )
                if fallback_result.get("ok") is False:
                    return fallback_result
            install_result = _install_plugin_archive(
                archive_path=archive_path,
                data_dir=self._data_dir,
                mode=mode,
            )
        if install_result.get("ok") is False:
            return install_result
        installed_version = _optional_string(install_result.get("version")) or resolved_version
        return {
            **install_result,
            "packageName": parsed.name,
            "clawhub": {
                "source": "clawhub",
                "clawhubUrl": self._base_url,
                "clawhubPackage": parsed.name,
                "clawhubFamily": package.get("family"),
                "clawhubChannel": package.get("channel"),
                "version": installed_version,
                "integrity": observed_integrity,
                "resolvedAt": self._now().astimezone(UTC).isoformat().replace("+00:00", "Z"),
            },
        }

    async def _request_json(
        self,
        path: str,
        *,
        search: dict[str, str] | None = None,
    ) -> dict[str, object]:
        if self._fetch_json is not None:
            return await self._fetch_json(path, search=search)
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(
                _build_url(self._base_url, path, search),
                headers=self._headers(),
            )
            if response.status_code >= 400:
                raise _ClawHubHttpError(
                    path=path,
                    status=response.status_code,
                    body=response.text.strip() or response.reason_phrase,
                )
            parsed = response.json()
            return parsed if isinstance(parsed, dict) else {}

    async def _request_archive(
        self,
        path: str,
        *,
        search: dict[str, str] | None = None,
    ) -> bytes:
        if self._download_bytes is not None:
            return await self._download_bytes(path, search=search)
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(
                _build_url(self._base_url, path, search),
                headers=self._headers(),
            )
            if response.status_code >= 400:
                raise _ClawHubHttpError(
                    path=path,
                    status=response.status_code,
                    body=response.text.strip() or response.reason_phrase,
                )
            return bytes(response.content)

    def _headers(self) -> dict[str, str] | None:
        token = _optional_string(self._token) or _resolve_clawhub_token()
        return {"Authorization": f"Bearer {token}"} if token else None


def _normalize_base_url(value: str | None) -> str:
    resolved = (
        _optional_string(value)
        or _optional_string(os.environ.get("OPENCLAW_CLAWHUB_URL"))
        or _optional_string(os.environ.get("CLAWHUB_URL"))
        or _DEFAULT_CLAWHUB_URL
    )
    return resolved.rstrip("/") or _DEFAULT_CLAWHUB_URL


def _resolve_clawhub_token() -> str | None:
    return (
        _optional_string(os.environ.get("OPENCLAW_CLAWHUB_TOKEN"))
        or _optional_string(os.environ.get("CLAWHUB_TOKEN"))
        or _optional_string(os.environ.get("CLAWHUB_AUTH_TOKEN"))
    )


def _resolve_compatibility_host_version() -> str:
    return (
        _optional_string(os.environ.get("OPENCLAW_COMPATIBILITY_HOST_VERSION"))
        or _optional_string(os.environ.get("OPENCLAW_VERSION"))
        or _optional_string(os.environ.get("OPENCLAW_SERVICE_VERSION"))
        or _optional_string(os.environ.get("OPENZUES_VERSION"))
        or __version__
    )


def _build_url(base_url: str, path: str, search: Mapping[str, str] | None) -> str:
    query = urlencode({key: value for key, value in (search or {}).items() if value})
    return f"{base_url}{path}{f'?{query}' if query else ''}"


def _package_detail_path(name: str) -> str:
    return f"/api/v1/packages/{quote(name, safe='')}"


def _package_version_path(name: str, version: str) -> str:
    return f"/api/v1/packages/{quote(name, safe='')}/versions/{quote(version, safe='')}"


def _package_download_path(name: str) -> str:
    return f"/api/v1/packages/{quote(name, safe='')}/download"


def _parse_clawhub_spec(raw: str) -> _ClawHubSpec | None:
    trimmed = raw.strip()
    if not trimmed.lower().startswith("clawhub:"):
        return None
    spec = trimmed[len("clawhub:") :].strip()
    if not spec:
        return None
    at_index = spec.rfind("@")
    if at_index <= 0 or at_index >= len(spec) - 1:
        return _ClawHubSpec(name=spec)
    return _ClawHubSpec(
        name=spec[:at_index].strip(),
        version=spec[at_index + 1 :].strip() or None,
    )


def _resolve_requested_version(
    package: dict[str, Any],
    requested_version: str | None,
) -> str | None:
    if requested_version:
        return requested_version
    latest = _optional_string(package.get("latestVersion"))
    if latest:
        return latest
    tags = package.get("tags")
    if isinstance(tags, dict):
        return _optional_string(tags.get("latest"))
    return None


def _map_package_request_error(exc: _ClawHubHttpError) -> dict[str, object]:
    if exc.status == 404:
        return {
            "ok": False,
            "code": "package_not_found",
            "error": "Package not found on ClawHub.",
        }
    return {"ok": False, "error": str(exc)}


def _map_version_request_error(
    exc: _ClawHubHttpError,
    *,
    name: str,
    version: str,
) -> dict[str, object]:
    if exc.status == 404:
        return {
            "ok": False,
            "code": "version_not_found",
            "error": f"Version not found on ClawHub: {name}@{version}.",
        }
    return {"ok": False, "error": str(exc)}


def _resolve_archive_verification(
    *,
    version_payload: dict[str, Any],
    package_name: str,
    version: str,
) -> dict[str, object]:
    sha256hash_value = version_payload.get("sha256hash")
    sha256hash = _optional_string(sha256hash_value)
    if sha256hash:
        integrity = _normalize_sha256_integrity(sha256hash)
        if integrity:
            return {
                "ok": True,
                "verification": _ArchiveVerification(
                    kind="archive-integrity",
                    integrity=integrity,
                ),
            }
    if sha256hash_value is not None:
        if isinstance(sha256hash_value, str) and not sha256hash_value.strip():
            detail = "empty string"
        elif isinstance(sha256hash_value, str):
            detail = f'unrecognized value "{sha256hash_value.strip()}"'
        else:
            detail = f"non-string value of type {type(sha256hash_value).__name__}"
        return {
            "ok": False,
            "code": "missing_archive_integrity",
            "error": (
                f'ClawHub version metadata for "{package_name}@{version}" has an '
                f"invalid sha256hash ({detail})."
            ),
        }
    files = version_payload.get("files")
    if not isinstance(files, list) or len(files) == 0:
        return {"ok": True, "verification": None}
    normalized_files: list[_ArchiveFile] = []
    seen_paths: set[str] = set()
    for index, file_value in enumerate(files):
        if not isinstance(file_value, dict):
            got = "null" if file_value is None else type(file_value).__name__
            return {
                "ok": False,
                "code": "missing_archive_integrity",
                "error": (
                    f'ClawHub version metadata for "{package_name}@{version}" has an '
                    f"invalid files[{index}] entry (expected an object, got {got})."
                ),
            }
        file_path = _normalize_relative_path(file_value.get("path"))
        sha256_value = _optional_string(file_value.get("sha256"))
        sha256 = _normalize_sha256_hex(sha256_value) if sha256_value else None
        if file_path is None:
            return {
                "ok": False,
                "code": "missing_archive_integrity",
                "error": (
                    f'ClawHub version metadata for "{package_name}@{version}" has an '
                    f"invalid files[{index}].path "
                    f"({_describe_invalid_relative_path(file_value.get('path'))})."
                ),
            }
        if file_path == _GENERATED_ARCHIVE_METADATA_FILE:
            return {
                "ok": False,
                "code": "missing_archive_integrity",
                "error": (
                    f'ClawHub version metadata for "{package_name}@{version}" must not '
                    f'include generated file "{file_path}" in files[].'
                ),
            }
        if sha256 is None:
            return {
                "ok": False,
                "code": "missing_archive_integrity",
                "error": (
                    f'ClawHub version metadata for "{package_name}@{version}" has an '
                    f"invalid files[{index}].sha256 "
                    f"({_describe_invalid_sha256(file_value.get('sha256'))})."
                ),
            }
        if file_path in seen_paths:
            return {
                "ok": False,
                "code": "missing_archive_integrity",
                "error": (
                    f'ClawHub version metadata for "{package_name}@{version}" has '
                    f'duplicate files[] path "{file_path}".'
                ),
            }
        seen_paths.add(file_path)
        normalized_files.append(_ArchiveFile(path=file_path, sha256=sha256))
    return {
        "ok": True,
        "verification": _ArchiveVerification(kind="file-list", files=tuple(normalized_files)),
    }


def _validate_package(
    *,
    package: dict[str, Any],
    compatibility: dict[str, Any],
    runtime_version: str,
) -> dict[str, object] | None:
    name = _optional_string(package.get("name")) or "unknown"
    family = _optional_string(package.get("family"))
    channel = _optional_string(package.get("channel"))
    if not package:
        return {
            "ok": False,
            "code": "package_not_found",
            "error": "Package not found on ClawHub.",
        }
    if family == "skill":
        return {
            "ok": False,
            "code": "skill_package",
            "error": f'"{name}" is a skill. Use "openclaw skills install {name}" instead.',
        }
    if family not in {"code-plugin", "bundle-plugin"}:
        return {
            "ok": False,
            "code": "unsupported_family",
            "error": f"Unsupported ClawHub package family: {family}",
        }
    if channel == "private":
        return {
            "ok": False,
            "code": "private_package",
            "error": f'"{name}" is private on ClawHub and cannot be installed anonymously.',
        }
    plugin_api_range = _optional_string(compatibility.get("pluginApiRange"))
    if plugin_api_range and not _satisfies_semver_range(runtime_version, plugin_api_range):
        return {
            "ok": False,
            "code": "incompatible_plugin_api",
            "error": (
                f'Plugin "{name}" requires plugin API {plugin_api_range}, but this '
                f"OpenClaw runtime exposes {runtime_version}."
            ),
        }
    min_gateway = _optional_string(compatibility.get("minGatewayVersion"))
    if min_gateway and not _is_version_at_least(runtime_version, min_gateway):
        return {
            "ok": False,
            "code": "incompatible_gateway",
            "error": (
                f'Plugin "{name}" requires OpenClaw >={min_gateway}, but this host is '
                f"{runtime_version}."
            ),
        }
    return None


def _parse_semver(value: str) -> tuple[int, int, int] | None:
    match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", value.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _compare_semver(left: str, right: str) -> int | None:
    left_parsed = _parse_semver(left)
    right_parsed = _parse_semver(right)
    if left_parsed is None or right_parsed is None:
        return None
    return (left_parsed > right_parsed) - (left_parsed < right_parsed)


def _upper_bound_for_caret(version: str) -> str | None:
    parsed = _parse_semver(version)
    if parsed is None:
        return None
    major, minor, patch = parsed
    if major > 0:
        return f"{major + 1}.0.0"
    if minor > 0:
        return f"0.{minor + 1}.0"
    return f"0.0.{patch + 1}"


def _satisfies_comparator(version: str, token: str) -> bool:
    trimmed = token.strip()
    if not trimmed:
        return True
    if trimmed.startswith("^"):
        base = trimmed[1:].strip()
        upper_bound = _upper_bound_for_caret(base)
        lower_cmp = _compare_semver(version, base)
        upper_cmp = _compare_semver(version, upper_bound) if upper_bound else None
        return lower_cmp is not None and upper_cmp is not None and lower_cmp >= 0 and upper_cmp < 0
    match = re.match(r"^(>=|<=|>|<|=)?\s*(.+)$", trimmed)
    if not match:
        return False
    operator = match.group(1) or "="
    target = match.group(2).strip()
    cmp = _compare_semver(version, target)
    if cmp is None:
        return False
    if operator == ">=":
        return cmp >= 0
    if operator == "<=":
        return cmp <= 0
    if operator == ">":
        return cmp > 0
    if operator == "<":
        return cmp < 0
    return cmp == 0


def _satisfies_semver_range(version: str, version_range: str) -> bool:
    tokens = [token.strip() for token in version_range.split() if token.strip()]
    return bool(tokens) and all(_satisfies_comparator(version, token) for token in tokens)


def _is_version_at_least(version: str, minimum: str) -> bool:
    cmp = _compare_semver(version, minimum)
    return cmp is not None and cmp >= 0


def _verify_archive_files(
    *,
    archive_path: Path,
    package_name: str,
    package_version: str,
    files: tuple[_ArchiveFile, ...],
) -> dict[str, object]:
    try:
        if archive_path.stat().st_size > _MAX_ARCHIVE_BYTES_ZIP:
            return {
                "ok": False,
                "code": "archive_integrity_mismatch",
                "error": (
                    "ClawHub archive fallback verification rejected the downloaded "
                    "archive because it exceeds the ZIP archive size limit."
                ),
            }
        actual_files: dict[str, str] = {}
        validated_generated_paths: set[str] = set()
        extracted_bytes = 0
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if len(infos) > _MAX_ENTRIES:
                return {
                    "ok": False,
                    "code": "archive_integrity_mismatch",
                    "error": (
                        "ClawHub archive fallback verification exceeded the archive "
                        "entry limit."
                    ),
                }
            for info in infos:
                if info.is_dir():
                    continue
                relative_path = _normalize_relative_path(info.filename)
                if relative_path is None:
                    return {
                        "ok": False,
                        "code": "archive_integrity_mismatch",
                        "error": (
                            "ClawHub archive contents do not match files[] metadata for "
                            f'"{package_name}@{package_version}": invalid package file path '
                            f'"{info.filename}" ({_describe_invalid_relative_path(info.filename)}).'
                        ),
                    }
                if info.file_size > _MAX_ENTRY_BYTES:
                    return {
                        "ok": False,
                        "code": "archive_integrity_mismatch",
                        "error": (
                            f'ClawHub archive fallback verification rejected "{info.filename}" '
                            "because it exceeds the per-file size limit."
                        ),
                    }
                extracted_bytes += info.file_size
                if extracted_bytes > _MAX_EXTRACTED_BYTES:
                    return {
                        "ok": False,
                        "code": "archive_integrity_mismatch",
                        "error": (
                            "ClawHub archive fallback verification exceeded the total "
                            "extracted-size limit."
                        ),
                    }
                payload = archive.read(info)
                if relative_path == _GENERATED_ARCHIVE_METADATA_FILE:
                    meta_failure = _validate_archive_meta_json(
                        package_name=package_name,
                        version=package_version,
                        bytes_value=payload,
                    )
                    if meta_failure is not None:
                        return meta_failure
                    validated_generated_paths.add(relative_path)
                    continue
                actual_files[relative_path] = hashlib.sha256(payload).hexdigest()
        for file in files:
            actual_sha256 = actual_files.get(file.path)
            if actual_sha256 is None:
                return {
                    "ok": False,
                    "code": "archive_integrity_mismatch",
                    "error": (
                        "ClawHub archive contents do not match files[] metadata for "
                        f'"{package_name}@{package_version}": missing "{file.path}".'
                    ),
                }
            if actual_sha256 != file.sha256:
                return {
                    "ok": False,
                    "code": "archive_integrity_mismatch",
                    "error": (
                        "ClawHub archive contents do not match files[] metadata for "
                        f'"{package_name}@{package_version}": expected {file.path} to hash '
                        f"to {file.sha256}, got {actual_sha256}."
                    ),
                }
            del actual_files[file.path]
        unexpected_file = sorted(actual_files)[0] if actual_files else None
        if unexpected_file:
            return {
                "ok": False,
                "code": "archive_integrity_mismatch",
                "error": (
                    "ClawHub archive contents do not match files[] metadata for "
                    f'"{package_name}@{package_version}": unexpected file "{unexpected_file}".'
                ),
            }
        return {
            "ok": True,
            "validatedGeneratedPaths": sorted(validated_generated_paths),
        }
    except (OSError, ValueError, zipfile.BadZipFile):
        return {
            "ok": False,
            "code": "archive_integrity_mismatch",
            "error": (
                "ClawHub archive fallback verification failed while reading the "
                "downloaded archive."
            ),
        }


def _validate_archive_meta_json(
    *,
    package_name: str,
    version: str,
    bytes_value: bytes,
) -> dict[str, object] | None:
    try:
        parsed = json.loads(bytes_value.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {
            "ok": False,
            "code": "archive_integrity_mismatch",
            "error": (
                "ClawHub archive contents do not match files[] metadata for "
                f'"{package_name}@{version}": '
                "_meta.json is not valid JSON."
            ),
        }
    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "code": "archive_integrity_mismatch",
            "error": (
                "ClawHub archive contents do not match files[] metadata for "
                f'"{package_name}@{version}": '
                "_meta.json is not a JSON object."
            ),
        }
    if parsed.get("slug") != package_name:
        return {
            "ok": False,
            "code": "archive_integrity_mismatch",
            "error": (
                "ClawHub archive contents do not match files[] metadata for "
                f'"{package_name}@{version}": '
                "_meta.json slug does not match the package name."
            ),
        }
    if parsed.get("version") != version:
        return {
            "ok": False,
            "code": "archive_integrity_mismatch",
            "error": (
                "ClawHub archive contents do not match files[] metadata for "
                f'"{package_name}@{version}": '
                "_meta.json version does not match the package version."
            ),
        }
    return None


def _install_plugin_archive(
    *,
    archive_path: Path,
    data_dir: Path,
    mode: str,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="openzues-clawhub-extract-") as temp_name:
        extracted_dir = Path(temp_name)
        try:
            _safe_extract_zip(archive_path, extracted_dir)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            return {"ok": False, "error": f"failed to extract ClawHub archive: {exc}"}
        package_root = _find_package_root(extracted_dir)
        manifest = _read_json_object(package_root / "openclaw.plugin.json")
        package_json = _read_json_object(package_root / "package.json")
        plugin_id = _optional_string(manifest.get("id"))
        if plugin_id is None:
            return {
                "ok": False,
                "code": "missing_openclaw_extensions",
                "error": "package missing openclaw.plugin.json",
            }
        target_dir = data_dir / "plugins" / "clawhub" / _safe_segment(plugin_id)
        if target_dir.exists():
            if mode != "update":
                return {
                    "ok": False,
                    "code": "already_exists",
                    "error": f"install target already exists: {target_dir}",
                }
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package_root, target_dir)
        version = _optional_string(manifest.get("version")) or _optional_string(
            package_json.get("version")
        )
        return {
            "ok": True,
            "pluginId": plugin_id,
            "targetDir": str(target_dir),
            "version": version,
        }


def _safe_extract_zip(archive_path: Path, destination: Path) -> None:
    destination_root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            if not target.is_relative_to(destination_root):
                raise ValueError(f"unsafe archive member: {info.filename}")
        archive.extractall(destination)


def _find_package_root(extracted_dir: Path) -> Path:
    package_dir = extracted_dir / "package"
    if package_dir.is_dir():
        return package_dir
    manifest_paths = sorted(
        extracted_dir.rglob("openclaw.plugin.json"),
        key=lambda path: len(path.parts),
    )
    if manifest_paths:
        return manifest_paths[0].parent
    package_jsons = sorted(extracted_dir.rglob("package.json"), key=lambda path: len(path.parts))
    if package_jsons:
        return package_jsons[0].parent
    return extracted_dir
