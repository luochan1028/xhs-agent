import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import rules, topics


def _load_note(path):
    raw = (ROOT / path).read_text(encoding="utf-8").strip().split("\n")
    return raw[0].strip(), "\n".join(raw[1:]).strip()


class TestCDomain(unittest.TestCase):
    def test_correct_c_note_scores_high(self):
        """(a) 正确的 C 教学笔记得分高（准确性满分）。"""
        title, body = _load_note("data/sample_notes/c_pointer.txt")
        res = rules.diagnose_note(title, body, "C语言", ["指针", "3天"])
        self.assertGreaterEqual(res["total"], 80)
        self.assertEqual(res["dims"]["C语言准确性"], 10)
        self.assertIn("🟢", res["verdict"])

    def test_grade_stats_note_scores_high(self):
        """(a2) 实验二样例笔记得分高（准确性满分）。"""
        title, body = _load_note("data/sample_notes/c_grade_stats.txt")
        res = rules.diagnose_note(title, body, "C语言", ["成绩统计", "循环"])
        self.assertGreaterEqual(res["total"], 80)
        self.assertEqual(res["dims"]["C语言准确性"], 10)

    def test_error_example_not_penalized(self):
        """标注为错误示例的反例行不判为硬错误（常见错误样例笔记）。"""
        title, body = _load_note("data/sample_notes/c_mistakes.txt")
        res = rules.diagnose_note(title, body, "C语言", ["新手", "避雷"])
        self.assertEqual(res["dims"]["C语言准确性"], 10)
        self.assertGreaterEqual(res["total"], 80)

    def test_wrong_c_note_scores_low(self):
        """(b) 含错误 C 代码的笔记得分低（准确性硬门槛封顶 59）。"""
        title, body = _load_note("tests/fixtures/wrong_c_note.txt")
        res = rules.diagnose_note(title, body, "C语言", ["指针", "3天"])
        self.assertEqual(res["dims"]["C语言准确性"], 0)
        self.assertLessEqual(res["total"], 59)
        self.assertIn("🔴", res["verdict"])

    def test_c_draft_compiles(self):
        """(c) 对给定主题能生成 C 教学笔记草稿，内嵌代码可编译运行。"""
        draft = topics.generate_draft_note("指针", ["指针"])
        self.assertIn("指针", draft["title"])
        m = re.search(r"```c\n(.*?)```", draft["body"], re.S)
        self.assertIsNotNone(m, "草稿正文须含 ```c 代码块")
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "draft.c"
            src.write_text(m.group(1), encoding="utf-8")
            r = subprocess.run(["gcc", "-Wall", "-o", str(Path(td) / "draft"), str(src)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"草稿代码编译失败：{r.stderr}")
            self.assertEqual(r.stderr.strip(), "", f"编译有警告：{r.stderr}")
            out = subprocess.run([str(Path(td) / "draft")], capture_output=True, text=True)
            self.assertEqual(out.stdout.strip(), "10")

    def test_all_snippets_compile(self):
        """全部草稿代码示例均可 gcc -Wall 零警告编译。"""
        for key, snip in topics.C_SNIPPETS.items():
            with tempfile.TemporaryDirectory() as td:
                src = Path(td) / "s.c"
                src.write_text(snip["code"], encoding="utf-8")
                r = subprocess.run(["gcc", "-Wall", "-o", str(Path(td) / "s"), str(src)],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"{key} 编译失败：{r.stderr}")
                self.assertEqual(r.stderr.strip(), "", f"{key} 编译有警告：{r.stderr}")
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "s.c"
            src.write_text(topics.DEFAULT_SNIPPET["code"], encoding="utf-8")
            r = subprocess.run(["gcc", "-Wall", "-o", str(Path(td) / "s"), str(src)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"默认示例编译失败：{r.stderr}")
            self.assertEqual(r.stderr.strip(), "", f"默认示例编译有警告：{r.stderr}")

    def test_agent_draft_route(self):
        """Agent 对话能按主题生成草稿。"""
        import tempfile as _tf
        from src.agent import Agent
        with _tf.TemporaryDirectory() as td:
            agent = Agent(Path(td) / "data")
            r = agent.handle("default", "帮我写一篇指针的草稿")
            self.assertIn("指针", r["reply"])
            self.assertIn("```c", r["reply"])
            self.assertIn("int main", r["reply"])

    def test_c_topics_use_c_outline(self):
        """C 领域选题用专用大纲（概念 + 最小代码 + 练习）。"""
        tps = topics.generate_topics("C语言", ["指针"], rules.load_data()[0])
        self.assertEqual(len(tps), 3)
        self.assertIn("最小代码", tps[0]["outline"][1])


if __name__ == "__main__":
    unittest.main()
