#!/usr/bin/env python3
"""会话与画像存储：JSON 文件，多轮上下文 + 账号画像。

目录结构（data_root 下）：
  sessions/<session_id>.json  多轮消息、当前目标、最近一次诊断
  profiles/<profile_id>.json  垂类、人设、历史笔记与分数趋势、目标、复盘结论
默认 session_id == profile_id == "default"（单创作者场景）。
"""
import json
from pathlib import Path


class Store:
    def __init__(self, data_root):
        self.root = Path(data_root)
        self.sessions_dir = self.root / "sessions"
        self.profiles_dir = self.root / "profiles"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    # ---- 会话 ----
    def load_session(self, session_id="default"):
        p = self.sessions_dir / f"{session_id}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"session_id": session_id, "messages": [], "goal": None,
                "last_note": None, "last_score": None, "last_dims": None}

    def save_session(self, session_id, data):
        p = self.sessions_dir / f"{session_id}.json"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 画像 ----
    def load_profile(self, profile_id="default"):
        p = self.profiles_dir / f"{profile_id}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"profile_id": profile_id, "niche": "", "persona": "",
                "notes": [], "goals": [], "learnings": []}

    def save_profile(self, profile_id, data):
        p = self.profiles_dir / f"{profile_id}.json"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
