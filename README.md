# 小红书内容运营智能体 xhs-agent

华为开发者大赛·智能体创新赛（西南赛区 · OPC 组）参赛作品。
创作者的 7 天内容运营搭子：多轮对话 + 账号画像记忆 + 目标拆解 + 诊断改写 + 发后复盘。

- 代码：GitHub 公开仓 https://github.com/luochan1028/xhs-agent（免登录克隆或下载 zip）
- 在线 Demo：http://119.3.227.184:8081（部署在华为云，模板模式，零成本）
- 演示视频：v9，4:18（规范建议 3 分钟以内，非强制）

## 1. 环境依赖说明

- **Python 3.7 以上**。实测：本地 Python 3.12.3；华为云 CodeArts 构建环境 Python 3.7.4。
- **唯一第三方依赖：PyYAML**（`requirements.txt` 只有这一行），用于解析 `data/*.yaml` 规则库。
- Web 界面与 JSON API **只用 Python 标准库**（`http.server`），不需要 gcc、不需要 root。
- 默认监听 `0.0.0.0:8081`，`PORT` 环境变量可改端口。
- 画像与会话存在 `data/profiles/` 与 `data/sessions/` 的 JSON 文件里，不需要数据库。

## 2. 一键安装与运行

```bash
./install.sh            # 建 .venv、装 PyYAML、跑 13 项测试（--with-cover 再装 Pillow）
.venv/bin/python run.py # 浏览器打开 http://localhost:8081
```

`install.sh` 做五件事：检查 Python ≥ 3.7、创建虚拟环境 `.venv`、装 PyYAML、
可选装 Pillow（`--with-cover`，启用封面尺寸检查）、跑通 13 项测试。
Windows 用 `install.ps1`（同样流程）。注意：脚本退出后 venv 不会留在当前 shell 里，
启动要用 `.venv/bin/python run.py`（或先 `source .venv/bin/activate` 再 `python run.py`）。
不跑脚本时手动安装也一样：

```bash
pip install -r requirements.txt
python3 -m unittest discover -s tests
python3 run.py
```

健康检查：`curl http://localhost:8081/api/health` 应返回 `{"ok": true, "mode": "template"}`。

## 3. 部署运行步骤

### 本地运行

见第 2 节：`./install.sh` 后 `python3 run.py`，浏览器打开 http://localhost:8081。

### 华为云 CodeArts 部署（本作品线上 Demo 实际采用的方式）

1. **代码托管**：CodeArts 项目「小红书内容运营智能体」→ 代码仓 `xhs-agent`。
2. **编译构建**：构建任务 `xhs-agent-build`，产物为 `xhs-agent.zip`。
3. **部署**：部署应用 `xhs-agent-deploy` → 主机集群 `c-lab-openeuler`（ECS 119.3.227.184），
   下载软件包、解压到 `/root/xhs-agent`，`setsid` + `nohup` 启动 `run.py`，监听 8081 端口。
   安全组已放行 TCP 8081。
4. **验证**：部署健康检查对 `/` 与 `/api/health` 均返回 200；
   诊断实测：旅行攻略 90/90、C 语言指针教学笔记 100/100、减脂餐 45/90。
5. 完整分步说明见提交包 `codearts_proof/` 里的《部署手册-代码托管到上线全流程.pdf》。

### 手动部署到自有服务器

上传 `xhs-agent.zip` → 解压到 `/root/xhs-agent` → `setsid nohup python3 run.py &` →
检查 `curl http://<服务器IP>:8081/api/health` 返回 200。

## 4. 开源组件说明

| 组件 | 版本 / 来源 | 许可证 | 用途 |
|---|---|---|---|
| Python 3 | 3.7 以上 | PSF License | 运行环境 |
| PyYAML | `requirements.txt` | MIT License | 解析 `data/*.yaml` 规则库 |
| 本作品 | ©2026 罗婵 | MIT License（见 `LICENSE`） | 全部自研代码 |

- 除 PyYAML 外**无第三方依赖**；无小红书官方 API，发布数据靠人工回填。
- 规则库（标题句式、风险词、标签、发布时间）为作者自研，与 Skill 版 `xhs-optimizer` 同源，
  在本作品中作确定性校验层。

## 5. 码道（华为云 CodeArts）应用总结

- **代码托管**：项目「小红书内容运营智能体」（ID `7670a1ebf25c41e4bd661d8981e0c882`，华北-北京四），
  代码仓 `xhs-agent`（ID `3115699`）；2026-11-18 同步后 32 个文件，与本包 `project/` 一致。
- **编译构建**：构建任务 `xhs-agent-build`（ID `5d382ca1721140bb855c8ad0b1a66cf2`）；
  最新构建 `#20261118.1` 于 2026-11-18 14:06 成功；
  产物路径 `/xhs-agent/20261117.1/xhs-agent.zip`（产物版本号固定，不随构建号变化，每次新构建覆盖上传到同一路径）。
- **部署**：部署应用 `xhs-agent-deploy`（ID `3e8f8ea644784de78b6cd734f1a1bfb5`）；
  最新部署记录 `#7` 于 2026-11-18 14:09 成功（42 秒），新进程 14:10 启动，
  健康检查 `/` 与 `/api/health` 均返回 200。
- **评审对齐**：开发过程使用码道（代码托管 + 编译构建 + 部署）并提交使用证明，
  对应评分「码道应用深度 25 分」；部署地点无强制要求，本作品部署在华为云 ECS。
- 详细过程记录与截图见提交包 `codearts_proof/`（码道使用证明 + 部署手册 + 6 张截图）。

## 6. 功能一览

- **多轮对话**：定目标、选题、撰写辅导、诊断、改写、排期、复盘，一路聊下来不用重复交代背景。
- **账号画像记忆**：垂类、人设、历史笔记与分数趋势存在本地，下次打开还记得。
- **目标拆解**：一个 7 天目标拆成 16 项任务（3 篇 × 5 步 + 1 次复盘），带进度跟踪。
- **诊断与改写**：四维评分（标题 30 / 正文 25 / 标签 15 / 合规 20，C 语言笔记另加准确性 10 分），
  给出改写标题与发布时间建议。
- **发后复盘**：填入真实阅读、点赞、收藏，算互动率并判定是否超预期。

## 7. 与 Skill 版的区别

| 维度 | Skill 版 xhs-optimizer（已交 Skill 赛） | 本作品 xhs-agent |
|---|---|---|
| 产品形态 | 命令行工具，单次调用 | 对话式 Web 应用，多轮会话 |
| 核心能力 | 单篇笔记发前诊断 | 选题→撰写辅导→诊断→改写→排期→复盘，全流程 |
| 记忆 | 无状态 | 账号画像：垂类、人设、历史笔记与分数趋势 |
| 引擎 | 纯规则（盘古位预留未接） | 模板模式为默认（确定性模板回复）；盘古大模型为可选增强，Key 配好才启用，失败回落并明示；规则引擎为底座校验层 |
| 目标管理 | 无 | 目标拆解 + 排期 + 进度跟踪 |

复用的只是同一作者的底层规则库（标题句式、风险词、标签、发布时间），
作确定性校验层；其余能力均为新开发，代码、界面、文档、Demo 独立成仓。

## 8. 测试

```bash
python3 -m unittest discover -s tests -v
```

12 项测试全部通过。回归用例：Skill 版实测 45 分样本（标题 23 / 正文 8 / 标签 9 / 合规 5）；
全流程冒烟：定目标 → 选题 → 诊断 → 改写 → 复盘 → 体检。
实测分数（2026-11-18 线上 Demo 复核）：旅行攻略 90/90、C 语言指针教学笔记 100/100、减脂餐 45/90。

## 9. 目录结构

```
xhs-agent/
  run.py            入口（默认 0.0.0.0:8081，PORT 环境变量可改）
  install.sh        一键安装脚本（Linux / macOS，建 .venv + 跑测试）
  install.ps1       一键安装脚本（Windows PowerShell，同样流程）
  requirements.txt  仅 pyyaml
  LICENSE           MIT License
  data/             规则库（与 Skill 版同源）+ 样例笔记 + 运行期画像/会话（JSON）
  src/
    rules.py        四维评分 + 标题改写 + 封面初检（复用 Skill 版口径）
    llm.py          LLM 层：模板模式（默认）/ 盘古模式（Key + 已核对 endpoint）
    session.py      会话与画像存储（JSON）
    planner.py      目标拆解与任务跟踪
    topics.py       选题生成（钩子结构 + 大纲脚手架）
    review.py       发后复盘（预测分 vs 真实数据）
    agent.py        意图路由 + Agent 主体
    app.py          Web 界面 + JSON API（仅标准库）
  tests/            回归 + 全流程冒烟
```

## 10. 诚实口径

- 默认**模板模式**：确定性模板回复，零成本、离线可跑，界面与回复中明确标注，
  不冒充大模型能力。盘古模式仅当 `PANGU_API_KEY` 与 `PANGU_API_BASE`
  同时给出时启用，endpoint 与模型名须按华为云盘古 MaaS 官方文档核对后填入；
  调用失败自动回落到模板模式并明示。
- 风险词库为示例版，命中请人工复核；封面只做尺寸比例初检，不评配色情绪。
- 无小红书官方 API，发布数据靠人工回填；不承诺涨粉、不承诺爆款。
- 意图识别为 v1 关键词启发式，非语义理解。

## 11. 赛制对齐（官方提交规范 2026-11-18 核实）

- 西南赛区 OPC 组，1 人 + AI 即可成队；报名与交作品均 2026-11-24 23:59:59 截止。
- 作品开发过程须用华为云码道并提交使用证明（25 分），部署地点无强制要求；不得是纯 AI 聊天对话类作品。
- 提交包 5 个文件夹：`ppt/`、`project/`、`video/`、`codearts_proof/`、`readme/`，≤ 200MB。
- `ppt/` 须含场景背景、功能架构、核心亮点、码道应用说明；
  `codearts_proof/` 须含核心功能开发的 AI 交互对话与 Prompt 截图、代码生成 / 重构 / 排错过程记录；
  `readme/` 须含环境依赖说明与一键安装脚本、部署运行步骤、开源组件说明、码道应用总结；
  `video/` 建议 3 分钟以内（非强制），本作品 v9 为 4:18。
- 作品提交后可多次修改提交，每队每天最多 1 次；以最后一次提交为准。
