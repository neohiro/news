# tests/test_normalizer.py
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from news.sources import NewsItem
from news.normalizer import normalize, _similar, _rerank, group_by_topic


def mk(title, url=None, score=0, source="x", topics=None):
    return NewsItem(id=title, title=title, url=url, score=score, source=source, topics=topics or [])


class TestNormalizer(unittest.TestCase):
    def test_dedup_by_url(self):
        a = mk("A", url="https://x.com/1", score=10)
        b = mk("A", url="https://x.com/1", score=5)
        out = normalize([a, b])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].score, 10)

    def test_dedup_by_title_similarity(self):
        a = mk("Major AI breakthrough in medical research", url="https://x.com/1", score=10)
        b = mk("Major AI breakthrough in medical science", url="https://x.com/2", score=8)
        out = normalize([a, b])
        self.assertEqual(len(out), 1)

    def test_keeps_distinct(self):
        a = mk("AI news", url="https://x.com/1", score=10)
        b = mk("Sports news", url="https://x.com/2", score=5)
        out = normalize([a, b])
        self.assertEqual(len(out), 2)

    def test_rerank_adds_topic_bonus(self):
        a = mk("AI thing", score=0, topics=["ai"])
        b = mk("boring", score=0, topics=[])
        out = normalize([a, b])
        # AI should rank higher
        self.assertEqual(out[0].title, "AI thing")

    def test_rerank_caps_at_1000(self):
        a = mk("AI", score=900, topics=["ai", "llm"])
        out = normalize([a])
        self.assertLessEqual(out[0].score, 1000)

    def test_similar_threshold(self):
        self.assertTrue(_similar("hello world", "hello world", 0.75))
        self.assertFalse(_similar("hello", "world", 0.75))

    def test_group_by_topic(self):
        items = [mk("a", topics=["ai"]), mk("b", topics=["ai", "security"]), mk("c", topics=[])]
        g = group_by_topic(items)
        self.assertEqual(len(g["ai"]), 2)
        self.assertEqual(len(g["security"]), 1)
        self.assertEqual(len(g["uncategorized"]), 1)


if __name__ == "__main__":
    unittest.main()
