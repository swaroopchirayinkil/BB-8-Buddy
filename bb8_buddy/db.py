"""
Local SQLite database layer for BB-8 Buddy.
Reliable, zero-external-dependencies, persistent storage with analytics & exports.
"""

from __future__ import annotations
import csv
import io
import json
import sqlite3
import sys
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bb8_buddy.config import get_xdg_data_dir


def parse_iso(ts_str: str) -> datetime:
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = get_xdg_data_dir() / "bb8_buddy.db"
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    text TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    audio_path TEXT,
                    duration_minutes REAL NOT NULL DEFAULT 0.0,
                    source TEXT NOT NULL DEFAULT 'text',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_entries_timestamp ON entries(timestamp);
                CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at);

                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

    def add_entry(
        self,
        text: str,
        tags: Optional[List[str]] = None,
        audio_path: Optional[str] = None,
        source: str = "text",
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Adds a check-in entry. Calculates duration from the last entry automatically.
        """
        now = timestamp or datetime.now(timezone.utc)
        iso_now = now.isoformat()
        clean_text = text.strip()
        tags_list = tags or []

        # Extract hashtags from text if any
        words = clean_text.split()
        for w in words:
            if w.startswith("#") and len(w) > 1 and w not in tags_list:
                tags_list.append(w)

        tags_json = json.dumps(tags_list)

        last_entry = self.get_last_entry()
        duration_minutes = 0.0
        if last_entry:
            last_dt = parse_iso(last_entry["timestamp"])
            diff_secs = (now - last_dt).total_seconds()
            if 0 < diff_secs <= 4 * 3600:  # within 4 hours, count as continuous activity
                duration_minutes = round(diff_secs / 60.0, 1)
            else:
                duration_minutes = 0.0

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO entries (timestamp, text, tags, audio_path, duration_minutes, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (iso_now, clean_text, tags_json, audio_path, duration_minutes, source, iso_now),
            )
            entry_id = cursor.lastrowid

        return {
            "id": entry_id,
            "timestamp": iso_now,
            "text": clean_text,
            "tags": tags_list,
            "audio_path": audio_path,
            "duration_minutes": duration_minutes,
            "source": source,
            "created_at": iso_now,
        }

    def get_last_entry(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM entries ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def get_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM entries WHERE id = ?", (entry_id,)
            ).fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def delete_entry(self, entry_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            return cursor.rowcount > 0

    def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        tag: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query entries with optional date filtering, tag filtering, and full-text search.
        """
        clauses = []
        params: List[Any] = []

        if start_date:
            clauses.append("timestamp >= ?")
            params.append(start_date)

        if end_date:
            clauses.append("timestamp <= ?")
            params.append(end_date)

        if tag:
            clauses.append("tags LIKE ?")
            params.append(f"%{tag}%")

        if query:
            clauses.append("text LIKE ?")
            params.append(f"%{query}%")

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM entries {where_sql} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_streak(self) -> int:
        """
        Calculates consecutive daily streak up to today or yesterday.
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT substr(timestamp, 1, 10) as day FROM entries ORDER BY day DESC"
            ).fetchall()

        if not rows:
            return 0

        days = [date.fromisoformat(r["day"]) for r in rows]
        today = date.today()
        yesterday = today - timedelta(days=1)

        if days[0] != today and days[0] != yesterday:
            return 0

        streak = 1
        expected = days[0] - timedelta(days=1)

        for d in days[1:]:
            if d == expected:
                streak += 1
                expected = d - timedelta(days=1)
            elif d > expected:
                continue
            else:
                break

        return streak

    def get_analytics(self, period: str = "today") -> Dict[str, Any]:
        """
        Computes summary metrics, tag distributions, top activities, and streak.
        period: 'today', 'week', 'month', 'all'
        """
        local_now = datetime.now().astimezone()
        if period == "today":
            local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_dt = local_midnight.astimezone(timezone.utc)
        elif period == "week":
            start_dt = (local_now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        elif period == "month":
            start_dt = (local_now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        else:
            start_dt = None

        start_str = start_dt.isoformat() if start_dt else None
        entries = self.get_entries(limit=1000, start_date=start_str)

        total_entries = len(entries)
        total_duration = sum(e.get("duration_minutes", 0.0) for e in entries)

        # Tag breakdown
        tag_counts: Dict[str, int] = {}
        tag_duration: Dict[str, float] = {}
        activity_freq: Dict[str, int] = {}

        for e in entries:
            # Clean text activity
            txt = e["text"].strip().lower()
            if txt:
                activity_freq[txt] = activity_freq.get(txt, 0) + 1

            tags = e.get("tags", [])
            dur = e.get("duration_minutes", 0.0)
            if not tags:
                tag_counts["#untagged"] = tag_counts.get("#untagged", 0) + 1
                tag_duration["#untagged"] = tag_duration.get("#untagged", 0.0) + dur
            else:
                for t in tags:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
                    tag_duration[t] = tag_duration.get(t, 0.0) + dur

        # Top 5 activities
        top_activities = sorted(
            [{"activity": k, "count": v} for k, v in activity_freq.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:8]

        # Tag breakdown list with percentages
        tag_breakdown = []
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
            pct = round((count / total_entries * 100), 1) if total_entries > 0 else 0
            tag_breakdown.append({
                "tag": tag,
                "count": count,
                "percentage": pct,
                "duration_minutes": round(tag_duration.get(tag, 0.0), 1),
            })

        streak = self.get_streak()

        return {
            "period": period,
            "total_entries": total_entries,
            "total_duration_minutes": round(total_duration, 1),
            "total_duration_hours": round(total_duration / 60.0, 1),
            "streak_days": streak,
            "top_activities": top_activities,
            "tag_breakdown": tag_breakdown,
        }

    def export_csv(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """
        Exports entries as CSV format.
        """
        entries = self.get_entries(limit=10000, start_date=start_date, end_date=end_date)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "Activity", "Tags", "Duration (Minutes)", "Source", "Audio Path"])

        for e in reversed(entries):  # chronological
            tags_str = ", ".join(e.get("tags", []))
            writer.writerow([
                e["id"],
                e["timestamp"],
                e["text"],
                tags_str,
                e.get("duration_minutes", 0.0),
                e.get("source", "text"),
                e.get("audio_path") or "",
            ])

        return output.getvalue()

    def export_markdown(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """
        Exports entries as a clean, readable Markdown log.
        """
        entries = self.get_entries(limit=10000, start_date=start_date, end_date=end_date)
        if not entries:
            return "# BB-8 Buddy Log\n\n*No entries found.*"

        output = []
        output.append("# 🤖 BB-8 Buddy Activity Log")
        output.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        # Group by date
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for e in reversed(entries):
            day_str = e["timestamp"][:10]
            grouped.setdefault(day_str, []).append(e)

        for day, items in grouped.items():
            day_total_dur = sum(i.get("duration_minutes", 0.0) for i in items)
            output.append(f"## 📅 {day} (Total tracked: {round(day_total_dur/60.0, 1)} hrs / {len(items)} check-ins)\n")
            output.append("| Time | Activity | Tags | Duration | Source |")
            output.append("| :--- | :--- | :--- | :--- | :--- |")

            for item in items:
                time_str = item["timestamp"][11:16]
                tags_str = " ".join(f"`{t}`" for t in item.get("tags", []))
                dur_str = f"{item.get('duration_minutes', 0.0)}m" if item.get("duration_minutes") else "-"
                src_icon = "🎤" if item.get("source") == "voice" else "⌨️"
                text_clean = item["text"].replace("|", "\\|")
                output.append(f"| **{time_str}** | {text_clean} | {tags_str} | {dur_str} | {src_icon} |")

            output.append("")

        return "\n".join(output)

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["tags"] = json.loads(d.get("tags") or "[]")
        except Exception:
            d["tags"] = []
        return d

