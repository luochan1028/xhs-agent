#!/usr/bin/env python3
"""规则校验层：五维评分 + 标题改写 + 封面初检。

评分结构（v1.1）：通用四维（标题 30 / 正文 25 / 标签 15 / 合规 20，
满分 90）+ C 语言准确性（第 5 维，满分 10，仅 C 语言领域笔记计入，
C 领域满分 100）。教学准确性是硬门槛：检测到 C 硬错误时总分封顶 59 分。
来源：同一作者的 Skill 版作品 xhs-optimizer（scripts/optimize.py），
评分口径与函数逻辑原样复用，作 Agent 版的确定性校验层。
数据文件在 xhs-agent/data/（与 Skill 版同源，版本一致）。
改动：BASE 指向本仓库根目录；新增 diagnose_note() 便捷封装；
v1.1 新增 C 语言准确性维度与 C 标题句式（c_patterns）。
风险词库为示例版，命中请人工复核；封面只做尺寸比例初检。
"""
import re
from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parent.parent
DIGITS = re.compile(r"\d+")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]")
INTERACT = re.compile(r"(你们|姐妹们|评论区|留言|投票|你怎么看|试过吗|有用吗)")
CLICKBAIT_OVER = re.compile(r"(震惊|竟然|天啊|救命|离谱|吓死)")


def load_data():
    d = BASE / "data"
    patterns = yaml.safe_load((d / "title_patterns.yaml").read_text(encoding="utf-8"))["patterns"]
    c_patterns = yaml.safe_load((d / "title_patterns.yaml").read_text(encoding="utf-8")).get("c_patterns") or []
    risks = [w.strip() for w in (d / "risk_words.txt").read_text(encoding="utf-8").split("\n")
             if w.strip() and not w.strip().startswith("#")]
    tags = yaml.safe_load((d / "tags.yaml").read_text(encoding="utf-8"))["niches"]
    times = yaml.safe_load((d / "post_times.yaml").read_text(encoding="utf-8"))
    return patterns, c_patterns, risks, tags, times


# ---- C 语言教学准确性（v1.1 新增，第 5 维，硬门槛）----
C_NICHES = {"C语言", "C语言学习", "C语言入门", "编程", "程序设计"}
C_CODE_MARKERS = ("#include", "int main", "printf(", "scanf(", "void main",
                  "C语言", "指针")
# 错误示例行标记：同一行含这些词，视为教学用的反例展示，不判为硬错误。
# 错误示例须与标注写在同一行，否则会被判为硬错误。
ERROR_EXAMPLE_MARKERS = ("错误", "反例", "❌", "不要这样", "错误写法", "错误示例")


def is_c_domain(niche, body):
    """是否 C 语言教学笔记：垂类是 C 相关，或正文含 C 代码/关键词。"""
    if (niche or "") in C_NICHES:
        return True
    return any(m in (body or "") for m in C_CODE_MARKERS)


def _scanf_missing_amp(line):
    """返回一行里 scanf 缺 & 的硬错误描述。%s（字符数组）不需要 &，跳过。"""
    errs = []
    for m in re.finditer(r'scanf\s*\(\s*"([^"]*)"\s*,([^)]*)\)', line):
        fmt, args = m.group(1), m.group(2)
        specs = re.findall(r"%[0-9.]*[hlL]?([difuoxcs])", fmt)
        arg_list = [a.strip() for a in args.split(",")]
        for i, spec in enumerate(specs):
            if spec in ("d", "i", "f", "u", "o", "x", "c"):
                if i < len(arg_list) and not arg_list[i].startswith("&"):
                    errs.append(f"scanf 第 {i + 1} 个参数缺少 &（%{spec} 须传地址）")
    return errs


def diagnose_c_accuracy(body):
    """C 语言准确性（第 5 维，满分 10）。只扣分：每处硬错误 -5，最低 0。
    出现任何硬错误，总分封顶 59（见 diagnose_note）。
    带 错误/反例/❌ 标注的行视为教学反例，不计分。"""
    score, notes, hard = 10, [], []
    for line in (body or "").split("\n"):
        if any(m in line for m in ERROR_EXAMPLE_MARKERS):
            continue
        if re.search(r"void\s+main\s*\(", line):
            hard.append("void main 应为 int main")
        if re.search(r"\bgets\s*\(", line):
            hard.append("gets 已废弃且不安全，改用 fgets")
        if re.search(r"if\s*\(\s*[A-Za-z_]\w*\s*=\s*[^=]", line):
            hard.append("if 条件里用了赋值 =，比较要用 ==")
        hard.extend(_scanf_missing_amp(line))
        if re.search(r'printf\s*\(\s*"[^"]*%d[^"]*"\s*,\s*\d+\.\d+', line):
            hard.append("printf 用 %d 输出小数，格式与实参不匹配")
        if re.search(r'printf\s*\(\s*"[^"]*%f[^"]*"\s*,\s*\d+\s*[,)]', line):
            hard.append("printf 用 %f 输出整数，格式与实参不匹配")
        m = re.search(r"C\s*语言([^。]{0,20})面向对象", line)
        if m and "不" not in m.group(1):
            hard.append("C 语言不是面向对象语言")
        if re.search(r"数组越界[^。不]{0,15}(安全|没关系|可以|没问题)", line):
            hard.append("数组越界是未定义行为，不安全")
        if re.search(r"scanf[^。]{0,15}不(需要|用).*&", line):
            hard.append("scanf 读数值须传地址（加 &）")
        m = re.search(r"指针(.{0,10})数组(.{0,10})(完全一样|就是一回事|没有区别)", line)
        if m and "不" not in (m.group(1) + m.group(2)):
            hard.append("指针与数组不是一回事")
        if re.search(r"字符串.{0,10}不(需要|用).{0,5}(\\0|结束符|'\\0')", line):
            hard.append(r"C 字符串须以 \0 结尾")
        if re.search(r"switch[^。]{0,15}不(需要|用).*break", line):
            hard.append("switch 的 break 不能一概省略")
        if re.search(r"递归[^。]{0,15}不(需要|用).{0,8}(终止|出口|结束)", line):
            hard.append("递归必须有终止条件")
        if re.search(r"gets[^。不没]{0,10}安全", line):
            hard.append("gets 不安全")
        if re.search(r"内存泄漏[^。]{0,10}(没关系|没事|不重要)", line):
            hard.append("内存泄漏不能忽视")
        if re.search(r"main\s*函数[^。不]{0,8}可以[^。]{0,4}void", line):
            hard.append("main 函数返回值应为 int，不是 void")
    for h in hard:
        score = max(score - 5, 0)
        notes.append(f"🚨 硬错误：{h}")
    if not hard:
        if "#include <stdio.h>" in (body or "") and "int main" in (body or ""):
            notes.append("✅ 代码含规范的 #include 与 int main")
        else:
            notes.append("✅ 未检测到 C 语言硬错误")
    return score, notes, hard


def diagnose_title(title, patterns):
    score, notes = 30, []
    n = len(title)
    if n <= 20:
        notes.append(f"✅ 标题 {n} 字，长度合适（小红书标题建议≤20字）")
    else:
        score -= 8
        notes.append(f"⚠️ 标题 {n} 字偏长，信息流中会被折叠，建议压缩到20字内")
    if DIGITS.search(title):
        notes.append("✅ 含数字，具体感强")
    else:
        score -= 4
        notes.append("⚠️ 标题无数字，加上具体数字点击率更高")
    if "?" in title or "？" in title or "!" in title or "！" in title:
        notes.append("✅ 有疑问/感叹语气，情绪钩子到位")
    else:
        score -= 3
        notes.append("⚠️ 缺情绪钩子，试试反问或感叹句式")
    if CLICKBAIT_OVER.search(title):
        score -= 5
        notes.append("⚠️ 标题党词汇过重，易被限流且伤信任")
    hit = [p["name"] for p in patterns if any(k in title for k in ("怎么", "为什么", "避雷", "秘密", "天", "块"))]
    notes.append("✅ 命中高点击句式特征" if hit else "ℹ️ 未明显命中高点击句式，见下方改写建议")
    return max(score, 0), notes


def diagnose_body(body):
    score, notes = 25, []
    n = len(re.sub(r"\s+", "", body))
    if 300 <= n <= 800:
        notes.append(f"✅ 正文 {n} 字，信息量适中")
    elif n < 300:
        score -= 6
        notes.append(f"⚠️ 正文仅 {n} 字，偏单薄，加细节/过程/感受")
    else:
        score -= 4
        notes.append(f"⚠️ 正文 {n} 字偏长，注意分段，重点前置")
    paras = [p for p in body.split("\n") if p.strip()]
    if len(paras) >= 3:
        notes.append(f"✅ 分 {len(paras)} 段，阅读节奏好")
    else:
        score -= 4
        notes.append("⚠️ 几乎没分段，手机端阅读压力大，回车分段")
    em = len(EMOJI.findall(body))
    if em >= 3:
        notes.append(f"✅ emoji {em} 个，氛围感够")
    elif em > 0:
        notes.append(f"ℹ️ emoji {em} 个，可再加2-3个作段落分隔")
    else:
        score -= 3
        notes.append('⚠️ 零 emoji，小红书体感偏"严肃"，适当加')
    if INTERACT.search(body):
        notes.append("✅ 有互动引导（提问/喊话），利评论区")
    else:
        score -= 4
        notes.append("⚠️ 无互动引导，结尾加一句提问（如'你们试过吗'）")
    return max(score, 0), notes


def diagnose_tags(body, niche, tags_db):
    score, notes, rec = 15, [], []
    found = re.findall(r"#(\S+)", body)
    if 3 <= len(found) <= 8:
        notes.append(f"✅ 标签 {len(found)} 个，数量合适")
    elif len(found) < 3:
        score -= 6
        notes.append(f"⚠️ 只有 {len(found)} 个标签，曝光入口太少")
    else:
        score -= 3
        notes.append(f"⚠️ {len(found)} 个标签偏多，堆砌会被降权")
    if niche in tags_db:
        rec = [t for t in tags_db[niche] if t not in found][:8 - len(found)]
        if rec:
            notes.append(f"💡 推荐补标签：{' '.join('#' + t for t in rec)}")
    return max(score, 0), notes, found


def diagnose_risk(text, risks):
    score, notes = 20, []
    hit = [w for w in risks if w in text]
    if not hit:
        notes.append("✅ 未命中风险词库")
    else:
        score -= min(5 * len(hit), 18)
        notes.append(f"🚨 命中风险词 {len(hit)} 个：{'、'.join(hit)}")
        notes.append("   → 站外引流词（微信/私聊）易限流，改'主页简介有方式'；极限词改温和表达")
    return max(score, 0), notes


def pick_numbers(keywords):
    """选数字：优先取不带时间单位的数字（如 8斤 的 8），避免“30天→30个变化”"""
    joined = "".join(keywords)
    nums = re.findall(r"\d+", joined)
    for n in nums:
        if not re.search(n + r"\s*(天|周|月|年|小时|分钟)", joined):
            return n
    return nums[0] if nums else "3"


def pick_times(keywords):
    # 优先取像 "30天"/"2天" 这样数字+时间单位的词；含时间单位字的普通词
    #（如“成都周边”含“周”）不能当时间词，否则选题标题会把关键词当时间填。
    ts = [k for k in keywords
          if re.search(r"\d+\s*(天|周|月|年|小时|分钟)\s*$", k)]
    if ts:
        return ts[0]
    ts = [k for k in keywords if any(u in k for u in ("天", "周", "月", "年", "小时", "分钟"))]
    return ts[0] if ts else "30天"


def rewrite_titles(keywords, patterns):
    """用关键词填充句式槽位；填不上的槽位明确标出待填项"""
    kw = keywords[0] if keywords else "关键词"
    fill = {"{kw}": kw, "{n}": pick_numbers(keywords), "{时间}": pick_times(keywords)}
    out = []
    for p in patterns[:3]:
        t = p["template"]
        missing = []
        for slot in re.findall(r"\{[^}]+\}", t):
            if slot in fill:
                t = t.replace(slot, fill[slot])
            else:
                missing.append(slot.strip("{}"))
                t = t.replace(slot, "…")
        out.append((p["name"], t, missing, p["tip"], p["example"]))
    return out


STYLE_HOOKS = [
    ("数字钩", re.compile(r"\d+"), "{kw}{时间}实测：{n}个变化", "数字放前，具体感强"),
    ("时间钩", re.compile(r"(天|周|月|年|小时|分钟)"), "{时间}，我靠{kw}{改变}", "时间越短、改变越大，点击越高"),
    ("反问钩", re.compile(r"[？?]|吗\b|呢|怎么|为什么|如何"), "{kw}真的有用吗？{时间}亲测告诉你", "用反问制造认知冲突"),
    ("对比钩", re.compile(r"[vV][sS]|PK|对比|差别|差距|前后"), "{kw}前后对比：{时间}差别有多大", "对比结构天然带悬念"),
    ("悬念钩", re.compile(r"秘密|真相|避雷|内幕|不会告诉你|建议收藏"), "没人告诉你的{kw}真相，{n}条", "利他型标题，收藏率最高"),
    ("情绪钩", re.compile(r"[!！]|天啊|救命|竟然|离谱"), "{kw}{时间}亲测，效果分享", "情绪词慎用：过重会被判标题党"),
]


def analyze_style(ref_title):
    """拆解对标爆款标题的钩子结构：返回命中的钩子 + 分段数"""
    hits = []
    for name, pat, template, tip in STYLE_HOOKS:
        if pat.search(ref_title):
            hits.append({"name": name, "template": template, "tip": tip})
    segs = [s for s in re.split(r"[，。！？；、,]", ref_title) if s.strip()]
    return hits, len(segs)


def rewrite_with_style(keywords, style_hits):
    """用用户的关键词，套对标爆款的钩子结构（学结构，不抄文案）"""
    kw = keywords[0] if keywords else "关键词"
    fill = {"{kw}": kw, "{n}": pick_numbers(keywords),
            "{时间}": pick_times(keywords), "{改变}": "大变样"}
    out = []
    for h in style_hits[:3]:
        t = h["template"]
        missing = []
        for slot in re.findall(r"\{[^}]+\}", t):
            if slot in fill:
                t = t.replace(slot, fill[slot])
            else:
                missing.append(slot.strip("{}"))
                t = t.replace(slot, "…")
        out.append((h["name"], t, missing, h["tip"]))
    return out


def diagnose_cover(cover_path):
    """封面初检（PIL）：尺寸比例/文件大小。不计入总分，附加项。"""
    notes = []
    if not cover_path:
        return ["ℹ️ 未提供封面图，跳过封面检查"]
    try:
        from PIL import Image
        img = Image.open(cover_path)
        w, h = img.size
        ratio = w / h
        size_kb = Path(cover_path).stat().st_size / 1024
        if 0.70 <= ratio <= 0.80:
            notes.append(f"✅ 封面 {w}×{h}（{ratio:.2f}），3:4 竖版，信息流展示面积最大")
        elif 0.95 <= ratio <= 1.05:
            notes.append(f"ℹ️ 封面 {w}×{h}（{ratio:.2f}），1:1 方形；重要笔记建议改 3:4 竖版")
        else:
            notes.append(f"⚠️ 封面 {w}×{h}（{ratio:.2f}），非主流比例，信息流中可能被裁剪，建议 3:4")
        if size_kb > 5120:
            notes.append(f"⚠️ 文件 {size_kb:.0f}KB 偏大，压到 5MB 内上传更快")
        else:
            notes.append(f"✅ 文件 {size_kb:.0f}KB，大小合适")
        notes.append("ℹ️ 文字占比/配色情绪需人工或多模态大模型复核")
    except ImportError:
        notes.append("⚠️ 未装 Pillow，跳过封面检查（pip install pillow）")
    except Exception as e:
        notes.append(f"⚠️ 封面读取失败：{e}")
    return notes


def diagnose_note(title, body, niche, keywords, patterns=None, risks=None, tags_db=None, c_patterns=None, times=None):
    """一篇笔记的完整诊断。通用四维 + C 语言准确性（第 5 维，仅 C 领域计入）。
    含 C 硬错误时总分封顶 59。返回结构化结果（供 Agent 与测试共用）。
    times 为发布时间建议（data/post_times.yaml），不传时随规则库一起加载。"""
    if patterns is None or risks is None or tags_db is None:
        patterns, c_patterns, risks, tags_db, loaded_times = load_data()
        if times is None:
            times = loaded_times
    s1, n1 = diagnose_title(title, patterns)
    s2, n2 = diagnose_body(body)
    s3, n3, found = diagnose_tags(body, niche, tags_db)
    s4, n4 = diagnose_risk(title + "\n" + body, risks)
    total = s1 + s2 + s3 + s4
    dims = {"标题吸引力": s1, "正文质量": s2, "标签曝光": s3, "合规安全": s4}
    notes = {"标题": n1, "正文": n2, "标签": n3, "合规": n4}
    c_domain = is_c_domain(niche, body)
    if c_domain:
        s5, n5, hard = diagnose_c_accuracy(body)
        dims["C语言准确性"] = s5
        notes["C语言准确性"] = n5
        total += s5
        if hard:
            total = min(total, 59)
            notes["C语言准确性"].append("🚨 教学准确性是硬门槛：检测到硬错误，总分已封顶 59 分，须先改再发")
    rewrites = rewrite_titles(keywords, c_patterns if (c_domain and c_patterns) else patterns)
    return {
        "total": total,
        "max_score": 100 if c_domain else 90,
        "dims": dims,
        "notes": notes,
        "rewrites": [{"name": n, "title": t, "missing": m, "tip": tip, "example": ex}
                     for n, t, m, tip, ex in rewrites],
        "tags_found": found,
        "times": times,
        "verdict": ("🟢 优秀，直接发" if total >= 80 else
                    "🟡 可发，建议按下面优化" if total >= 60 else "🔴 先改再发"),
    }
