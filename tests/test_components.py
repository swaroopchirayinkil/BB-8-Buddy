"""
Unit tests for idle detection, audio manager, and notifications.
"""

import sys
import tempfile
import unittest
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from bb8_buddy.idle import IdleDetector
from bb8_buddy.audio import AudioManager
from bb8_buddy.notifications import NotificationManager


class TestComponents(unittest.TestCase):
    def test_idle_detector_fallback(self):
        detector = IdleDetector()
        idle_secs = detector.get_idle_seconds()
        self.assertIsInstance(idle_secs, float)
        self.assertGreaterEqual(idle_secs, 0.0)
        # Should not falsely report idle on 0 threshold
        self.assertFalse(detector.is_idle(0))

    def test_audio_manager_status(self):
        audio = AudioManager()
        status = audio.get_status()
        self.assertIn("has_mic", status)
        self.assertIn("stt_engine", status)
        self.assertIn("message", status)
        self.assertIsInstance(status["has_mic"], bool)

    def test_audio_converted_and_deleted(self):
        import wave, subprocess
        audio = AudioManager()
        temp_wav = audio.audio_dir / "test_sample.wav"
        with wave.open(str(temp_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 32000)

        audio._current_audio_file = temp_wav
        audio._recording_process = subprocess.Popen(["true"])
        audio._recording_process.wait()

        ok, msg, transcript, audio_path = audio.stop_recording()
        self.assertTrue(ok)
        self.assertIsNotNone(transcript)
        self.assertIsNone(audio_path)
        # Ensure temporary audio file is strictly deleted and not kept on disk
        self.assertFalse(temp_wav.exists())

    def test_notification_manager(self):
        nm = NotificationManager()
        # Should execute without throwing exceptions
        res = nm.show("Test BB-8", "Testing notification dispatch", urgency="low")
        self.assertIsInstance(res, bool)


if __name__ == "__main__":
    unittest.main()

