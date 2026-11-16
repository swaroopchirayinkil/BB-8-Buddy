"""
Unit tests for the SQLite Database layer.
"""

import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from bb8_buddy.db import Database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_bb8.db"
        self.db = Database(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_get_entry(self):
        entry = self.db.add_entry(
            text="Developing BB-8 Buddy",
            tags=["#work", "#python"],
            source="text",
        )
        self.assertIsNotNone(entry["id"])
        self.assertEqual(entry["text"], "Developing BB-8 Buddy")
        self.assertIn("#work", entry["tags"])
        self.assertIn("#python", entry["tags"])
        self.assertEqual(entry["source"], "text")

        fetched = self.db.get_entry(entry["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["text"], "Developing BB-8 Buddy")

    def test_duration_calculation(self):
        t0 = datetime(2026, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 11, 15, 10, 30, 0, tzinfo=timezone.utc)

        e1 = self.db.add_entry("First check-in", ["#work"], timestamp=t0)
        self.assertEqual(e1["duration_minutes"], 0.0)

        e2 = self.db.add_entry("Second check-in", ["#work"], timestamp=t1)
        self.assertEqual(e2["duration_minutes"], 30.0)

    def test_streak_calculation(self):
        today = datetime.now(timezone.utc)
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        self.db.add_entry("Day -2", ["#work"], timestamp=two_days_ago)
        self.db.add_entry("Day -1", ["#work"], timestamp=yesterday)
        self.db.add_entry("Day 0", ["#work"], timestamp=today)

        streak = self.db.get_streak()
        self.assertEqual(streak, 3)

    def test_analytics(self):
        self.db.add_entry("Coding feature A #work", ["#work"])
        self.db.add_entry("Reviewing PR #meeting", ["#meeting"])
        self.db.add_entry("Quick tea break #break", ["#break"])

        analytics = self.db.get_analytics("all")
        self.assertEqual(analytics["total_entries"], 3)
        self.assertGreaterEqual(len(analytics["tag_breakdown"]), 3)
        self.assertGreaterEqual(len(analytics["top_activities"]), 1)

    def test_exports(self):
        self.db.add_entry("Sprint planning", ["#meeting", "#work"])
        self.db.add_entry("Coffee break", ["#break"])

        csv_data = self.db.export_csv()
        self.assertIn("Sprint planning", csv_data)
        self.assertIn("#meeting", csv_data)

        md_data = self.db.export_markdown()
        self.assertIn("BB-8 Buddy Activity Log", md_data)
        self.assertIn("Sprint planning", md_data)


if __name__ == "__main__":
    unittest.main()

