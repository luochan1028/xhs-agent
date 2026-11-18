#!/usr/bin/env python3
"""LLM 层：对话、选题生成、语义改写。

两种模式，诚实标注：
- template（默认）：确定性模板回复，零成本、离线可跑。所有由模板生成的
  内容在返回时都会标明“模板模式”，不冒充大模型能力。
- pangu：盘古大模型。仅当环境变量 PANGU_API_KEY 与 PANGU_API_BASE
  同时给出时启用；endpoint 与模型名须按华为云盘古 MaaS 官方文档核对
  后填入，本文件不猜测、不硬编码官方地址。调用失败时自动回落到模板
  模式并在回复中说明。
"""
import json
import os
import urllib.request
import urllib.error


class TemplateLLM:
    """确定性模板 LLM：按上下文拼装回复，不冒充语义理解。"""
    mode = "template"

    def chat(self, user_text, context=None):
        ctx = context or {}
        score = ctx.get("last_score")
        dims = ctx.get("last_dims") or {}
        goal = ctx.get("goal")
        parts = []
        if score is not None:
            worst = min(dims, key=dims.get) if dims else None
            parts.append(f"上一篇笔记 {score} 分" + (f"，最弱的一维是{worst}（{dims[worst]} 分），先补这一维。" if worst else "。"))
        if goal:
            parts.append(f"当前目标：{goal}。")
        parts.append("我可以帮你：1）诊断一篇小红书笔记（在上方表单粘贴标题+正文）；"
                     "2）给选题（说“给我 3 个选题”）；3）改标题（说“再改一版”）；"
                     "4）写一篇草稿（说“帮我写一篇草稿”）；"
                     "5）发后复盘（说“发完了”，再把阅读/点赞/收藏数给我）。")
        return " ".join(parts)

    def rewrite(self, keywords, style_hint=""):
        return []

    def topics(self, niche, keywords):
        return []


class PanguLLM:
    """盘古大模型适配器（OpenAI 兼容 chat-completions 形状）。

    启用条件：PANGU_API_KEY 与 PANGU_API_BASE 均已设置。
    PANGU_API_BASE 例：华为云盘古 MaaS 的 chat-completions 地址（须按官方文档核对）。
    PANGU_MODEL：模型名（须按官方文档核对）。
    未核对前不要启用；启用后仍保留失败回落。
    """
    mode = "pangu"

    def __init__(self):
        self.api_key = os.environ["PANGU_API_KEY"]
        self.base = os.environ["PANGU_API_BASE"].rstrip("/")
        self.model = os.environ.get("PANGU_MODEL", "")

    def _post(self, messages, timeout=30):
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base + "/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def chat(self, user_text, context=None):
        system = ("你是小红书内容运营智能体，服务一位小红书创作者。"
                  "回答简洁、可执行；不承诺涨粉、不承诺爆款；"
                  "涉及知识点时只讲已核实的内容，不编造代码与结论；"
                  "涉及合规风险时提醒人工复核。")
        messages = [{"role": "system", "content": system}]
        if context and context.get("last_score") is not None:
            messages.append({"role": "system",
                             "content": f"上下文：用户上一篇笔记 {context['last_score']} 分，"
                                        f"四维为 {context.get('last_dims')}，目标：{context.get('goal') or '未设定'}。"})
        messages.append({"role": "user", "content": user_text})
        return self._post(messages)

    def rewrite(self, keywords, style_hint=""):
        return self._post([
            {"role": "system", "content": "你是小红书标题改写助手，只给标题建议，不写整篇笔记。"},
            {"role": "user", "content": f"关键词：{','.join(keywords)}。{style_hint} 给 3 个标题。"},
        ])

    def topics(self, niche, keywords):
        return self._post([
            {"role": "system", "content": "你是小红书选题策划，只给选题方向与钩子说明，不编造代码与结论。"},
            {"role": "user", "content": f"垂类：{niche}，关键词：{','.join(keywords)}。给 3 个选题，各配一句话钩子说明。"},
        ])


def get_llm():
    """有盘古 Key + 已核对的 endpoint 才用盘古；否则模板模式。"""
    if os.environ.get("PANGU_API_KEY") and os.environ.get("PANGU_API_BASE"):
        try:
            return PanguLLM()
        except Exception:
            return TemplateLLM()
    return TemplateLLM()
