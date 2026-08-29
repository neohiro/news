# tests/test_output.py
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from news.sources import NewsItem
from news.output import write_feeds, write_combined, _item_to_dict


def mk(title, url=None, score=0, source="x", topics=None):
    return NewsItem(
        id=title.lower().replace(" ", "-"),
        title=title, url=url, score=score, source=source, topics=topics or [],
    )


class TestOutput(unittest.TestCase):
    def test_write_feeds_creates_files(self):
        items = [mk("AI news", "https://x.com/1", 10, "gdelt", ["ai"])]
        with tempfile.TemporaryDirectory() as tmp:
            p = write_feeds(items, "test_source", tmp)
            self.assertIsNotNone(p)
            self.assertTrue(p.exists())
            data = json.loads(p.read_text())
            self.assertEqual(data["source"], "test_source")
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["items"][0]["title"], "AI news")

    def test_write_combined(self):
        items = [mk("a", "https://x.com/1"), mk("b", "https://x.com/2")]
        with tempfile.TemporaryDirectory() as tmp:
            p = write_combined(items, tmp)
            self.assertIsNotNone(p)
            data = json.loads(p.read_text())
            self.assertEqual(data["count"], 2)

    def test_item_to_dict_excludes_raw(self):
        item = NewsItem(id="i", title="T", url="u", score=1, source="s", topics=[], raw={"secret": "x"})
        d = _item_to_dict(item)
        self.assertNotIn("raw", d)
        self.assertNotIn("secret", d)


if __name__ == "__main__":
    unittest.main()
