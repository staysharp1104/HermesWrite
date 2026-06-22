# Hermes Agent 项目架构分析

## 一、项目定位

Hermes 是一个**自进化 AI 代理（Self-Evolving AI Agent）**，核心价值在于内置学习闭环。它运行同一套 Agent 核心引擎，横跨 **CLI、消息网关（20+ 平台）、TUI（终端 UI）、Electron 桌面应用、OpenAI 兼容 API、ACP 编辑器集成** 六种前端形态。具备跨会话记忆、自主技能创建/改进、子代理委托、定时任务调度、终端和浏览器控制等能力。

---

## 二、技术栈

| 层面       | 技术                                                         |
|------------|--------------------------------------------------------------|
| **语言**   | Python 3.11+（<3.14）, Node.js 22 LTS, TypeScript           |
| **包管理** | `uv`（Python）, `npm`（Node.js）                             |
| **AI 框架**| OpenAI SDK（兼容协议）, Anthropic, Google Gemini, Bedrock, Azure 等多适配器 |
| **CLI**    | `prompt_toolkit` + `rich` + 皮肤引擎（skin_engine.py）       |
| **TUI**    | Ink（React for Terminal）+ TypeScript + tui_gateway JSON-RPC  |
| **桌面**   | Electron + React 19 + nanostore                              |
| **Web**    | FastAPI + uvicorn + Docusaurus（文档站）                      |
| **存储**   | SQLite（WAL 模式 + FTS5 全文搜索）                            |
| **容器化** | Debian 13 + s6-overlay（PID 1）+ 多阶段构建                   |
| **测试**   | pytest（~17k 测试 / ~900 文件）                               |
| **定时任务**| `croniter` 内置调度                                          |

---

## 三、系统架构总览

```
┌─────────────────────────── 前端接入层 ───────────────────────────┐
│                                                                   │
│  CLI          TUI           Electron       Web Dashboard          │
│  cli.py       ui-tui/       apps/desktop/  web/                   │
│  prompt_      tui_gateway/                 hermes_cli/            │
│  toolkit                                    web_server.py         │
│                                                                   │
│  消息网关           OpenAI API        ACP 编辑器集成              │
│  gateway/run.py     platforms/         acp_adapter/               │
│                     api_server.py                                 │
└──────────────────────────┬────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────┐
│                      核心引擎层                                    │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ AIAgent          │  │ 对话循环      │  │ 系统提示词组装      │   │
│  │ run_agent.py     │──│ conversation_ │  │ system_prompt.py   │   │
│  │ (~5.5k LOC)      │  │ loop.py       │  │ prompt_builder.py  │   │
│  └────────┬─────────┘  └──────────────┘  └────────────────────┘   │
│           │                                                       │
│  ┌────────▼─────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ 工具编排          │  │ 工具注册中心  │  │ 工具集定义          │   │
│  │ model_tools.py   │──│ tools/        │  │ toolsets.py        │   │
│  │ (~1.2k LOC)      │  │ registry.py   │  │ (~907 LOC)         │   │
│  └────────┬─────────┘  └──────┬───────┘  └────────────────────┘   │
└───────────┼────────────────────┼──────────────────────────────────┘
            │                    │
┌───────────▼────────────────────▼──────────────────────────────────┐
│                       能力层                                      │
│                                                                   │
│  内置工具 40+         终端后端 6种       浏览器控制                │
│  tools/*.py           tools/environments/ tools/browser_tool.py   │
│                       ├── local.py       tools/browser_supervisor  │
│                       ├── docker.py                               │
│                       ├── ssh.py         MCP 集成                 │
│                       ├── modal.py       tools/mcp_tool.py        │
│                       ├── daytona.py                              │
│                       └── singularity.py                          │
│                                                                   │
│  记忆系统              技能系统           插件系统                 │
│  agent/memory_        skills/            plugins/                 │
│  manager.py           optional-skills/   ├── memory/              │
│  tools/memory_tool.py ~/.hermes/skills/  ├── model-providers/     │
│  tools/session_                          ├── context_engine/      │
│  search_tool.py                          ├── kanban/              │
│  hermes_state.py                         ├── image_gen/           │
│  (SQLite + FTS5)                         ├── video_gen/           │
│                                          ├── browser/             │
│                                          ├── observability/       │
│                                          └── ... 更多             │
│                                                                   │
│  定时任务              子代理委托         代码执行                 │
│  cron/scheduler.py    tools/delegate_    tools/code_execution_    │
│  cron/jobs.py         tool.py            tool.py                  │
│  tools/cronjob_       (~3.2k LOC)        (~1.8k LOC)             │
│  tools.py                                                       │
└───────────────────────────────────────────────────────────────────┘
            │
┌───────────▼───────────────────────────────────────────────────────┐
│                     消息网关平台适配器（20+）                       │
│  gateway/platforms/base.py (ABC ~5k LOC)                          │
│                                                                   │
│  国际: Telegram | Discord | Slack | WhatsApp | Signal | Matrix    │
│        Mattermost | Email | SMS | BlueBubbles(iMessage)           │
│  国内: 微信(Weixin) | 企业微信(WeCom) | 飞书(Feishu) | 钉钉      │
│        (DingTalk) | QQ Bot | 元宝(Yuanbao)                        │
│  通用: Webhook | API Server (OpenAI 兼容)                          │
│  微软: MS Graph (Teams)                                           │
└───────────────────────────────────────────────────────────────────┘
```

---

## 四、核心模块详解

### 4.1 入口与前端接入

| 模块 | 文件/目录 | 规模 | 职责 |
|------|-----------|------|------|
| CLI 交互终端 | `cli.py` | ~15k LOC | 基于 `prompt_toolkit` 的 REPL 交互，命令补全、皮肤引擎、Slash 命令调度 |
| TUI 终端 UI | `ui-tui/` + `tui_gateway/` | React+TS | Ink(React) 渲染前端，Python JSON-RPC 后端，完整替代 CLI |
| Electron 桌面 | `apps/desktop/` | React+TS | 独立聊天表面，走 `tui_gateway` JSON-RPC 后端 |
| Web Dashboard | `web/` + `hermes_cli/web_server.py` | FastAPI | Web 界面，嵌入 `hermes --tui` 的 PTY |
| 消息网关 | `gateway/run.py` | ~18k LOC | 长驻守护进程，同时接入 20+ 消息平台，会话管理、Agent 缓存、Slash 命令 |
| ACP 适配器 | `acp_adapter/` | ~12 文件 | VS Code / Zed / JetBrains 编辑器集成协议 |
| OpenAI API | `gateway/platforms/api_server.py` | ~4.5k LOC | 提供 OpenAI 兼容 HTTP API |
| 批量运行器 | `batch_runner.py` | ~1.3k LOC | 并行批处理，多进程，支持断点续跑 |

### 4.2 核心引擎

#### AIAgent (`run_agent.py` ~5.5k LOC)

核心 `AIAgent` 类，约 60 个构造参数。关键接口：

```python
class AIAgent:
    def chat(self, message: str) -> str
        """简单接口 — 返回最终响应字符串"""

    def run_conversation(self, user_message, system_message=None,
                         conversation_history=None, task_id=None) -> dict
        """完整接口 — 返回 dict(final_response + messages)"""
```

**对话循环**（同步执行）：
1. 构建 system prompt（stable → context → volatile 三层拼接）
2. 进入 `while` 循环（最大 `max_iterations` 次，默认 90）
3. 调用 LLM `chat.completions.create(model, messages, tools)`
4. 若有 `tool_calls` → 分发执行 → 结果追加到 messages → 继续循环
5. 若无 → 返回最终文本响应

**关键特性**：
- 中断检查（`_interrupt_requested`）
- 迭代预算追踪（`iteration_budget`）
- 单轮宽限调用（`_budget_grace_call`）
- 推理内容存储到 `assistant_msg["reasoning"]`

#### 工具编排 (`model_tools.py` ~1.2k LOC)

薄编排层，触发工具发现并提供公共 API：

```python
get_tool_definitions(enabled_toolsets, disabled_toolsets, quiet_mode) -> list
handle_function_call(function_name, function_args, task_id, user_task) -> str
get_all_tool_names() -> list
check_tool_availability(quiet) -> tuple
```

**异步桥接**：持久化事件循环（避免 asyncio.run() 的创建/关闭循环问题），支持 CLI 线程、Worker 线程、Gateway 异步栈三种场景。

#### 工具注册中心 (`tools/registry.py` ~590 LOC)

单例模式，每个工具文件在导入时自注册：

```python
class ToolRegistry:
    def register(name, toolset, schema, handler, check_fn, ...)
    def deregister(name)
    def get_definitions(tool_names, quiet) -> List[dict]  # OpenAI 格式
    def dispatch(name, args, **kwargs) -> str              # 执行工具
    def get_all_tool_names() -> List[str]
    def is_toolset_available(toolset) -> bool
```

**ToolEntry 元数据**：
```python
class ToolEntry:
    name, toolset, schema, handler, check_fn,
    requires_env, is_async, description, emoji,
    max_result_size_chars, dynamic_schema_overrides
```

**check_fn TTL 缓存**：外部状态探测（Docker 守护进程、Modal SDK、playwright 等）结果缓存 ~30 秒，避免频繁探测。

**文件依赖链**（无循环导入）：
```
tools/registry.py  (无依赖 — 被所有工具文件导入)
       ↑
tools/*.py  (每个文件在模块级别调用 registry.register())
       ↑
model_tools.py  (导入 tools/registry + 触发工具发现)
       ↑
run_agent.py, cli.py, batch_runner.py
```

#### 工具集定义 (`toolsets.py` ~907 LOC)

工具集的组合解析系统：

```python
# 基础工具集
"web", "terminal", "file", "browser", "memory", "skills",
"vision", "image_gen", "video_gen", "tts", "todo",
"session_search", "clarify", "code_execution", "delegation",
"cronjob", "homeassistant", "kanban", "computer_use",
"discord", "discord_admin", "spotify", "feishu_doc", "feishu_drive"

# 场景工具集
"coding", "debugging", "safe"

# 平台工具集
"hermes-cli", "hermes-telegram", "hermes-discord", "hermes-whatsapp",
"hermes-slack", "hermes-signal", "hermes-email", "hermes-sms",
"hermes-matrix", "hermes-mattermost", "hermes-bluebubbles",
"hermes-dingtalk", "hermes-feishu", "hermes-weixin", "hermes-wecom",
"hermes-qqbot", "hermes-yuanbao", "hermes-webhook", "hermes-gateway",
"hermes-acp", "hermes-api-server"
```

支持递归组合（`includes` 字段）、环检测、运行时动态创建自定义工具集。

---

### 4.3 内置工具清单（40+ 工具）

按功能域分类：

| 功能域 | 工具名 | 实现文件 | 规模 |
|--------|--------|----------|------|
| **Web 搜索** | `web_search`, `web_extract` | `tools/web_tools.py` | ~1.4k LOC |
| **X/Twitter** | `x_search` | `tools/x_search_tool.py` | ~525 LOC |
| **终端执行** | `terminal`, `process` | `tools/terminal_tool.py` | ~2.7k LOC |
| **进程管理** | — | `tools/process_registry.py` | ~1.9k LOC |
| **文件读写** | `read_file`, `write_file` | `tools/file_tools.py` | ~1.7k LOC |
| **文件操作** | `patch`, `search_files` | `tools/file_operations.py` | ~2.4k LOC |
| **模糊匹配** | — | `tools/fuzzy_match.py` | ~860 LOC |
| **浏览器** | `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`, `browser_snapshot`, `browser_back`, `browser_press`, `browser_get_images`, `browser_vision`, `browser_console`, `browser_cdp`, `browser_dialog` | `tools/browser_tool.py` | ~4k LOC |
| **浏览器管控** | — | `tools/browser_supervisor.py` | ~1.5k LOC |
| **浏览器安全** | — | `tools/browser_camofox.py` | ~794 LOC |
| **视觉分析** | `vision_analyze` | `tools/vision_tools.py` | ~1.6k LOC |
| **图片生成** | `image_generate` | `tools/image_generation_tool.py` | ~1.6k LOC |
| **视频生成** | `video_generate` | `tools/video_generation_tool.py` | ~562 LOC |
| **TTS 语音** | `text_to_speech` | `tools/tts_tool.py` | ~2.8k LOC |
| **语音模式** | — | `tools/voice_mode.py` | ~1.2k LOC |
| **转录** | — | `tools/transcription_tools.py` | ~1.8k LOC |
| **记忆** | `memory` | `tools/memory_tool.py` | ~1k LOC |
| **会话搜索** | `session_search` | `tools/session_search_tool.py` | ~797 LOC |
| **技能** | `skills_list`, `skill_view`, `skill_manage` | `tools/skills_tool.py` + `tools/skill_manager_tool.py` | ~1.6k + ~1.2k LOC |
| **技能中心** | — | `tools/skills_hub.py` | ~3.9k LOC |
| **任务跟踪** | `todo` | `tools/todo_tool.py` | ~308 LOC |
| **澄清提问** | `clarify` | `tools/clarify_tool.py` | ~191 LOC |
| **子代理委托** | `delegate_task` | `tools/delegate_tool.py` | ~3.2k LOC |
| **代码执行** | `execute_code` | `tools/code_execution_tool.py` | ~1.8k LOC |
| **定时任务** | `cronjob` | `tools/cronjob_tools.py` | ~973 LOC |
| **智能家居** | `ha_list_entities`, `ha_get_state`, `ha_list_services`, `ha_call_service` | `tools/homeassistant_tool.py` | ~513 LOC |
| **看板协调** | `kanban_show`, `kanban_list`, `kanban_complete`, `kanban_block`, `kanban_heartbeat`, `kanban_comment`, `kanban_create`, `kanban_link`, `kanban_unblock` | `tools/kanban_tools.py` | ~1.5k LOC |
| **桌面控制** | `computer_use` | `tools/computer_use/` | ~43+780+213+823+204 LOC |
| **Discord** | `discord`, `discord_admin` | `tools/discord_tool.py` | ~959 LOC |
| **飞书** | `feishu_doc_read`, `feishu_drive_*` | `tools/feishu_doc_tool.py` + `tools/feishu_drive_tool.py` | ~138+431 LOC |
| **元宝** | `yb_query_group_info`, `yb_send_dm`, `yb_*_sticker` | `tools/yuanbao_tools.py` | ~737 LOC |
| **混合推理** | `mixture_of_agents` | `tools/mixture_of_agents_tool.py` | ~542 LOC |
| **消息发送** | — | `tools/send_message_tool.py` | ~1.7k LOC |
| **MCP** | 动态 MCP 工具 | `tools/mcp_tool.py` | ~4.7k LOC |
| **安全审批** | — | `tools/approval.py` | ~2k LOC |
| **安全扫描** | — | `tools/tirith_security.py` | ~822 LOC |

### 4.4 终端执行后端（6 种）

通过 `tools/environments/base.py` (~895 LOC) 定义 ABC：

| 后端 | 实现文件 | 规模 | 场景 |
|------|----------|------|------|
| **Local** | `tools/environments/local.py` | ~747 LOC | 本地主机直接执行 |
| **Docker** | `tools/environments/docker.py` | ~1.3k LOC | Docker 容器隔离执行 |
| **SSH** | `tools/environments/ssh.py` | ~375 LOC | 远程 SSH 主机执行 |
| **Modal** | `tools/environments/modal.py` | ~478 LOC | Modal Serverless GPU |
| **Daytona** | `tools/environments/daytona.py` | ~270 LOC | Daytona 开发环境 |
| **Singularity** | `tools/environments/singularity.py` | ~265 LOC | HPC Singularity 容器 |

辅助模块：`file_sync.py`（文件同步）, `modal_utils.py`（Modal 工具函数）

### 4.5 消息网关平台适配器

通过 `gateway/platforms/base.py` (~5k LOC) 定义 `PlatformAdapter(ABC)`。

每个适配器实现：
- `connect()` / `disconnect()` — 生命周期管理
- `send_message()` — 消息发送（支持富媒体、线程回复）
- `handle_incoming()` — 入站消息处理

**已实现 20+ 平台：**

| 分类 | 平台 | 主要实现文件 |
|------|------|-------------|
| 国际主流 | Telegram | `gateway/platforms/` (多文件) |
| | Discord | `gateway/platforms/` |
| | Slack | `gateway/platforms/` |
| | WhatsApp Cloud | `gateway/platforms/whatsapp_cloud.py` (~2k LOC) |
| | Signal | `gateway/platforms/signal.py` (~1.7k LOC) |
| | Matrix | `gateway/platforms/` |
| | Mattermost | `gateway/platforms/` |
| | Email (IMAP/SMTP) | `gateway/platforms/` |
| | SMS (Twilio) | `gateway/platforms/` |
| 国内平台 | 微信 (Weixin) | `gateway/platforms/weixin.py` (~2.4k LOC) |
| | 企业微信 (WeCom) | `gateway/platforms/` |
| | 飞书 (Feishu/Lark) | `gateway/platforms/` |
| | 钉钉 (DingTalk) | `gateway/platforms/` |
| | QQ Bot | `gateway/platforms/` |
| | 元宝 (Yuanbao) | `gateway/platforms/yuanbao.py` (~5.4k LOC) |
| Apple | BlueBubbles (iMessage) | `gateway/platforms/bluebubbles.py` (~1k LOC) |
| 通用 | Webhook | `gateway/platforms/webhook.py` (~1k LOC) |
| | API Server | `gateway/platforms/api_server.py` (~4.5k LOC) |
| 微软 | MS Graph (Teams) | `gateway/platforms/msgraph_webhook.py` |

网关核心模块：

| 模块 | 职责 |
|------|------|
| `gateway/run.py` | 网关主循环、Agent 缓存、会话调度、Slash 命令 |
| `gateway/session.py` | 网关会话管理 |
| `gateway/stream_dispatch.py` | 流式响应分发 |
| `gateway/stream_consumer.py` | 流式消费 |
| `gateway/stream_events.py` | 流式事件 |
| `gateway/slash_commands.py` | Slash 命令处理 |
| `gateway/delivery.py` | 消息投递 |
| `gateway/hooks.py` | 钩子系统 |
| `gateway/config.py` | 网关配置 |
| `gateway/platform_registry.py` | 平台注册中心 |
| `gateway/pairing.py` | 设备配对 |
| `gateway/mirror.py` | 消息镜像 |
| `gateway/restart.py` | 网关热重启 |

### 4.6 记忆系统

三层记忆架构：

| 层级 | 机制 | 实现 | 说明 |
|------|------|------|------|
| Agent 自管理记忆 | `memory` 工具 | `tools/memory_tool.py` | 模型自主读写持久笔记 |
| 会话搜索 | FTS5 全文索引 SQLite | `tools/session_search_tool.py` + `hermes_state.py` | 跨会话检索 |
| 外部记忆提供商 | 插件化 MemoryProvider ABC | `plugins/memory/` + `agent/memory_manager.py` | 一次只能激活一个 |

**MemoryManager 编排接口：**
```python
self._memory_manager.build_system_prompt()      # 注入系统提示词
self._memory_manager.prefetch_all(user_message)  # 每轮预取上下文
self._memory_manager.sync_all(msg, response)     # 轮后同步
self._memory_manager.queue_prefetch_all(msg)     # 异步队列预取
self._memory_manager.shutdown_all()              # 关闭时排空
```

### 4.7 技能系统（Skills）

技能是 Markdown 文件（SKILL.md），教 Agent 如何执行特定任务。支持自动创建和改进。

| 分类 | 目录 | 内容 |
|------|------|------|
| 内置技能 (17 组) | `skills/` | apple, autonomous-ai-agents, creative, data-science, dogfood, email, github, index-cache, media, mlops, note-taking, productivity, research, smart-home, social-media, software-development, yuanbao |
| 可选技能 (19 组) | `optional-skills/` | 更重/小众的技能，默认不激活 |
| 用户技能 | `~/.hermes/skills/` | 运行时动态加载和创建 |

**关键设计**：技能通过 `agent/skill_commands.py` 扫描并作为 **user message**（而非 system prompt）注入，以保护 prompt cache 不被破坏。

相关模块：
- `tools/skills_tool.py` — 技能列表/查看
- `tools/skill_manager_tool.py` — 技能创建/编辑/删除
- `tools/skills_hub.py` — 技能中心（发现/安装/发布）
- `tools/skills_sync.py` — 技能同步
- `tools/skills_guard.py` — 技能安全扫描
- `tools/skill_usage.py` — 技能使用追踪
- `agent/skill_utils.py` — 技能解析工具
- `agent/skill_bundles.py` — 技能打包
- `agent/skill_commands.py` — 技能命令注入
- `agent/skill_preprocessing.py` — 技能预处理

### 4.8 插件系统

| 插件 | 目录 | 职责 |
|------|------|------|
| 记忆提供商 | `plugins/memory/` | Honcho, Mem0, SuperMemory 等 |
| 模型提供商 | `plugins/model-providers/` | OpenRouter, Anthropic, GMI 等推理后端 |
| 上下文引擎 | `plugins/context_engine/` | 运行时上下文管理 |
| 看板调度 | `plugins/kanban/` | 多 Agent 协调的看板派发 + Worker |
| 图片生成 | `plugins/image_gen/` | 图片生成后端提供商 |
| 视频生成 | `plugins/video_gen/` | 视频生成后端 |
| 浏览器 | `plugins/browser/` | 浏览器驱动提供商 |
| 可观测性 | `plugins/observability/` | Metrics / Traces / Logs |
| 成就系统 | `plugins/hermes-achievements/` | 游戏化成就追踪 |
| 磁盘清理 | `plugins/disk-cleanup/` | 自动磁盘空间管理 |
| 安全指导 | `plugins/security-guidance/` | 安全建议注入 |
| Spotify | `plugins/spotify/` | Spotify 音乐控制 |
| Google Meet | `plugins/google_meet/` | Google Meet 会议集成 |
| Dashboard 认证 | `plugins/dashboard_auth/` | Web 面板认证 |
| Cron 扩展 | `plugins/cron/` | 定时任务调度扩展 |
| Web 扩展 | `plugins/web/` | Web 相关扩展 |
| Teams Pipeline | `plugins/teams_pipeline/` | Microsoft Teams 管道 |

**插件原则**：插件在独立目录，通过 ABC + Hooks 扩展，不修改核心文件。

### 4.9 系统提示词组装

三级结构，一次构建，整个会话复用（只有 context compression 才重建）：

| 层级 | 内容 |
|------|------|
| **Stable（稳定层）** | Agent 身份（SOUL.md 或 DEFAULT_AGENT_IDENTITY）、工具指导、计算机使用指导、Nous 订阅块、工具使用强制指导 + 模型特定操作指导、技能提示、环境提示、平台提示 |
| **Context（上下文层）** | 调用方提供的 system_message + AGENTS.md / .cursorrules / SOUL.md 等上下文文件 |
| **Volatile（易变层）** | 记忆快照、USER.md 用户画像、外部记忆提供商数据块、时间戳/会话/模型/提供商信息 |

实现入口：`agent/system_prompt.py` (~535 LOC) + `agent/prompt_builder.py` (~1.8k LOC)

**关键设计约束**：
- 提示词在会话内**字节级稳定**，保护上游 prompt cache
- 上下文文件注入前经过**威胁模式扫描**（prompt injection 检测，`tools/threat_patterns.py`）
- 技能作为 user message 注入，不污染 system prompt

### 4.10 数据存储

| 存储 | 实现 | 说明 |
|------|------|------|
| 会话数据库 | `hermes_state.py` (~5k LOC) | SQLite WAL 模式 + FTS5 全文搜索，支持会话分支、压缩续接、级联删除 |
| 配置文件 | `~/.hermes/config.yaml` | 行为设置、功能开关、显示偏好 |
| 密钥文件 | `~/.hermes/.env` | 仅存放 API key、token 等凭证 |
| 日志 | `~/.hermes/logs/` | `agent.log` (INFO+), `errors.log` (WARNING+), `gateway.log` |
| 技能 | `~/.hermes/skills/` | 用户创建的技能文件 |
| 插件 | `~/.hermes/plugins/` | 用户安装的插件 |
| 记忆 | `~/.hermes/memory.json` | Agent 自管理的持久笔记 |

### 4.11 CLI 子命令体系

通过 `hermes_cli/subcommands/` 实现 **30+ 子命令**：

| 子命令 | 实现文件 | 职责 |
|--------|----------|------|
| `hermes setup` | `subcommands/setup.py` | 首次配置向导 |
| `hermes config` | `subcommands/config.py` | 配置管理 |
| `hermes tools` | `subcommands/` (tools相关) | 工具集启用/禁用/状态查看 |
| `hermes gateway run` | `subcommands/gateway.py` | 启动消息网关 |
| `hermes cron` | `subcommands/cron.py` | 定时任务管理 |
| `hermes mcp` | `subcommands/mcp.py` | MCP 服务器管理 |
| `hermes memory` | `subcommands/memory.py` | 记忆管理 |
| `hermes plugins` | `subcommands/plugins.py` | 插件管理 |
| `hermes profile` | `subcommands/profile.py` | 多 Profile 管理 |
| `hermes dashboard` | `subcommands/dashboard.py` | Web 面板启动 |
| `hermes doctor` | `subcommands/doctor.py` | 环境诊断 |
| `hermes logs` | `subcommands/logs.py` | 日志查看 |
| `hermes auth` | `subcommands/auth.py` | 认证管理 |
| `hermes login/logout` | `subcommands/login.py` / `logout.py` | 登录登出 |
| `hermes backup` | `subcommands/backup.py` | 备份/恢复 |
| `hermes model` | `subcommands/model.py` | 模型选择 |
| `hermes acp` | `subcommands/acp.py` | ACP 编辑器协议 |
| `hermes insights` | `subcommands/insights.py` | 使用洞察 |
| `hermes security` | `subcommands/security.py` | 安全审计 |
| `hermes debug` | `subcommands/debug.py` | 调试 |
| `hermes dump` | `subcommands/dump.py` | 数据导出 |
| `hermes gui` | `subcommands/gui.py` | GUI 启动 |
| `hermes hooks` | `subcommands/hooks.py` | 钩子管理 |
| `hermes import` | `subcommands/import_cmd.py` | 数据导入 |
| `hermes pairing` | `subcommands/pairing.py` | 设备配对 |
| `hermes claw` | `subcommands/claw.py` | Claw 功能 |

### 4.12 Slash 命令注册中心

`hermes_cli/commands.py` 定义中央 `COMMAND_REGISTRY`（`CommandDef` 列表），所有下游消费者自动派生：

```python
CommandDef(
    name="mycommand",       # 规范名
    description="...",      # 描述
    category="Session",     # 分类: Session | Configuration | Tools & Skills | Info | Exit
    aliases=("mc",),        # 别名
    args_hint="[arg]",      # 参数提示
    cli_only=False,         # 仅 CLI 可用
    gateway_only=False,     # 仅网关可用
    gateway_config_gate=... # 配置门控
)
```

| 消费者 | 派生方式 |
|--------|----------|
| CLI | `process_command()` 解析别名后分派 |
| Gateway | `GATEWAY_KNOWN_COMMANDS` + `resolve_command()` 分派 |
| Telegram | `telegram_bot_commands()` 自动生成 BotCommand 菜单 |
| Slack | `slack_subcommand_map()` 自动生成子命令路由 |
| 自动补全 | `SlashCommandCompleter` 驱动 |
| CLI 帮助 | `COMMANDS_BY_CATEGORY` 驱动 `show_help()` |

---

## 五、Agent 内部模块 (`agent/`)

| 模块 | 文件 | 职责 |
|------|------|------|
| 对话循环 | `conversation_loop.py` | 核心对话迭代 |
| 系统提示词 | `system_prompt.py` | 三级提示词组装 |
| 提示词构建 | `prompt_builder.py` | 提示词各部件构建 |
| 记忆管理 | `memory_manager.py` | 记忆提供商编排 |
| 记忆抽象 | `memory_provider.py` | MemoryProvider ABC |
| 上下文引擎 | `context_engine.py` | 运行时上下文管理 |
| 上下文压缩 | `context_compressor.py` | 上下文压缩 |
| 会话压缩 | `conversation_compression.py` | 长会话压缩/分割 |
| 手动压缩反馈 | `manual_compression_feedback.py` | 用户反馈驱动压缩 |
| 提示词缓存 | `prompt_caching.py` | Prompt Cache 管理 |
| 编码上下文 | `coding_context.py` | 代码工作区检测、coding 工具集自动选择 |
| 技能命令 | `skill_commands.py` | 技能 Slash 命令注入 |
| 技能工具 | `skill_utils.py` | 技能解析辅助 |
| 技能预处理 | `skill_preprocessing.py` | 技能前置处理 |
| 技能包 | `skill_bundles.py` | 技能打包 |
| 子代理 | `auxiliary_client.py` | 辅助 LLM 客户端 |
| 后台审查 | `background_review.py` | 后台审查循环 |
| 迭代预算 | `iteration_budget.py` | 工具调用迭代预算管理 |
| 信用追踪 | `credits_tracker.py` | 信用额度追踪 |
| 使用定价 | `usage_pricing.py` | 使用量定价计算 |
| 账户用量 | `account_usage.py` | 账户用量查询 |
| 账单视图 | `billing_view.py` | 账单展示 |
| 速率限制 | `rate_limit_tracker.py` | 速率限制追踪 |
| 重试工具 | `retry_utils.py` | 通用重试逻辑 |
| 错误分类 | `error_classifier.py` | 错误分类与路由 |
| 消息内容 | `message_content.py` | 消息内容处理 |
| 消息清洗 | `message_sanitization.py` | 消息消毒 |
| 思维清洗 | `think_scrubber.py` | reasoning 内容清洗 |
| 标题生成 | `title_generator.py` | 会话标题生成 |
| 洞察 | `insights.py` | 使用洞察 |
| 轮次上下文 | `turn_context.py` | 单轮上下文 |
| 轮次终止 | `turn_finalizer.py` | 轮次收尾 |
| 轮次重试 | `turn_retry_state.py` | 轮次重试状态 |
| 模型元数据 | `model_metadata.py` | 模型元信息 |
| 模型开发 | `models_dev.py` | 模型开发辅助 |
| Gemini schema | `gemini_schema.py` | Gemini 模型 schema |
| Gemini 适配器 | `gemini_native_adapter.py` / `gemini_cloudcode_adapter.py` | Gemini 推理适配 |
| Anthropic 适配器 | `anthropic_adapter.py` | Anthropic 推理适配 |
| Bedrock 适配器 | `bedrock_adapter.py` | AWS Bedrock 适配 |
| Azure 适配器 | `azure_identity_adapter.py` | Azure Identity 适配 |
| Codex 适配器 | `codex_responses_adapter.py` / `codex_runtime.py` | OpenAI Codex 适配 |
| Copilot ACP | `copilot_acp_client.py` | Copilot ACP 客户端 |
| 凭证池 | `credential_pool.py` | 凭证池管理 |
| 凭证来源 | `credential_sources.py` | 凭证来源抽象 |
| 凭证持久化 | `credential_persistence.py` | 凭证持久化存储 |
| Shell 钩子 | `shell_hooks.py` | Shell 命令钩子 |
| 文件安全 | `file_safety.py` | 文件操作安全检查 |
| 门户标签 | `portal_tags.py` | Portal 标签 |
| Markdown 表格 | `markdown_tables.py` | 表格格式化 |
| i18n 国际化 | `i18n.py` | 多语言支持 |
| 浏览器提供商 | `browser_provider.py` / `browser_registry.py` | 浏览器后端注册 |
| 图片生成 | `image_gen_provider.py` / `image_gen_registry.py` / `image_routing.py` | 图片生成后端注册与路由 |
| 视频生成 | `video_gen_provider.py` / `video_gen_registry.py` | 视频生成后端注册 |
| TTS | `tts_provider.py` / `tts_registry.py` | TTS 后端注册 |
| 转录 | `transcription_provider.py` / `transcription_registry.py` | 转录后端注册 |
| Web 搜索 | `web_search_provider.py` / `web_search_registry.py` | Web 搜索后端注册 |
| 轨迹 | `trajectory.py` | 对话轨迹记录 |
| 流诊断 | `stream_diag.py` | 流式响应诊断 |
| LSP | `lsp/` (11 文件) | Language Server Protocol 集成 |
| 密钥管理 | `secret_sources/` + `secret_scope.py` | 密钥来源与作用域 |
| 传输层 | `transports/` (11 文件) | 多种 LLM 传输适配 |
| SSL 守卫 | `ssl_guard.py` | SSL 证书验证 |
| 运行时 CWD | `runtime_cwd.py` | 运行时工作目录解析 |
| 子目录提示 | `subdirectory_hints.py` | 项目子目录提示 |
| 显示 | `display.py` | 终端显示工具 |
| 异步工具 | `async_utils.py` | 异步辅助 |
| 插件 LLM | `plugin_llm.py` | 插件 LLM 接口 |
| 进程引导 | `process_bootstrap.py` | 进程启动引导 |
| 初始化 | `agent_init.py` | Agent 初始化逻辑 |
| 运行时辅助 | `agent_runtime_helpers.py` | Agent 运行时辅助 |
| 工具分发辅助 | `tool_dispatch_helpers.py` | 工具分发辅助 |
| 工具执行 | `tool_executor.py` | 工具执行器 |
| 工具护栏 | `tool_guardrails.py` | 工具安全护栏 |
| 工具结果分类 | `tool_result_classification.py` | 工具结果分类 |
| 策展 | `curator.py` / `curator_backup.py` | 内容策展 |
| 按需安装 | `jiter_preload.py` | JSON 解析器预加载 |
| Nous 速率守卫 | `nous_rate_guard.py` | Nous 订阅速率限制 |
| LM Studio 推理 | `lmstudio_reasoning.py` | LM Studio 推理适配 |
| Google OAuth | `google_oauth.py` / `google_code_assist.py` | Google 认证 |
| Antigravity 适配器 | `antigravity_cloudcode_adapter.py` / `antigravity_code_assist.py` / `antigravity_oauth.py` | Antigravity 适配 |
| Moonshot schema | `moonshot_schema.py` | Moonshot 模型 schema |

---

## 六、关键业务流程

### 6.1 用户消息处理流程

```
用户消息到达 (CLI / Telegram / Discord / ...)
  │
  ▼
平台适配器接收 (gateway/platforms/<platform>.py)
  │
  ▼
会话查找/创建 (gateway/session.py)
  │
  ▼
AIAgent 创建或复用 (gateway/run.py 缓存, 上限128个, 空闲1h驱逐)
  │
  ▼
系统提示词组装 (stable + context + volatile 三层)
  │
  ▼
对话循环开始 (run_conversation())
  │
  ├─ LLM 响应有 tool_calls? ─── 是 ──→ 工具分发执行 → 结果追加 → 继续循环
  │
  └─ LLM 响应有 tool_calls? ─── 否 ──→ 返回最终文本响应 → 平台适配器发送 → 用户
```

### 6.2 工具注册与发现流程

```
启动时 discover_builtin_tools()
  │
  ▼
扫描 tools/*.py (排除 __init__.py, registry.py, mcp_tool.py)
  │
  ▼
AST 静态分析：仅导入包含顶层 registry.register() 调用的模块
  │
  ▼
importlib 动态导入各工具模块
  │
  ▼
各工具模块在模块级别调用 registry.register(name, toolset, schema, handler, check_fn)
  │
  ▼
ToolRegistry 单例存储 name → ToolEntry 映射
  │
  ▼
get_definitions() 时运行 check_fn 过滤 (TTL 缓存 30s)
  │
  ▼
输出 OpenAI 格式 tool schemas → 随每次 API 调用发送
```

### 6.3 子代理委托流程

```
主 Agent 调用 delegate_task 工具
  │
  ▼
delegate_tool.py 创建新 AIAgent 实例 (隔离上下文)
  │
  ▼
配置子代理工具集、模型、迭代预算
  │
  ▼
子代理执行独立对话循环
  │
  ▼
返回结果给主 Agent
  │
  ▼
主 Agent 继续处理
```

### 6.4 记忆系统数据流

```
用户消息到达
  │
  ▼
MemoryManager.prefetch_all(user_message)
  ├─ Agent 记忆: 从 memory.json 加载相关笔记
  ├─ 会话搜索: FTS5 查询相关历史会话
  └─ 外部提供商: 调用 MemoryProvider.prefetch()
  │
  ▼
记忆内容注入到消息上下文
  │
  ▼
Agent 执行对话循环 (可使用 memory 工具读写记忆)
  │
  ▼
MemoryManager.sync_all(user_msg, assistant_response)
  ├─ 更新 Agent 记忆
  └─ 同步到外部提供商
```

### 6.5 MCP 集成流程

```
MCP Server 配置 (hermes mcp add)
  │
  ▼
mcp_tool.py 连接 MCP Server
  │
  ▼
发现 MCP Server 暴露的工具列表
  │
  ▼
注册到 ToolRegistry (toolset = "mcp-<servername>")
  │
  ▼
check_fn 检查服务器连通性 (TTL 缓存)
  │
  ▼
模型调用时透明分发到 MCP Server
  │
  ▼
结果返回 Agent
```

---

## 七、核心设计原则

| 原则 | 说明 |
|------|------|
| **Prompt Cache 神圣不可侵犯** | 每会话系统提示词字节级稳定，任何修改历史上下文的操作都会使缓存失效、增加成本。唯一例外是 context compression |
| **核心窄腰部** | 新增核心工具门槛极高（每次 API 调用都会发送）。能力扩展路径：扩展已有代码 → CLI+Skill → Service-gated → Plugin → MCP Server → 核心工具（最后手段） |
| **扩展而非复制** | 新功能优先复用已有基础设施，3+ PR 尝试同类集成时设计 ABC + 编排器 |
| **行为契约优于快照** | 测试断言关系不变量，不冻结具体值（模型列表、配置版本号等） |
| **插件不碰核心文件** | 插件在独立目录，通过 ABC + Hooks 扩展，需要更多能力时扩宽通用插件表面 |
| **角色交替严格** | 消息序列中不允许两个相同 role 的消息连续出现，不允许注入合成 user 消息 |
| **.env 仅存密钥** | 行为设置全部走 config.yaml，.env 仅存放 API key、token、password |
| **能力在边缘生长** | 产品表面（平台、渠道、提供商、模型、桌面/TUI 特性）积极扩展，核心腰部保持克制 |

---

## 八、目录结构速查

```
hermes-agent/
├── run_agent.py          # AIAgent 核心类 — 对话循环 (~5.5k LOC)
├── model_tools.py        # 工具编排、discover_builtin_tools()、handle_function_call()
├── toolsets.py           # 工具集定义、_HERMES_CORE_TOOLS 列表
├── cli.py                # HermesCLI 类 — 交互式 CLI 编排器 (~15k LOC)
├── hermes_state.py       # SessionDB — SQLite 会话存储 (FTS5 搜索)
├── hermes_constants.py   # get_hermes_home()、display_hermes_home()
├── hermes_logging.py     # setup_logging() — 日志配置
├── batch_runner.py       # 并行批处理
├── hermes_bootstrap.py   # 进程引导 (Windows UTF-8 stdio)
├── hermes_time.py        # 时间工具
├── toolset_distributions.py  # 工具集分布配置
├── mcp_serve.py          # MCP 服务器模式
├── mini_swe_runner.py    # SWE 基准测试
├── trajectory_compressor.py  # 轨迹压缩
├── utils.py              # 通用工具函数
│
├── agent/                # Agent 内部模块 (~70+ 文件)
│   ├── lsp/              # Language Server Protocol 集成
│   ├── secret_sources/   # 密钥来源
│   ├── transports/       # LLM 传输适配
│   ├── system_prompt.py  # 系统提示词组装
│   ├── prompt_builder.py # 提示词部件构建
│   ├── memory_manager.py # 记忆编排
│   ├── coding_context.py # 编码上下文检测
│   └── ...               # 提供商适配器、缓存、压缩等
│
├── tools/                # 工具实现 (~104 文件，自动发现)
│   ├── registry.py       # 工具注册中心
│   ├── environments/     # 终端后端 (6种)
│   ├── browser_tool.py   # 浏览器控制
│   ├── terminal_tool.py  # 终端执行
│   ├── file_tools.py     # 文件操作
│   ├── delegate_tool.py  # 子代理委托
│   ├── mcp_tool.py       # MCP 集成
│   └── ...               # 40+ 工具实现
│
├── gateway/              # 消息网关
│   ├── run.py            # 网关主循环 (~18k LOC)
│   ├── session.py        # 网关会话管理
│   ├── platforms/        # 平台适配器 (20+)
│   │   ├── base.py       # 平台 ABC (~5k LOC)
│   │   ├── api_server.py # OpenAI 兼容 API
│   │   ├── weixin.py     # 微信
│   │   ├── yuanbao.py    # 元宝
│   │   └── ...           # 更多平台
│   ├── stream_dispatch.py    # 流式分发
│   ├── slash_commands.py     # Slash 命令
│   └── ...
│
├── plugins/              # 插件系统 (18 个)
│   ├── memory/           # 记忆提供商
│   ├── model-providers/  # 推理后端
│   ├── context_engine/   # 上下文引擎
│   ├── kanban/           # 多 Agent 看板
│   ├── observability/    # 可观测性
│   └── ...               # 更多插件
│
├── skills/               # 内置技能 (17 组)
├── optional-skills/      # 可选技能 (19 组)
│
├── hermes_cli/           # CLI 子命令 (~30+)
│   ├── subcommands/      # 子命令实现
│   ├── commands.py       # Slash 命令注册中心
│   ├── config.py         # 配置管理
│   ├── skin_engine.py    # 皮肤引擎
│   └── ...
│
├── ui-tui/               # TUI 前端 (Ink/React)
├── tui_gateway/          # TUI Python JSON-RPC 后端
├── apps/desktop/         # Electron 桌面应用
├── apps/shared/          # 共享前端代码
├── web/                  # Web Dashboard
├── website/              # Docusaurus 文档站
├── acp_adapter/          # ACP 编辑器集成
├── cron/                 # 定时任务调度
├── scripts/              # 构建/发布脚本
├── tests/                # 测试套件 (~17k 测试 / ~900 文件)
├── nix/                  # Nix 构建配置
├── docker/               # Docker 配置 (s6-overlay)
├── locales/              # 国际化 (16 语言)
├── providers/            # 提供商配置
├── docs/                 # 设计文档
├── datagen-config-examples/  # 数据生成配置示例
└── packaging/            # 打包配置 (Homebrew)
```

---

## 九、关键文件依赖关系

```
hermes_constants.py  (无依赖 — 被所有模块导入)
       ↑
tools/registry.py  (工具注册中心)
       ↑
tools/*.py  (各工具实现，模块级自注册)
       ↑
toolsets.py  (工具集定义与组合)
       ↑
model_tools.py  (工具编排公共 API)
       ↑
run_agent.py  (AIAgent 核心)
       ↑
┌──────┼──────────┬──────────────┐
cli.py  gateway/run.py  batch_runner.py  acp_adapter/
```
