# myagent · 从 0 手写 Agent 的学习项目

目标:吃透 Agent 原理 + 补工程能力,走向**初级 FDE**。

## 目录结构(按学习阶段 / 对应 FDE 学习地图)

| 文件夹 | 学习阶段 | 地图 Phase | 状态 |
|---|---|---|---|
| `01_agent_basics/` | Agent 基础原理 | Phase 00 | ✅ 完成 |
| `02_mcp/` | MCP 工具协议 | Phase 01 | ✅ 完成 |
| `03_python_engineering/` | Python 工程基本功 | Phase 02 | ⏳ 待填 |
| `04_rag/` | RAG 与私有知识 | Phase 03 | ⏳ 待填(下一站) |
| `05_production/` | 生产级 Agent 骨架 | Phase 04 | ⏳ 待填 |
| `06_security_project/` | 安全领域 FDE 作品 | Phase 05 | ⏳ 待填 |
| `07_delivery/` | 部署 · Eval · 求职交付 | Phase 06 | ⏳ 待填 |

## 已完成的 step 索引

### 01_agent_basics(基础 Agent · function calling)
- `step1_hello.py` — 裸调 Claude API(最初版本)
- `step1_hello_deepseek.py` — 裸调 DeepSeek(现在主用)
- `step2_tools_deepseek.py` — 给模型一份工具说明书(function calling)
- `step2b_tools_multi_deepseek.py` — 多工具,模型自己挑
- `step3_agent_loop_deepseek.py` — Agent Loop(ReAct)核心 ★
- `step4_real_weather_deepseek.py` — 接真·联网工具
- `step5_chat_assistant.py` — 记忆 + 人设(完整命名版)
- `step6_streaming.py` — 流式输出

### 02_mcp(MCP · 工具与 Agent 解耦)
- `step6b_async_basics.py` — 异步入门(MCP 前置课,做早餐比喻)
- `step7_weather_mcp_server.py` — MCP 服务端(挂工具,已接真天气)
- `step8_mcp_client.py` — MCP 客户端(连接 → 发现 → 调用)
- `step9_agent_over_mcp.py` — 模型 + MCP(模型自己驱动 MCP 工具)

## 约定

- **配置统一在根目录 `.env`**(`DEEPSEEK_API_KEY` / `BASE_URL` / `MODEL`),所有阶段共用一份。
  各文件用 `Path(__file__).resolve().parent.parent / ".env"` 往上一层找它。
- **虚拟环境在根目录 `.venv`**。运行任何文件请用它的解释器,例如:
  ```
  .venv\Scripts\python.exe 02_mcp\step8_mcp_client.py
  ```
  (VS Code 里把解释器选成 `.venv` 即可点 ▶ 运行。)
- `__pycache__/` 是 Python 自动生成的字节码缓存,可随时删,已被 `.gitignore` 忽略。

## 更新记录
- 项目已上传 GitHub,跑通 Git 日常流程(add / commit / push)。
