#!/usr/bin/env python3
"""目标拆解：创作者给一个目标，拆成可逐项打勾的任务清单。

解析规则（v1 启发式，明确标注）：
- 篇数：取“发 N 篇 / N 篇”中的数字，默认 3；
- 垂类：匹配已知垂类词表，未命中则为空；
- 时间窗：下周 / 本周 / 这个月 / N 天，未命中默认“下周”。
任务链（每篇）：选题 → 标题 → 大纲 → 诊断 → 排期；最后加一项“发后复盘”。
"""
import re

NICHES = ["C语言", "美妆", "美食", "职场", "学习", "搞钱", "穿搭", "旅行", "家居", "母婴", "数码"]


def parse_goal(text):
    m = re.search(r"(\d+)\s*篇", text)
    count = int(m.group(1)) if m else 3
    count = max(1, min(count, 7))
    niche = next((n for n in NICHES if n in text), "")
    if "本周" in text:
        window = "本周"
    elif "这个月" in text or "本月" in text:
        window = "本月"
    elif re.search(r"(\d+)\s*天", text):
        window = re.search(r"(\d+)\s*天", text).group(0)
    else:
        window = "下周"
    return {"count": count, "niche": niche, "window": window}


def plan_goal(text):
    parsed = parse_goal(text)
    tasks = []
    for i in range(1, parsed["count"] + 1):
        for step in ("选题", "标题", "大纲", "诊断", "排期"):
            tasks.append({"id": f"n{i}-{step}", "note": i, "step": step,
                          "title": f"第 {i} 篇：{step}", "status": "todo"})
    tasks.append({"id": "review", "note": 0, "step": "复盘",
                  "title": "发后复盘：回填真实数据，对比预测分", "status": "todo"})
    return {"goal": text, "count": parsed["count"], "niche": parsed["niche"],
            "window": parsed["window"], "tasks": tasks}


def mark_task(plan, task_id, status="done"):
    for t in plan["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            return True
    return False
