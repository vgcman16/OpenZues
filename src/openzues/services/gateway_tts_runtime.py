from __future__ import annotations

import asyncio
import base64
import os
import platform
import secrets
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from openzues.services.gateway_tts import normalize_tts_provider


@dataclass(frozen=True, slots=True)
class GatewayTtsSynthesisResult:
    audio_path: str
    provider: str
    output_format: str
    voice_compatible: bool


class GatewayTtsRuntimeUnavailableError(RuntimeError):
    pass


type GatewayTtsConvertRunner = Callable[
    ...,
    GatewayTtsSynthesisResult,
]


class GatewayTtsRuntimeService:
    def __init__(
        self,
        data_dir: Path | None = None,
        *,
        provider_loader: Callable[[], str | None] | None = None,
        convert_runner: GatewayTtsConvertRunner | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._data_dir = data_dir
        self._provider_loader = provider_loader
        self._convert_runner = convert_runner
        self._enabled = enabled

    async def convert(
        self,
        *,
        text: str,
        channel: str | None,
        provider: str | None,
        model_id: str | None,
        voice_id: str | None,
    ) -> dict[str, object]:
        result = await self._convert_result(
            text=text,
            channel=channel,
            provider=provider,
            model_id=model_id,
            voice_id=voice_id,
        )
        return {
            "audioPath": result.audio_path,
            "provider": result.provider,
            "outputFormat": result.output_format,
            "voiceCompatible": result.voice_compatible,
        }

    async def speak(
        self,
        *,
        text: str,
        provider: str | None,
        model_id: str | None,
        voice_id: str | None,
        output_format: str | None,
        speed: float | None,
        rate_wpm: float | None,
    ) -> dict[str, object]:
        if output_format is not None and output_format.strip().lower() not in {"wav", "wave"}:
            raise GatewayTtsRuntimeUnavailableError(
                f'talk.speak unavailable: output format "{output_format}" '
                "is not wired in OpenZues yet"
            )
        self._resolve_speed(speed=speed, rate_wpm=rate_wpm)
        result = await self._convert_result(
            text=text,
            channel=None,
            provider=provider,
            model_id=model_id,
            voice_id=voice_id,
        )
        audio_path = Path(result.audio_path)
        audio_bytes = audio_path.read_bytes()
        if self._convert_runner is None:
            audio_path.unlink(missing_ok=True)
        return {
            "audioBase64": base64.b64encode(audio_bytes).decode("ascii"),
            "provider": result.provider,
            "outputFormat": result.output_format,
            "voiceCompatible": result.voice_compatible,
            "mimeType": "audio/wav",
            "fileExtension": ".wav",
        }

    async def _convert_result(
        self,
        *,
        text: str,
        channel: str | None,
        provider: str | None,
        model_id: str | None,
        voice_id: str | None,
    ) -> GatewayTtsSynthesisResult:
        resolved_provider = self._resolve_provider(provider)
        if resolved_provider != "microsoft":
            raise GatewayTtsRuntimeUnavailableError(
                f'TTS conversion unavailable: provider "{resolved_provider}" '
                "is not wired in OpenZues yet"
            )
        if self._convert_runner is not None:
            return self._convert_runner(
                text=text,
                channel=channel,
                provider=resolved_provider,
                model_id=model_id,
                voice_id=voice_id,
            )
        if not self._is_runtime_enabled():
            raise GatewayTtsRuntimeUnavailableError(
                "TTS conversion runtime not wired in OpenZues yet"
            )
        return await asyncio.to_thread(
            self._convert_with_windows_sapi,
            text=text,
            provider=resolved_provider,
            voice_id=voice_id,
        )

    def _resolve_provider(self, requested_provider: str | None) -> str:
        if requested_provider is not None:
            normalized = normalize_tts_provider(requested_provider)
            if normalized is not None:
                return normalized
        if self._provider_loader is not None:
            normalized = normalize_tts_provider(self._provider_loader())
            if normalized is not None:
                return normalized
        return "microsoft"

    def _is_runtime_enabled(self) -> bool:
        if self._enabled is not None:
            return self._enabled
        if self._convert_runner is not None:
            return True
        if platform.system() != "Windows":
            return False
        return shutil.which("powershell") is not None or shutil.which("pwsh") is not None

    def _convert_with_windows_sapi(
        self,
        *,
        text: str,
        provider: str,
        voice_id: str | None,
    ) -> GatewayTtsSynthesisResult:
        command = shutil.which("powershell") or shutil.which("pwsh")
        if command is None:
            raise GatewayTtsRuntimeUnavailableError(
                "PowerShell is not available for TTS conversion"
            )
        output_path = self._next_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env["OPENZUES_TTS_TEXT_B64"] = base64.b64encode(text.encode("utf-8")).decode("ascii")
        env["OPENZUES_TTS_OUTPUT"] = str(output_path)
        env["OPENZUES_TTS_VOICE_ID"] = voice_id or ""
        script = """
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$text = [System.Text.Encoding]::UTF8.GetString(
  [Convert]::FromBase64String($env:OPENZUES_TTS_TEXT_B64)
)
$output = $env:OPENZUES_TTS_OUTPUT
$voiceId = $env:OPENZUES_TTS_VOICE_ID
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  if ($voiceId) {
    $synth.SelectVoice($voiceId)
  }
  $synth.SetOutputToWaveFile($output)
  $synth.Speak($text)
} finally {
  $synth.Dispose()
}
"""
        completed = subprocess.run(
            [command, "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            output_path.unlink(missing_ok=True)
            detail = (completed.stderr or completed.stdout or "").strip()
            raise GatewayTtsRuntimeUnavailableError(
                detail or "TTS conversion runtime not wired in OpenZues yet"
            )
        if not output_path.exists() or output_path.stat().st_size == 0:
            output_path.unlink(missing_ok=True)
            raise GatewayTtsRuntimeUnavailableError("TTS conversion produced no audio output")
        return GatewayTtsSynthesisResult(
            audio_path=str(output_path.resolve()),
            provider=provider,
            output_format="wav",
            voice_compatible=True,
        )

    def _next_output_path(self) -> Path:
        root = (
            self._data_dir / "generated" / "tts"
            if self._data_dir is not None
            else Path(tempfile.gettempdir()) / "openzues" / "generated" / "tts"
        )
        filename = f"tts-{int(time.time() * 1000)}-{secrets.token_hex(4)}.wav"
        return root / filename

    def _resolve_speed(self, *, speed: float | None, rate_wpm: float | None) -> float | None:
        if speed is not None:
            resolved_speed = float(speed)
        elif rate_wpm is not None:
            resolved_speed = float(rate_wpm) / 175.0
        else:
            return None
        if resolved_speed <= 0.5 or resolved_speed >= 2.0:
            raise ValueError(
                "invalid talk.speak params: rateWpm must resolve to speed between 0.5 and 2.0"
            )
        return resolved_speed
