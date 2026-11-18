import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import rules


class TestRules(unittest.TestCase):
    def test_sample_note_scores_45(self):
        """回归：Skill 版实测 45 分样本（标题 23/正文 8/标签 9/合规 5）。"""
        raw = (ROOT / "tests" / "fixtures" / "sample_note.txt").read_text(
            encoding="utf-8").strip().split("\n")
        title, body = raw[0].strip(), "\n".join(raw[1:]).strip()
        res = rules.diagnose_note(title, body, "美食", ["减脂餐", "30天", "8斤"])
        self.assertEqual(res["total"], 45)
        self.assertEqual(res["dims"], {"标题吸引力": 23, "正文质量": 8,
                                       "标签曝光": 9, "合规安全": 5})
        self.assertEqual(len(res["rewrites"]), 3)

    def test_clean_note_scores_high(self):
        """对照：对标爆款样本应明显高于 45 分样本。"""
        raw = (ROOT / "tests" / "fixtures" / "ref_note.txt").read_text(
            encoding="utf-8").strip().split("\n")
        title, body = raw[0].strip(), "\n".join(raw[1:]).strip()
        res = rules.diagnose_note(title, body, "美食", ["减脂餐", "30天", "8斤"])
        self.assertGreater(res["total"], 45)

    def test_diagnose_includes_publish_times(self):
        """诊断结果须含发布时间建议（与试用页同口径：3 个平时段 + 周末 + 提示）。"""
        raw = (ROOT / "tests" / "fixtures" / "sample_note.txt").read_text(
            encoding="utf-8").strip().split("\n")
        title, body = raw[0].strip(), "\n".join(raw[1:]).strip()
        res = rules.diagnose_note(title, body, "美食", ["减脂餐", "30天", "8斤"])
        self.assertIn("times", res)
        self.assertEqual(len(res["times"]["general"]), 3)
        self.assertEqual(len(res["times"]["weekend"]), 1)
        self.assertIn("21:00-23:00",
                      [t["time"] for t in res["times"]["general"]])
        self.assertTrue(res["times"]["tip"])


if __name__ == "__main__":
    unittest.main()
