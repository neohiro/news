# tests/test_frequency.py
# Unit tests for the frequency analyzer.

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from news.frequency import (
    token_frequency,
    topic_frequency,
    region_frequency,
    detect_breaks,
    build_digest,
    write_digest,
)


SAMPLE_ITEMS = [
    {
        "id": "1", "title": "AI breakthrough in medical research",
        "url": "https://example.com/1", "source": "GDELT",
        "score": 50, "topics": ["ai", "health"],
        "country": "US", "lat": 37.7, "lon": -122.4,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "2", "title": "OpenAI releases new AI model",
        "url": "https://example.com/2", "source": "GDELT",
        "score": 30, "topics": ["ai"],
        "country": "US", "lat": 37.7, "lon": -122.4,
        "fetched_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    },
    {
        "id": "3", "title": "Critical cybersecurity vulnerability found",
        "url": "https://example.com/3", "source": "GDELT",
        "score": 80, "topics": ["security"],
        "country": "Japan", "lat": 35.7, "lon": 139.7,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "4", "title": "Climate change conference begins",
        "url": "https://example.com/4", "source": "GDELT",
        "score": 5, "topics": ["climate"],
        "country": "Bangladesh", "lat": 23.8, "lon": 90.4,
        "fetched_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
    },
]


class TestFrequency(unittest.TestCase):
    def test_token_frequency(self):
        freq = token_frequency(SAMPLE_ITEMS)
        # "ai" is 3 chars (below min_len=4), so it shouldn't be in results
        # "openai" should be present
        self.assertIn("openai", freq)
        self.assertIn("critical", freq)
        self.assertIn("vulnerability", freq)
        # Stop words excluded
        self.assertNotIn("the", freq)
        self.assertNotIn("in", freq)

    def test_topic_frequency_grouping(self):
        result = topic_frequency(SAMPLE_ITEMS)
        topics = {r.topic: r.count for r in result}
        self.assertEqual(topics["ai"], 2)
        self.assertEqual(topics["security"], 1)
        self.assertEqual(topics["climate"], 1)

    def test_topic_centroid(self):
        result = topic_frequency(SAMPLE_ITEMS)
        ai = next(r for r in result if r.topic == "ai")
        # 2 items, both at (37.7, -122.4)
        self.assertAlmostEqual(ai.lat_lon_centroid[0], 37.7, places=2)
        self.assertAlmostEqual(ai.lat_lon_centroid[1], -122.4, places=2)

    def test_region_frequency(self):
        result = region_frequency(SAMPLE_ITEMS)
        self.assertEqual(result["US"]["count"], 2)
        self.assertEqual(result["Japan"]["count"], 1)
        self.assertIn("ai", result["US"]["topics"])

    def test_detect_breaks_recent(self):
        breaks = detect_breaks(SAMPLE_ITEMS, window_minutes=120)
        # Items 1, 2, 3 are within 2 hours. Item 4 is 2 days old → excluded
        self.assertEqual(len(breaks), 3)
        # Item 4 should NOT be in breaks
        ids = [b["id"] for b in breaks]
        self.assertNotIn("4", ids)

    def test_detect_breaks_filters_low_score_no_geo(self):
        # Add a recent low-score item without geo
        items = SAMPLE_ITEMS + [{
            "id": "5", "title": "boring low score",
            "url": "", "source": "x", "score": 1, "topics": [],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }]
        breaks = detect_breaks(items, window_minutes=60)
        self.assertNotIn("5", [b["id"] for b in breaks])

    def test_build_digest(self):
        digest = build_digest(SAMPLE_ITEMS)
        self.assertEqual(digest["item_count"], 4)
        self.assertIn("topics", digest)
        self.assertIn("regions", digest)
        self.assertIn("breaking", digest)
        self.assertIn("top_words", digest)
        # Climate (2 days old) should not be in breaking
        breaking_topics = {b.get("topics", [])[0] if b.get("topics") else "" for b in digest["breaking"]}
        self.assertNotIn("climate", breaking_topics)

    def test_write_digest(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = write_digest(SAMPLE_ITEMS, tmp)
            self.assertIsNotNone(path)
            self.assertTrue(path.exists())
            import json
            data = json.loads(path.read_text())
            self.assertEqual(data["item_count"], 4)


if __name__ == "__main__":
    unittest.main()
