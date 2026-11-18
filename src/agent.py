#!/usr/bin/env python3
"""Agent 主体：意图路由 + 多轮对话 + 记忆 + 目标拆解 + 发后复盘。

意图识别为 v1 关键词启发式（明确标注，非语义理解）：
- 含“发 N 篇”/“目标…篇”→ 定目标并拆任务
- 含“选题”→ 生成 3 个选题
- “再改一版”/“换个风格”→ 按上一篇笔记的关键词重写标题
- 含“复盘”/“回填”/“发完了”→ 解析阅读/点赞/收藏数做复盘
- 含“画像”/“体检”→ 账号体检报告
- 其余 → LLM 对话（模板模式或盘古，失败自动回落并明示）
"""
import re

from . import rules
from .llm import get_llm, TemplateLLM
from .planner import plan_goal, mark_task
from .review import review_note
from .session import Store
from .topics import generate_topics, generate_draft_note


class Agent:
    def __init__(self, data_root):
        self.store = Store(data_root)
        self.patterns, self.c_patterns, self.risks, self.tags_db, self.times = rules.load_data()
        self.llm = get_llm()

    # ---- 对话入口 ----
    def handle(self, session_id, text):
        session = self.store.load_session(session_id)
        profile = self.store.load_profile(session_id)
        text = (text or "").strip()
        if not text:
            return {"reply": "说点什么吧：定目标、要选题、诊断笔记、复盘都可以。",
                    "mode": self.llm.mode, "mode_note": ""}
        reply, mode_note = self._route(session, profile, text)
        session["messages"].append({"role": "user", "content": text})
        session["messages"].append({"role": "assistant", "content": reply})
        session["messages"] = session["messages"][-40:]
        self.store.save_session(session_id, session)
        self.store.save_profile(session_id, profile)
        return {"reply": reply, "mode": self.llm.mode, "mode_note": mode_note}

    def _ctx(self, session):
        goal = session.get("goal") or {}
        return {"last_score": session.get("last_score"),
                "last_dims": session.get("last_dims"),
                "goal": goal.get("goal") if isinstance(goal, dict) else None}

    def _route(self, session, profile, text):
        # 1）定目标
        if re.search(r"发\s*\d+\s*篇", text) or ("目标" in text and "篇" in text):
            plan = plan_goal(text)
            session["goal"] = plan
            profile["goals"].append(plan)
            if plan["niche"]:
                profile["niche"] = plan["niche"]
            lines = [f"目标已定：{plan['window']}发 {plan['count']} 篇"
                     + (f"（{plan['niche']}）" if plan["niche"] else "") + "。已拆成任务清单："]
            lines += [f"□ {t['title']}" for t in plan["tasks"]]
            lines.append("先从第 1 篇的选题开始：说“给我 3 个选题”。")
            return "\n".join(lines), ""
        # 2）选题
        if "选题" in text:
            niche = profile.get("niche") or "C语言"
            kws = self._extract_keywords(text, niche)
            topics = generate_topics(niche, kws, self.patterns)
            lines = [f"{niche}选题（关键词：{'、'.join(kws)}）："]
            for i, tp in enumerate(topics, 1):
                lines.append(f"{i}. 【{tp['hook']}】{tp['title']}")
                lines.append(f"   {tp['tip']}；大纲：{' → '.join(tp['outline'])}")
            lines.append("挑一个，我帮你往下走标题和大纲。")
            return "\n".join(lines), ""
        # 3）再改一版
        if text.startswith("再改") or "换个风格" in text or "再改一版" in text:
            last = session.get("last_note") or {}
            if not last:
                return "还没有诊断过的笔记，先在上方表单粘贴一篇笔记做诊断，我再帮你改。", ""
            kws = last.get("keywords") or ["关键词"]
            pats = (self.c_patterns if rules.is_c_domain(profile.get("niche"), "")
                    else self.patterns)
            rewrites = rules.rewrite_titles(kws, pats)
            lines = ["按原关键词再改一版（句式模板改写）："]
            for n, t, m, tip, ex in rewrites:
                lines.append(f"**{n}**：{t}（{tip}）")
                if m:
                    lines.append(f"   待填：{'、'.join(m)}")
            return "\n".join(lines), ""
        # 4）发后复盘
        if "复盘" in text or "回填" in text or "发完了" in text:
            reads = self._num(text, "阅读")
            likes = self._num(text, "点赞")
            collects = self._num(text, "收藏")
            last = session.get("last_note") or {}
            if reads is None or likes is None or collects is None:
                return "把发后的真实数据发我，格式：阅读 X 点赞 Y 收藏 Z，我来复盘。", ""
            if not last:
                return "还没有诊断记录，复盘需要一篇已诊断的笔记作预测分对照。", ""
            res = review_note(last["score"], reads, likes, collects)
            profile["learnings"].append(
                f"《{last['title']}》预测 {last['score']} 分，实际{res['verdict']}（互动率 {res['engagement_rate']:.1%}）：{res['lesson']}")
            if session.get("goal"):
                mark_task(session["goal"], "review", "done")
            lines = [f"复盘《{last['title']}》：预测 {last['score']} 分，"
                     f"阅读 {reads}、点赞 {likes}、收藏 {collects}，互动率 {res['engagement_rate']:.1%}，{res['verdict']}。",
                     res["lesson"],
                     "这条结论已记进账号画像，下次诊断会参考。"]
            return "\n".join(lines), ""
        # 5）写草稿：按主题生成一篇 C 语言教学笔记草稿（模板拼装，非大模型生成）
        if "草稿" in text or "写一篇" in text or "帮我写" in text:
            niche = profile.get("niche") or "C语言"
            t = text
            for w in ("帮我写", "写一篇", "草稿", "一篇", "来一篇", "关于"):
                t = t.replace(w, "")
            t = t.replace(niche, "")
            kws = [k.strip() for k in re.split(r"[,，、\s]+", t) if k.strip()]
            topic = (kws[0].rstrip("的") if kws else niche)
            draft = generate_draft_note(topic, kws or [topic],
                                        niche=profile.get("niche") or "",
                                        tags_db=self.tags_db)
            tail = ("草稿里的代码已通过本地 gcc -Wall 编译验证，可直接改着用。"
                    if draft.get("code_standalone") else
                    "草稿是模板拼装，填上自己的内容再发布。")
            lines = ["【笔记草稿】（模板拼装，须改写后发布）",
                     f"标题：{draft['title']}", "",
                     draft["body"], "",
                     tail]
            return "\n".join(lines), ""
        # 6）画像 / 体检
        if "画像" in text or "体检" in text:
            return self.profile_summary(profile), ""
        # 7）默认对话
        try:
            reply = self.llm.chat(text, self._ctx(session))
            note = ("（模板模式：确定性模板回复，未接大模型）"
                    if self.llm.mode == "template" else "")
            return reply, note
        except Exception:
            reply = TemplateLLM().chat(text, self._ctx(session))
            return reply, "盘古调用失败，已回落到模板模式。"

    # ---- 诊断 ----
    def diagnose(self, session_id, title, body, niche, keywords):
        session = self.store.load_session(session_id)
        profile = self.store.load_profile(session_id)
        result = rules.diagnose_note(title, body, niche, keywords,
                                     self.patterns, self.risks, self.tags_db,
                                     self.c_patterns, self.times)
        note = {"id": f"n{len(profile['notes']) + 1}", "title": title,
                "score": result["total"], "dims": result["dims"],
                "niche": niche, "keywords": list(keywords)}
        profile["notes"].append(note)
        if niche:
            profile["niche"] = niche
        session["last_note"] = note
        session["last_score"] = result["total"]
        session["last_dims"] = result["dims"]
        if session.get("goal"):
            for t in session["goal"]["tasks"]:
                if t["step"] == "诊断" and t["status"] == "todo":
                    t["status"] = "done"
                    break
        self.store.save_session(session_id, session)
        self.store.save_profile(session_id, profile)
        return result

    # ---- 复盘（API 直调）----
    def review(self, session_id, reads, likes, collects):
        session = self.store.load_session(session_id)
        profile = self.store.load_profile(session_id)
        last = session.get("last_note") or {}
        if not last:
            return {"error": "还没有诊断记录，复盘需要一篇已诊断的笔记作预测分对照。"}
        res = review_note(last["score"], reads, likes, collects)
        profile["learnings"].append(
            f"《{last['title']}》预测 {last['score']} 分，实际{res['verdict']}（互动率 {res['engagement_rate']:.1%}）：{res['lesson']}")
        if session.get("goal"):
            mark_task(session["goal"], "review", "done")
        self.store.save_session(session_id, session)
        self.store.save_profile(session_id, profile)
        return {"note": last, **res}

    # ---- 画像 ----
    def profile_summary(self, profile):
        notes = profile.get("notes") or []
        if not notes:
            return "还没有诊断记录。先诊断一篇笔记，我再给你画像。"
        scores = [n["score"] for n in notes]
        avg = sum(scores) / len(scores)
        dim_sums = {}
        for n in notes:
            for k, v in n["dims"].items():
                dim_sums[k] = dim_sums.get(k, 0) + v
        worst = min(dim_sums, key=lambda k: dim_sums[k] / len(notes))
        lines = [f"账号体检：已诊断 {len(notes)} 篇，平均 {avg:.1f} 分。",
                 "分数趋势：" + " → ".join(str(s) for s in scores),
                 f"最弱的一维是{worst}（平均 {dim_sums[worst] / len(notes):.1f} 分），下周重点补这一维。"]
        learnings = profile.get("learnings") or []
        if learnings:
            lines.append("复盘沉淀：")
            lines += [f"- {x}" for x in learnings[-5:]]
        return "\n".join(lines)

    # ---- 工具 ----
    @staticmethod
    def _extract_keywords(text, niche):
        t = re.sub(r"(给我|来)?\s*(3|三)?\s*个?选题", "", text)
        t = t.replace(niche, "")
        kws = [k.strip() for k in re.split(r"[,，、\s]+", t) if k.strip()]
        return kws or ["关键词"]

    @staticmethod
    def _num(text, key):
        m = re.search(key + r"\D*(\d+)", text)
        return int(m.group(1)) if m else None
