# Hermes Agent 核心技术实现分析

> 基于 hermes-agent v0.17.0 源码分析
> 覆盖：对话循环、工具注册、MCP 协议集成、多模型适配

---

## 一、对话循环（Conversation Loop）

### 1.1 整体架构

```
用户输入
    │
    ▼
build_turn_context()  ← 每次对话前的上下文准备
    │
    ▼  ┌─────────────────────────────────────────────┐
    │  while (api_call_count < max_iterations         │
    │         && iteration_budget.remaining > 0)      │  ← 主循环
    │  ┌───────────────────────────────────────────┐  │
    │  │ 1. 构建 api_messages（消息组装）          │  │
    │  │ 2. 应用 prompt caching                    │  │
    │  │ 3. 消息序列修复                           │  │
    │  │ 4. 调用 LLM API                           │  │
    │  │ 5. 处理 tool_calls                        │  │
    │  │ 6. 追加 tool_result 到 messages           │  │
    │  └───────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────┘
    │
    ▼
final_response
```

**核心代码路径：**
```
run_agent.py
  └─ AIAgent.run_conversation()       ← 转发器
        └─ agent/conversation_loop.py
              └─ run_conversation()    ← 主循环体 (~3500 LOC)
```

### 1.2 build_turn_context — 每轮上下文准备

`agent/turn_context.py` 中的 `build_turn_context()` 负责每轮对话开始前的一次性准备工作：

| 步骤 | 说明 | 文件 |
|------|------|------|
| stdio 守卫 | 确保子进程的 stdout 不污染 JSON-RPC 协议 | `agent/turn_context.py` |
| 重试计数器重置 | 重置本轮的重试状态 | `agent/turn_context.py` |
| 用户消息清洗 | sanitize surrogates / BOM / 控制字符 | `agent/message_sanitization.py` |
| todo/nudge 注入 | 记忆回顾、技能提示、任务状态注入 | `agent/turn_context.py` |
| system prompt 重建或恢复 | 三级结构（stable/context/volatile） | `agent/system_prompt.py` |
| 崩溃恢复持久化 | 将当前消息持久化到 SQLite | `agent/turn_context.py` |
| 预检压缩 | 超阈值时触发上下文压缩 | `agent/conversation_compression.py` |
| pre_llm_call 插件钩子 | 允许外部插件修改本轮上下文 | `plugins/` |
| 外部记忆预取 | 从 MemoryProvider 检索相关内容 | `agent/memory_manager.py` |
| 消息历史加载 | 从 SQLite 加载历史消息并注入到本轮 | `agent/turn_context.py` |

### 1.3 主循环核心逻辑

```python
while (api_call_count < agent.max_iterations
       and agent.iteration_budget.remaining > 0) \
       or agent._budget_grace_call:
    
    # ── 1. 构建 API 消息 ──
    api_messages = build_api_messages(messages, system_prompt)
    
    # ── 2. 应用 Anthropic prompt caching ──
    if agent._use_prompt_caching:
        api_messages = apply_anthropic_cache_control(api_messages)
    
    # ── 3. 消息序列修复 ──
    #     修复 role alternation（不能有两个同 role 连续）
    api_messages = agent._sanitize_api_messages(api_messages)
    api_messages = agent._drop_thinking_only_and_merge_users(api_messages)
    
    # ── 4. 调用 LLM API ──
    response = run_llm_execution_middleware(
        api_kwargs, _perform_api_call, ...
    )
    
    # ── 5. 处理 tool_calls 或返回结果 ──
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = handle_function_call(tool_call.name, tool_call.args)
            messages.append(tool_result_message(result))
    else:
        final_response = response.content
        break
    
    api_call_count += 1
```

**关键设计决策：**

- **同步阻塞模型**：整个循环在单线程中同步执行，不涉及 asyncio。这在 `run_agent.py` 中有明确注释："entirely synchronous, with interrupt checks"
- **中断检查**：每个循环迭代开始时检查 `agent._interrupt_requested`，支持用户在工具循环中发送新消息打断
- **预算控制**：两层预算 — `max_iterations`（硬限制）和 `iteration_budget`（软限制，允许最后一次优惠调用）
- **Steer 机制**：`_drain_pending_steer()` 在每次 API 调用前消费用户发来的修正指令，注入到上一条 tool 消息中

### 1.4 消息格式

采用 OpenAI Chat Completions 格式：

```python
[
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...", "tool_calls": [...]},
    {"role": "tool", "content": "...", "tool_call_id": "..."},
]
```

`reasoning` 字段单独存储在 assistant 消息中，UI 显示时为思考过程，API 调用时复制到 `reasoning_content`。

### 1.5 API 调用路径

```python
# run_llm_execution_middleware()  →  中间件链
    # └─ pre_api_request 钩子      →  插件系统（如 langfuse 追踪）
        # └─ _perform_api_call()    →  实际 SDK 调用
            # ├─ _interruptible_api_call()         → 非流式
            # └─ _interruptible_streaming_api_call() → 流式
```

中断机制通过 `threading.Event` 实现：在单独的线程中执行 SDK 调用，主线程等待 Event，收到中断信号时关闭 HTTP 连接。

---

## 二、工具注册（Tool Registry）

### 2.1 架构

```
tools/registry.py
  └── ToolRegistry（单例）
        ├── register()              ← 工具声明
        ├── dispatch()              ← 工具调用
        ├── get_definitions()       ← 获取 schema 列表
        └── check_fn TTL 缓存       ← 可用性检查缓存
            ↑
tools/*.py                           ← 各个工具实现文件
  └── 模块级 registry.register()      ← 自注册

model_tools.py
  ├── discover_builtin_tools()       ← 触发自动发现
  ├── handle_function_call()         ← 工具调用入口
  └── get_tool_definitions()         ← 工具列表入口
```

### 2.2 自动发现机制

```python
def discover_builtin_tools(tools_dir=None):
    """扫描 tools/ 目录，导入所有自注册工具模块"""
    # 1. 扫描 tools/*.py（排除 __init__, registry, mcp）
    # 2. AST 静态分析：检测模块是否包含 registry.register() 调用
    # 3. importlib.import_module() 动态导入
    # 4. 模块级 registry.register() 自注册到 ToolRegistry
```

**关键特性：**
- **AST 预检**：`_module_registers_tools()` 先做静态分析，跳过不包含 `registry.register()` 的模块，避免无用导入
- **hermes3 扩展**：`discover_builtin_tools()` 额外扫描 `hermes3/tools/` 目录（hermes3 改造时添加）
- **延迟导入**：`_module_registers_tools()` 只做语法树分析（`ast.parse`），不执行代码，性能开销极小

### 2.3 ToolEntry 数据结构

```python
class ToolEntry:
    __slots__ = (
        "name",           # 工具名，如 "web_search"
        "toolset",        # 工具集名，如 "web"
        "schema",         # OpenAI function calling schema
        "handler",        # 同步调用函数
        "check_fn",       # 可用性检查函数（可选）
        "requires_env",   # 必需的环境变量列表
        "is_async",       # 是否异步执行
        "description",    # 可读描述
        "emoji",          # 显示 emoji
        "max_result_size_chars",     # 结果截断上限
        "dynamic_schema_overrides",  # 运行时 schema 覆盖
    )
```

### 2.4 注册与调度流程

```python
# 注册（在 tools/*.py 模块级执行）
registry.register(
    name="web_search",
    toolset="web",
    schema=WEB_SEARCH_SCHEMA,    # OpenAI function calling schema
    handler=lambda args, **kw: web_search_tool(...),
    check_fn=check_web_api_key,  # 仅当 API key 配置时才可用
    emoji="🔍",
)

# 调度（在 handle_function_call 中触发）
def handle_function_call(name, args, task_id):
    entry = registry.get(name)
    if entry is None:
        return f"Error: Unknown tool '{name}'"
    # check_fn 缓存 30 秒
    if entry.check_fn and not entry.check_fn(task_id=task_id):
        return f"Error: Tool '{name}' requirements not met"
    return entry.handler(args, task_id=task_id)
```

### 2.5 工具集系统（toolsets.py）

```python
TOOLSETS = {
    "web": {
        "description": "网页搜索与内容提取",
        "tools": ["web_search", "web_extract"],
        "includes": []            # 支持递归引用其他工具集
    },
    "hermes3": {                  # 小说创作工具集（hermes3 新增）
        "description": "小说创作工具",
        "tools": ["novel_character", "novel_worldbuilding", ...],
        "includes": []
    },
}
```

`resolve_toolset()` 递归解析工具集，检测循环引用。工具集支持 `includes` 字段组合其他工具集。

### 2.6 check_fn TTL 缓存

```python
# tools/registry.py 中
_check_fn_cache: Dict[str, tuple[float, Optional[bool]]] = {}
_CACHE_TTL = 30.0  # 秒
```

每次 `dispatch()` 调用时先查缓存，30 秒内不再重复执行 `check_fn`。这在频繁调用场景（如 delegate_task 批量调度）中显著减少开销。

---

## 三、MCP 协议集成

### 3.1 架构

```
tools/mcp_tool.py (~4100 LOC)

┌─ MCP 配置管理 ───────────────────────────────┐
│  config.yaml 中的 mcpServers 字段              │
│  ↓                                            │
│  _load_mcp_config()                            │
│  → 读取 mcpServers 配置                        │
│  → 覆盖 yaml 字段到 server 配置                 │
└──────────────────────────────────────────────┘
              ↓
┌─ MCP 服务端生命周期 ──────────────────────────┐
│  MCPServerTask                                 │
│    ├─ _run_http()    — SSE / Streamable HTTP   │
│    ├─ _run_stdio()   — 子进程 JSON-RPC stdio   │
│    └─ _run_websocket() — WS 直连              │
└──────────────────────────────────────────────┘
              ↓
┌─ 工具桥接 ───────────────────────────────────┐
│  register_mcp_servers()                       │
│  → 连接 MCP Server                            │
│  → list_tools() 获取工具列表                   │
│  → registry.register() 注册为 hermes 内置工具   │
└──────────────────────────────────────────────┘
```

### 3.2 传输协议支持

| 协议类型 | 实现函数 | 说明 |
|----------|----------|------|
| **stdio** | `MCPServerTask._run_stdio()` | 子进程标准输入/输出 JSON-RPC |
| **HTTP SSE** | `MCPServerTask._run_http()` | Server-Sent Events 流式传输 |
| **Streamable HTTP** | `MCPServerTask._run_http()` | MCP 新版 HTTP 传输（`streamableHttpTransport`） |
| **WebSocket** | `MCPServerTask._run_websocket()` | 直接 WebSocket 连接 |

### 3.3 工具注册流程

```python
def register_mcp_servers(servers):
    """将 MCP 服务器的工具注册为 hermes 内置工具"""
    for name, cfg in servers.items():
        # 1. 创建 MCP 连接会话
        task = MCPServerTask(name, cfg)
        task.start()
        
        # 2. 等待连接就绪
        task.wait_ready()
        
        # 3. 获取服务器工具列表
        tools = task.session.list_tools()
        
        # 4. 注册到 hermes 的 registry
        for tool in tools:
            registry.register(
                name=f"mcp__{server_name}__{tool.name}",
                toolset=f"mcp-{server_name}",
                schema=convert_mcp_to_openai_schema(tool),
                handler=mcp_call_handler(server_name, tool.name),
                override=True,  # 允许 MCP 工具覆盖
            )
```

**关键设计：**
- 工具名前缀 `mcp__{server_name}__`，确保全局唯一
- `override=True` 允许 MCP 工具替换同名的内置工具
- 连接失败不阻塞启动，仅在 `model_tools.py` 中记录警告日志

### 3.4 认证支持

| 认证类型 | 实现 |
|----------|------|
| API Key / Bearer Token | HTTP Header 注入 |
| OAuth 2.0 | `ElicitationHandler` 支持 OAuth 授权流程 |
| 无认证 | 直接连接（localhost stdio 等） |

OAuth 流程通过 `ElicitationHandler.__call__()` 拦截 MCP SDK 的授权请求，向用户展示授权 URL，等待用户完成授权后继续。

### 3.5 配置示例

```yaml
# config.yaml
mcpServers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "."]
    enabled: true
  web-search:
    url: "https://api.example.com/mcp"
    api_key: "${MCP_WEB_SEARCH_API_KEY}"
    transport: "streamable-http"
    timeout: 30
    max_rpm: 10
```

---

## 四、多模型适配（Multi-Model Adapter）

### 4.1 适配器架构概览

```
agent/
├── anthropic_adapter.py          ~2590 LOC    ← Anthropic Messages API
├── gemini_native_adapter.py      ~1002 LOC    ← Google Gemini Native API
├── gemini_cloudcode_adapter.py   ~500 LOC     ← Google Cloud Code
├── bedrock_adapter.py            ~300 LOC     ← AWS Bedrock
├── azure_identity_adapter.py     ~200 LOC     ← Azure OpenAI
├── codex_responses_adapter.py    ~1000 LOC    ← GitHub Codex
├── antigravity_cloudcode_adapter.py           ← Antigravity Cloud
├── antigravity_code_assist.py                 ← Antigravity Code Assist
├── antigravity_oauth.py                       ← Antigravity OAuth
├── google_code_assist.py                      ← Google Code Assist
├── google_oauth.py                            ← Google OAuth
├── lmstudio_reasoning.py                      ← LM Studio
├── moonshot_schema.py                         ← Moonshot AI
└── chat_completion_helpers.py                 ← 共用辅助函数
```

### 4.2 适配器模式

所有适配器遵循同一个设计模式：

```python
# 1. Lazy SDK 导入
def _get_anthropic_sdk():
    """只在首次使用时导入，避免启动时 ~220ms 开销"""
    if _anthropic_sdk is ...:
        try:
            import anthropic
            _anthropic_sdk = anthropic
        except ImportError:
            _anthropic_sdk = None
    return _anthropic_sdk

# 2. 消息格式转换
def convert_openai_to_provider(messages):
    """将 Hermes 内部 OpenAI 格式 → 厂商格式"""
    ...

# 3. 请求构建
def build_api_kwargs(messages, tools, **kwargs):
    """构建厂商 SDK 的请求参数"""
    ...

# 4. 响应解析
def parse_provider_response(response):
    """将厂商响应 → Hermes 内部格式"""
    ...
```

### 4.3 核心适配器对比

| 适配器 | API 模式 | 核心差异 | SDK |
|--------|----------|----------|-----|
| **Anthropic** | `chat_completions` | 需要 `anthropic-version` header，支持 extended thinking、prompt caching | `anthropic` SDK |
| **Gemini Native** | `chat_completions` | 消息格式与 OpenAI 差异大，需完整 schema 转换 | `google-genai` SDK |
| **Bedrock** | `chat_completions` | AWS SigV4 签名认证 | `boto3` |
| **Azure** | `chat_completions` | Azure AD 令牌认证 | `azure-identity` |
| **Codex** | `codex_responses` | 独立 API 模式，不兼容 chat_completions | 自定义 HTTP |
| **OpenAI 兼容** | `chat_completions` | 标准格式，最小转换 | `openai` SDK |

### 4.4 AIAgent 中的适配器选择

```python
# run_agent.py / agent_init.py 中
@property
def api_mode(self):
    """决定使用哪种 API 调用方式"""
    # 由 provider 和 config 共同决定
    # chat_completions    → OpenAI 格式（标准路径）
    # codex_responses     → GitHub Codex（独立路径）
    # codex_app_server    → Codex App Server（独立子进程）
    pass

def _build_api_kwargs(self, messages, tools, stream=False):
    """根据 api_mode 和 provider 构建 API 请求参数"""
    if self.api_mode == "codex_responses":
        return build_codex_kwargs(...)
    # 标准 chat_completions 路径
    kwargs = {
        "model": self.model,
        "messages": messages,
        "tools": tools,
        "stream": stream,
        "max_tokens": self.max_tokens,
    }
    # 按 provider 注入特定参数
    if self.provider == "anthropic":
        kwargs.update(build_anthropic_specific_kwargs(self))
    elif self.provider == "gemini":
        kwargs.update(build_gemini_specific_kwargs(self))
    return kwargs
```

### 4.5 Anthropic 适配器深度分析

**认证方式（三种）：**

| 方式 | 凭证来源 | 认证头 |
|------|----------|--------|
| API Key | `ANTHROPIC_API_KEY` | `x-api-key: sk-ant-*` |
| OAuth Token | `~/.claude.json` | `Authorization: Bearer` |
| Bedrock | AWS 凭证 | SigV4 签名 |

**Prompt Caching 实现：**

```python
# agent/anthropic_adapter.py
def apply_cache_control(messages, cache_ttl):
    """在 system prompt 和最后 3 条消息上注入 cache_control"""
    # 1. system message → ephemeral cache
    # 2. 最后 3 条 user/tool 消息 → ephemeral cache
    # 效果：多轮对话减少 ~75% 输入 token 成本
```

**Thinking 模式（两种）：**

| 模式 | 旧版（Claude 3.x） | 新版（Claude 4.x+） |
|------|-------------------|-------------------|
| 机制 | `thinking.type: enabled` + `budget_tokens` | `thinking.type: enabled` + `thinking_budget.type: adaptive` |
| 温度 | 不支持 | 支持（adaptive mode 下自动管理） |
| 检测 | `_need_old_extended_thinking()` | `_need_new_extended_thinking()` |

### 4.6 Gemini 原生适配器深度分析

**为什么需要独立适配器：**

```
OpenAI 格式                    Gemini 原生格式
─────────────────              ─────────────────
messages: [{                   contents: [{
  role: "user",                  role: "user",
  content: "hello"               parts: [{text: "hello"}]
}]                            }]
tools: [{                      tools: [{
  type: "function",              function_declarations: [{
  function: {                      name: "...",
    name: "...",                   parameters: {...}
    parameters: {...}            }]
  }                            }]
}]                            }
```

**关键转换函数：**
- `openai_messages_to_gemini_contents()` — 消息格式转换
- `openai_tools_to_gemini_declarations()` — 工具格式转换
- `sanitize_gemini_tool_parameters()` — 清洗 Gemini 不支持的参数描述格式

### 4.7 provider 选择链

```
用户配置 "deepseek-chat"
    → provider = "openai-compatible"
    → base_url = "https://api.deepseek.com"
    → api_mode = "chat_completions"
    → 标准 OpenAI SDK 调用

用户配置 "anthropic/claude-sonnet-4"
    → provider = "anthropic"
    → api_mode = "chat_completions"
    → Anthropic SDK + 特殊参数处理
```

Provider 的解析在 `hermes_cli/runtime_provider.py` 中完成，支持：
- 预设 provider 列表（openai, anthropic, gemini, openrouter 等）
- 自定义 provider（openai-compatible，需指定 base_url）
- provider 排序/竞价（`providers_order` / `provider_sort`）
- provider 权限控制（`providers_allowed` / `providers_ignored`）

---

## 五、四者协同关系

```
用户输入
    │
    ▼
┌─ 对话循环 (conversation_loop.py) ──────────────────────┐
│                                                         │
│  1. build_turn_context()                                 │
│     ├─ 加载记忆 (memory_manager)                         │
│     ├─ 重建 system prompt (prompt_builder)               │
│     └─ 触发 pre_llm_call 插件                             │
│                                                         │
│  2. 构建 api_messages                                    │
│     ├─ 加入工具定义 ← get_tool_definitions()              │
│     │                    └─ ToolRegistry                   │
│     │                       ├─ 内置工具 (tools/*.py)      │
│     │                       └─ MCP 工具 (mcp_tool.py)     │
│     └─ 加入缓存控制 ← Anthropic prompt caching            │
│                                                         │
│  3. 调用 LLM ← _build_api_kwargs()                       │
│     │              └─ 适配器选择                          │
│     │                 ├─ AnthropicAdapter                 │
│     │                 ├─ GeminiAdapter                    │
│     │                 └─ OpenAIAdapter (默认)             │
│     ▼                                                   │
│  response ← {content | tool_calls}                       │
│                                                         │
│  4. 处理 tool_calls                                      │
│     └─ handle_function_call()                            │
│          └─ registry.dispatch()                          │
│             ├─ 内置函数直接调用                           │
│             └─ MCP 工具 → MCPServerTask.call_tool()       │
│                                                         │
│  5. 循环直到无 tool_calls 或达到限制                      │
└─────────────────────────────────────────────────────────┘
    │
    ▼
final_response
```

### 关键性能特性

| 特性 | 机制 | 效果 |
|------|------|------|
| Prompt Caching | Anthropic cache_control breakpoints | 多轮对话减少 ~75% 输入 token 成本 |
| 中断机制 | threading.Event + HTTP 连接关闭 | 用户可随时打断工具循环 |
| check_fn TTL | 30 秒缓存 check_fn 结果 | 高频工具调度减少 I/O |
| MCP 连接池 | 多 Server 并行连接 | 工具调用不阻塞 |
| SDk 延迟导入 | Lazy import + sentinel 标记 | 启动时不加载 SDK (~220ms/个) |
| 预算双重控制 | max_iterations + iteration_budget | 防止无限循环和 token 透支 |

---

## 六、对 hermes3 的启示

| hermes3 需求 | 可复用机制 |
|-------------|-----------|
| 多 Agent 调度 | 对话循环 + delegate_tool 子代理派生 |
| 14 个 Agent 工具 | ToolRegistry + novel_* 工具注册 |
| 本地文件读写 | MCP 协议（文件系统 Server） |
| 多模型切换 | Provider 适配器体系直接复用 |
| Agent Skill.md 加载 | 对话循环的 system prompt 构建机制 |
