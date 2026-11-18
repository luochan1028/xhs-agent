import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import Agent


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = Agent(Path(self.tmp.name) / "data")

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_loop(self):
        """全流程冒烟：定目标 → 选题 → 诊断 → 改写 → 复盘 → 体检。"""
        r = self.agent.handle("default", "下周发 3 篇美食笔记，冲一篇爆款")
        self.assertIn("目标已定", r["reply"])
        self.assertEqual(r["mode"], "template")

        r = self.agent.handle("default", "给我 3 个选题，减脂餐")
        self.assertIn("选题", r["reply"])

        raw = (ROOT / "tests" / "fixtures" / "sample_note.txt").read_text(
            encoding="utf-8").strip().split("\n")
        res = self.agent.diagnose("default", raw[0].strip(),
                                  "\n".join(raw[1:]).strip(),
                                  "美食", ["减脂餐", "30天", "8斤"])
        self.assertEqual(res["total"], 45)

        r = self.agent.handle("default", "再改一版")
        self.assertIn("改写", r["reply"])

        r = self.agent.handle("default", "发完了，阅读 1000 点赞 120 收藏 80")
        self.assertIn("复盘", r["reply"])
        self.assertIn("超预期", r["reply"])

        r = self.agent.handle("default", "我的画像")
        self.assertIn("账号体检", r["reply"])

        session = self.agent.store.load_session("default")
        done = [t for t in session["goal"]["tasks"] if t["status"] == "done"]
        self.assertTrue(any(t["step"] == "诊断" for t in done))
        self.assertTrue(any(t["step"] == "复盘" for t in done))

    def test_rewrite_without_note(self):
        r = self.agent.handle("default", "再改一版")
        self.assertIn("先在上方表单粘贴一篇笔记", r["reply"])


if __name__ == "__main__":
    unittest.main()
