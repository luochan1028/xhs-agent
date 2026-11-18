#!/usr/bin/env python3
"""发后复盘：预测分 vs 真实数据，对比后给出结论并沉淀经验。

互动率阈值为启发式（非平台官方口径），仅作复盘参考，
不承诺任何流量结果；结论只谈“这篇为什么”，不推导“下一篇一定爆”。
"""


def review_note(predicted, reads, likes, collects):
    er = (likes + collects) / max(reads, 1)
    if er >= 0.12:
        verdict, level = "超预期", "high"
    elif er >= 0.06:
        verdict, level = "符合预期", "ok"
    elif er >= 0.03:
        verdict, level = "低于预期", "low"
    else:
        verdict, level = "明显低于预期", "very_low"
    if predicted >= 80 and level in ("low", "very_low"):
        lesson = ("预测分高但真实互动低：可能是标题钩子与正文承诺脱节，"
                  "或 C 语言知识点讲得不够准、代码示例没跑通过，"
                  "或发布时间/标签入口问题；下次先查正文前三行是否兑现了标题承诺，"
                  "再核对代码是否编译通过。")
    elif predicted < 60 and level in ("high", "ok"):
        lesson = "预测分不高但真实互动好：标题或选题本身命中了需求；把这篇的钩子结构记下来，复用到下一篇。"
    elif level in ("high", "ok"):
        lesson = "预测与真实一致：这套打法有效，继续沿用，并把互动最高的段落结构固定下来。"
    else:
        lesson = "预测与真实都偏弱：先回炉标题与正文前三行，再检查 C 语言知识点是否准确、代码是否编译通过，最后看标签数量与发布时间。"
    return {
        "predicted": predicted,
        "reads": reads,
        "likes": likes,
        "collects": collects,
        "engagement_rate": round(er, 4),
        "verdict": verdict,
        "level": level,
        "lesson": lesson,
    }
