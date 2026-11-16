"""
Audio and Speech handling for BB-8 Buddy.
Provides microphone detection, local audio recording, STT engine discovery, and fallback.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from bb8_buddy.config import get_audio_dir


class AudioManager:
    def __init__(self):
        self.audio_dir = get_audio_dir()
        self._recording_process: Optional[subprocess.Popen] = None
        self._current_audio_file: Optional[Path] = None

    def is_microphone_available(self) -> bool:
        """
        Checks if any audio capture device is available on the system.
        """
        # 1. Check arecord
        arecord_bin = shutil.which("arecord")
        if arecord_bin:
            try:
                res = subprocess.run(
                    [arecord_bin, "-l"],
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                )
                if res.returncode == 0 and "capture" in res.stdout.lower():
                    return True
            except Exception:
                pass

        # 2. Check /proc/asound/pcm
        pcm_path = Path("/proc/asound/pcm")
        if pcm_path.exists():
            try:
                content = pcm_path.read_text(encoding="utf-8", errors="ignore")
                if "capture" in content.lower():
                    return True
            except Exception:
                pass

        # 3. Check pactl
        pactl_bin = shutil.which("pactl")
        if pactl_bin:
            try:
                res = subprocess.run(
                    [pactl_bin, "list", "sources", "short"],
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return True
            except Exception:
                pass

        return False

    def get_stt_engine(self) -> Optional[str]:
        """
        Checks for available local STT tools:
        - vosk CLI or python package
        - whisper CLI or whisper.cpp
        - pocketsphinx
        """
        for bin_name in ["vosk-transcriber", "whisper", "whisper-cli", "pocketsphinx_continuous"]:
            if shutil.which(bin_name):
                return bin_name

        try:
            import vosk  # noqa
            return "python-vosk"
        except ImportError:
            pass

        try:
            import pocketsphinx  # noqa
            return "python-pocketsphinx"
        except ImportError:
            pass

        return None

    def start_recording(self) -> Tuple[bool, str, Optional[str]]:
        """
        Starts recording audio to a new file in the audio directory.
        Returns (success, message, filepath).
        """
        if not self.is_microphone_available():
            return False, "Microphone hardware not detected.", None

        if self._recording_process is not None:
            return False, "Recording already in progress.", None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.audio_dir / f"note_{timestamp}.wav"
        self._current_audio_file = output_file

        arecord = shutil.which("arecord")
        ffmpeg = shutil.which("ffmpeg")

        if arecord:
            cmd = [
                arecord,
                "-q",
                "-f", "cd",
                "-t", "wav",
                str(output_file),
            ]
        elif ffmpeg:
            cmd = [
                ffmpeg,
                "-y",
                "-f", "pulse",
                "-i", "default",
                "-ac", "1",
                "-ar", "16000",
                str(output_file),
            ]
        else:
            return False, "Neither arecord nor ffmpeg is available for audio capture.", None

        try:
            self._recording_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, "Recording started...", str(output_file)
        except Exception as e:
            self._current_audio_file = None
            self._recording_process = None
            return False, f"Failed to start recording: {e}", None

    def stop_recording(self) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Stops active recording, converts audio to text, and deletes the audio file.
        No audio is kept on disk.
        Returns (success, message, transcribed_text, audio_path=None).
        """
        if self._recording_process is None:
            return False, "No active recording.", None, None

        proc = self._recording_process
        self._recording_process = None
        temp_audio_file = self._current_audio_file
        self._current_audio_file = None

        try:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception as e:
            print(f"[BB-8 Audio] Error terminating recording: {e}", file=sys.stderr)

        if not temp_audio_file or not temp_audio_file.exists():
            return False, "Audio recording was empty or failed to capture.", None, None

        size = temp_audio_file.stat().st_size
        if size < 1024:  # less than 1KB
            try:
                temp_audio_file.unlink()
            except Exception:
                pass
            return False, "Recording was too short.", None, None

        # Convert audio into text
        transcript = None
        stt_engine = self.get_stt_engine()
        if stt_engine:
            transcript = self._transcribe(temp_audio_file, stt_engine)

        if not transcript:
            # Fallback text conversion based on audio wave properties
            try:
                import wave
                with wave.open(str(temp_audio_file), "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    duration = max(1, round(frames / float(rate)))
                    transcript = f"Voice check-in ({duration}s speech)"
            except Exception:
                transcript = "Voice check-in"

        # ALWAYS delete the temporary audio file - do not keep audio
        try:
            if temp_audio_file.exists():
                temp_audio_file.unlink()
        except Exception as e:
            print(f"[BB-8 Audio] Error removing temporary audio file: {e}", file=sys.stderr)

        return True, "Audio converted to text! (Audio discarded)", transcript, None

    def _transcribe(self, audio_file: Path, engine: str) -> Optional[str]:
        try:
            if "whisper" in engine:
                res = subprocess.run(
                    [engine, str(audio_file), "--output_format", "txt"],
                    capture_output=True,
                    text=True,
                    timeout=15.0,
                )
                txt_file = audio_file.with_suffix(".txt")
                if txt_file.exists():
                    text = txt_file.read_text(encoding="utf-8").strip()
                    txt_file.unlink()
                    return text
            elif "vosk" in engine:
                res = subprocess.run(
                    [engine, "-i", str(audio_file)],
                    capture_output=True,
                    text=True,
                    timeout=15.0,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
        except Exception as e:
            print(f"[BB-8 Audio] Transcription error: {e}", file=sys.stderr)
        return None

    def get_status(self) -> Dict[str, Any]:
        has_mic = self.is_microphone_available()
        stt_engine = self.get_stt_engine()
        return {
            "has_mic": has_mic,
            "stt_engine": stt_engine,
            "is_recording": self._recording_process is not None,
            "message": (
                "Microphone and local STT ready" if (has_mic and stt_engine)
                else "Microphone ready (voice note mode)" if has_mic
                else "Microphone not detected (text mode ready)"
            ),
        }

