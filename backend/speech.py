"""Local Windows speech synthesis using installed System.Speech (SAPI) voices.

No browser/cloud speech engine is used. PowerShell is launched without a visible
window; text and voice names are passed as JSON on stdin, never as shell code.
"""
from __future__ import annotations

import base64
from functools import lru_cache
import io
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import wave


MAX_TEXT_LENGTH = 4000
DEFAULT_VOICE_PREFERENCE = ("Microsoft Zira Desktop", "Microsoft Zira")

_POWERSHELL = r"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$request = [Console]::In.ReadToEnd() | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($request.mode -eq 'voices') {
        $voices = @($speaker.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object {
            @{ name = $_.VoiceInfo.Name; culture = $_.VoiceInfo.Culture.Name;
               gender = [string]$_.VoiceInfo.Gender; local = $true }
        })
        @{ voices = $voices; engine = 'Windows SAPI / System.Speech'; offline = $true } | ConvertTo-Json -Depth 4 -Compress
    } elseif ($request.mode -eq 'synthesize') {
        $speaker.SelectVoice([string]$request.voice)
        $speaker.Rate = [int]$request.sapi_rate
        $speaker.Volume = 100
        $speaker.SetOutputToWaveFile([string]$request.output_path)
        $speaker.Speak([string]$request.text)
        $speaker.SetOutputToNull()
        @{ completed = $true } | ConvertTo-Json -Compress
    } else { throw 'Unknown speech operation.' }
} finally { $speaker.Dispose() }
"""


def _run_sapi(payload: dict, timeout: float = 60) -> dict:
    if os.name != "nt":
        raise RuntimeError("Offline speech requires Windows with an installed SAPI voice.")
    windows_dir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    executable = windows_dir / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    encoded = base64.b64encode(_POWERSHELL.encode("utf-16le")).decode("ascii")
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    try:
        result = subprocess.run(
            [str(executable), "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startup,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Windows speech took too long. Try a shorter transcript.") from exc
    except OSError as exc:
        raise RuntimeError("Windows offline speech could not start.") from exc
    if result.returncode != 0:
        raise RuntimeError("Windows could not synthesize speech with the selected local voice.")
    try:
        return json.loads(result.stdout.lstrip("\ufeff").strip())
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Windows speech returned an unreadable response.") from exc


@lru_cache(maxsize=1)
def installed_voices() -> tuple[dict, ...]:
    """Enumerate enabled, locally installed SAPI voices once per app process."""
    result = _run_sapi({"mode": "voices"}, timeout=15)
    voices = result.get("voices", [])
    if not isinstance(voices, list):
        raise RuntimeError("Windows returned an invalid installed-voice list.")
    return tuple(voice for voice in voices if isinstance(voice, dict) and voice.get("name"))


def _default_voice(voices: tuple[dict, ...]) -> str | None:
    names = {voice["name"] for voice in voices}
    for preferred in DEFAULT_VOICE_PREFERENCE:
        if preferred in names:
            return preferred
    english = next((voice["name"] for voice in voices if str(voice.get("culture", "")).startswith("en")), None)
    return english or (voices[0]["name"] if voices else None)


def speech_status() -> dict:
    """Return actual local voice availability; never imply a cloud fallback."""
    try:
        voices = installed_voices()
        return {
            "available": bool(voices),
            "offline": True,
            "engine": "Windows SAPI / System.Speech",
            "default_voice": _default_voice(voices),
            "voices": list(voices),
            "rate_min": 0.5,
            "rate_max": 2.0,
            "max_text_length": MAX_TEXT_LENGTH,
        }
    except RuntimeError as exc:
        return {"available": False, "offline": True, "engine": "Windows SAPI / System.Speech", "voices": [], "error": str(exc)}


def synthesize_wav(text: str, rate: float = 1.0, voice: str | None = None) -> bytes:
    """Synthesize a PCM WAV locally and remove its temporary file afterwards.

    Rate is a UI multiplier between 0.5 and 2.0 mapped to SAPI's integer rate.
    It is approximate, since exact timing differs between installed voices.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Add some transcript text before speaking.")
    text = text.strip()
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Speech supports up to {MAX_TEXT_LENGTH} characters at once.")
    if isinstance(rate, bool) or not isinstance(rate, (float, int)) or not math.isfinite(rate) or not 0.5 <= rate <= 2.0:
        raise ValueError("Voice speed must be between 0.5 and 2.0.")
    voices = installed_voices()
    selected = voice or _default_voice(voices)
    if not selected:
        raise RuntimeError("Install a Windows speech voice to enable offline playback.")
    if selected not in {item["name"] for item in voices}:
        raise ValueError("Choose one of the locally installed Windows voices.")
    sapi_rate = max(-10, min(10, round((float(rate) - 1.0) * 10)))
    with tempfile.TemporaryDirectory(prefix="kamayan-speech-") as folder:
        output_path = Path(folder) / "speech.wav"
        _run_sapi({"mode": "synthesize", "text": text, "voice": selected, "sapi_rate": sapi_rate, "output_path": str(output_path)})
        try:
            audio = output_path.read_bytes()
            with wave.open(io.BytesIO(audio), "rb") as wav:
                if wav.getnframes() == 0 or wav.getcomptype() != "NONE":
                    raise RuntimeError("Windows produced empty or invalid speech audio.")
        except (OSError, wave.Error, EOFError) as exc:
            raise RuntimeError("Windows produced an unreadable speech audio file.") from exc
        return audio
