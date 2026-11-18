#!/usr/bin/env python3
"""Web 对话界面：单页应用 + JSON API（仅标准库，无额外依赖）。

路由：
  GET  /                单页应用（聊天 + 诊断表单 + 画像/任务 + 复盘）
  GET  /api/health      运行状态与 LLM 模式
  GET  /api/profile     画像、目标任务、分数趋势
  POST /api/chat        多轮对话
  POST /api/diagnose    诊断一篇笔记
  POST /api/review      发后复盘
默认端口 8081（避开本机 8080 的 ComfyUI 网关），可用 PORT 环境变量改。
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
from src.agent import Agent  # noqa: E402

AGENT = Agent(ROOT / "data")
NICHES = ["C语言", "美妆", "美食", "职场", "学习", "搞钱", "穿搭", "旅行", "家居", "母婴", "数码"]

HTML_PAGE = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>小红书内容运营智能体 xhs-agent</title>
<style>
body{font-family:sans-serif;max-width:860px;margin:0 auto;padding:16px;color:#222}
h1{font-size:20px}h1 small{color:#888;font-weight:400}
h2{font-size:16px;margin-top:28px}
h3{font-size:15px;margin:14px 0 6px}
.score{font-size:22px;font-weight:700}
.score.good{color:#16a34a}.score.mid{color:#d97706}.score.bad{color:#dc2626}
.dim{font-weight:700}
#log{border:1px solid #ddd;border-radius:8px;padding:12px;min-height:180px;white-space:pre-wrap}
#log .u{color:#0366d6}#log .a{color:#222}
input,textarea,select{width:100%;box-sizing:border-box;padding:8px;margin:4px 0;border:1px solid #ccc;border-radius:6px}
textarea{min-height:90px}
button{padding:8px 16px;background:#ff2442;color:#fff;border:0;border-radius:6px;cursor:pointer}
button:hover{opacity:.85}
.row{display:flex;gap:8px}.row>*{flex:1}
pre{background:#f6f6f6;padding:10px;border-radius:6px;white-space:pre-wrap;word-break:break-word}
.note{font-size:13px;color:#888}
</style></head><body>
<h1>📕 小红书内容运营智能体 <small id="mode">xhs-agent</small></h1>
<p class="note">小红书内容运营：多轮对话 + 记忆 + 目标拆解 + 发后复盘。风险词库为示例版，命中请人工复核；不承诺涨粉、不承诺爆款。</p>
<h2>对话</h2>
<div id="log">智能体：你好，我是你的小红书内容运营搭子。先定个目标试试，比如“下周发 3 篇成都周边旅行攻略笔记，冲一篇爆款”。</div>
<div class="row"><input id="msg" placeholder="说点什么：定目标 / 给我3个选题 / 再改一版 / 发完了…"><button id="send">发送</button></div>
<h2>诊断一篇笔记</h2>
<input id="d-title" placeholder="标题">
<textarea id="d-body" placeholder="正文（标签写在正文里，如 #减脂餐）"></textarea>
<div class="row"><select id="d-niche"></select><input id="d-kw" placeholder="关键词，逗号分隔"></div>
<button id="d-go">诊断</button>
<div id="d-out"></div>
<h2>画像与任务</h2>
<button id="p-load">刷新画像</button>
<pre id="p-out"></pre>
<h2>发后复盘</h2>
<div class="row"><input id="r-reads" placeholder="阅读"><input id="r-likes" placeholder="点赞"><input id="r-collects" placeholder="收藏"></div>
<button id="r-go">复盘</button>
<pre id="r-out"></pre>
<script>
const sid = "default";
const NL = String.fromCharCode(10);
const $ = id => document.getElementById(id);
const esc = s => s.replace(/&/g,"&amp;").replace(/</g,"&lt;");
async function post(path, body){
  const r = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)});
  return r.json();
}
async function send(){
  const t = $("msg").value.trim(); if(!t) return;
  $("msg").value = "";
  $("log").innerHTML += NL + "<span class='u'>你：</span>" + esc(t);
  const d = await post("/api/chat", {session_id: sid, text: t});
  $("log").innerHTML += NL + "<span class='a'>智能体：</span>" + esc(d.reply || d.error || "") + (d.mode_note ? NL + "<span class='a'>" + esc(d.mode_note) + "</span>" : "");
}
$("send").onclick = send;
$("msg").addEventListener("keydown", e => { if(e.key === "Enter") send(); });
$("d-niche").innerHTML = ["C语言","美妆","美食","职场","学习","搞钱","穿搭","旅行","家居","母婴","数码"].map(n => `<option>${n}</option>`).join("");
$("d-go").onclick = async () => {
  const d = await post("/api/diagnose", {session_id: sid, title: $("d-title").value, body: $("d-body").value,
    niche: $("d-niche").value, keywords: $("d-kw").value.split(/[,，、 ]+/).filter(Boolean)});
  if(d.error){ $("d-out").textContent = d.error; return; }
  const cls = d.total >= 80 ? "good" : d.total >= 60 ? "mid" : "bad";
  const dimMax = {"标题吸引力": 30, "正文质量": 25, "标签曝光": 15, "合规安全": 20};
  const dimNote = {"标题吸引力": "标题", "正文质量": "正文", "标签曝光": "标签", "合规安全": "合规"};
  let h = `<h3>综合评分：<span class="score ${cls}">${d.total} / ${d.max_score || 100}</span> ${esc(d.verdict)}</h3><ul>`;
  for(const dk of ["标题吸引力", "正文质量", "标签曝光", "合规安全"]){
    h += `<li><span class="dim">${dk}：${d.dims[dk]}/${dimMax[dk]}</span><ul>${d.notes[dimNote[dk]].map(n => `<li>${esc(n)}</li>`).join("")}</ul></li>`;
  }
  if(d.dims["C语言准确性"] !== undefined){
    h += `<li><span class="dim">C语言准确性：${d.dims["C语言准确性"]}/10</span><ul>${d.notes["C语言准确性"].map(n => `<li>${esc(n)}</li>`).join("")}</ul></li>`;
  }
  h += "</ul>";
  h += "<h3>标题改写建议</h3><ul>" + d.rewrites.map(w =>
    `<li><b>${esc(w.name)}：</b>${esc(w.title)}${w.missing && w.missing.length ? `（缺：${esc(w.missing.join("、"))}，补上对应关键词）` : ""}<br><span class="note">${esc(w.tip)} 例：${esc(w.example)}</span></li>`).join("") + "</ul>";
  if(d.times){
    h += "<h3>发布时间建议</h3><ul>"
      + d.times.general.map(t => `<li>${esc(t.time)}：${esc(t.note)}</li>`).join("")
      + d.times.weekend.map(t => `<li>${esc(t.time)}：${esc(t.note)}</li>`).join("")
      + `<li>${esc(d.times.tip)}</li></ul>`;
  }
  h += '<p class="note">风险词库是示例版，命中请人工复核。</p>';
  $("d-out").innerHTML = h;
};
$("p-load").onclick = async () => {
  const d = await fetch("/api/profile?session_id=" + sid).then(r => r.json());
  const lines = [d.summary, "", "【目标任务】"];
  (d.goal ? d.goal.tasks : []).forEach(t => lines.push(`${t.status === "done" ? "☑" : "□"} ${t.title}`));
  lines.push("", "【历史分数】" + (d.notes || []).map(n => `${n.title}:${n.score}`).join(" | "));
  $("p-out").textContent = lines.join(NL);
};
$("r-go").onclick = async () => {
  const d = await post("/api/review", {session_id: sid,
    reads: parseInt($("r-reads").value || "0"), likes: parseInt($("r-likes").value || "0"),
    collects: parseInt($("r-collects").value || "0")});
  $("r-out").textContent = d.error || `《${d.note.title}》预测 ${d.predicted} 分，互动率 ${(d.engagement_rate*100).toFixed(1)}%，${d.verdict}。` + NL + d.lesson;
};
fetch("/api/health").then(r => r.json()).then(d => { $("mode").textContent = "xhs-agent · " + (d.mode === "pangu" ? "盘古模式" : "模板模式"); });
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == "/api/health":
            self._json({"ok": True, "mode": AGENT.llm.mode})
        elif parsed.path == "/api/profile":
            q = parse_qs(parsed.query)
            sid = q.get("session_id", ["default"])[0]
            session = AGENT.store.load_session(sid)
            profile = AGENT.store.load_profile(sid)
            self._json({"summary": AGENT.profile_summary(profile),
                        "goal": session.get("goal"),
                        "notes": profile.get("notes", []),
                        "learnings": profile.get("learnings", [])})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self._read_json()
        except Exception:
            self._json({"error": "请求体不是合法 JSON"}, 400)
            return
        sid = data.get("session_id") or "default"
        try:
            if parsed.path == "/api/chat":
                self._json(AGENT.handle(sid, data.get("text", "")))
            elif parsed.path == "/api/diagnose":
                title = (data.get("title") or "").strip()
                body = (data.get("body") or "").strip()
                if not title or not body:
                    self._json({"error": "标题与正文都要填。"})
                    return
                niche = data.get("niche") or "C语言"
                kws = [k for k in (data.get("keywords") or []) if k]
                self._json(AGENT.diagnose(sid, title, body, niche, kws))
            elif parsed.path == "/api/review":
                self._json(AGENT.review(sid, int(data.get("reads", 0)),
                                        int(data.get("likes", 0)),
                                        int(data.get("collects", 0))))
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:
            self._json({"error": f"服务异常：{e}"}, 500)


def main():
    port = int(os.environ.get("PORT", "8081"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"xhs-agent listening on 0.0.0.0:{port} (mode={AGENT.llm.mode})")
    server.serve_forever()


if __name__ == "__main__":
    main()
