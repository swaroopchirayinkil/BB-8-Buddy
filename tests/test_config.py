"""
Unit tests for the Config layer.
"""

import sys
import tempfile
import unittest
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from bb8_buddy.config import Config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.config = Config(self.config_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_values(self):
        self.assertEqual(self.config.interval_minutes, 30)
        self.assertEqual(self.config.idle_threshold_minutes, 10)
        self.assertTrue(self.config.smart_pause_enabled)
        self.assertEqual(self.config.presence_mode, "tray")
        self.assertTrue(self.config.sound_enabled)
        self.assertFalse(self.config.is_muted())

    def test_custom_interval(self):
        self.config.interval_minutes = 45
        self.assertEqual(self.config.interval_minutes, 45)
        # Verify persistence
        reloaded = Config(self.config_path)
        self.assertEqual(reloaded.interval_minutes, 45)

    def test_mute_unmute(self):
        self.config.mute_for_hours(1.0)
        self.assertTrue(self.config.is_muted())
        self.config.unmute()
        self.assertFalse(self.config.is_muted())

    def test_custom_tag(self):
        self.config.add_custom_tag("starwars")
        tags = self.config.get("custom_tags")
        self.assertIn("#starwars", tags)


if __name__ == "__main__":
    unittest.main()

