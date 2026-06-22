# step9_agent_over_mcp.py
# 第 9 步:把大模型接进来 —— 让模型【自己决定】调用哪个 MCP 工具。
#
# ======================================================================
# 这一步 = step5(agent 循环) + step8(MCP 客户端) 的合体
# ----------------------------------------------------------------------
#   · step5:模型决定调工具 → 执行 → 结果喂回 → 循环到最终答复(agent 循环)
#   · step8:连上 MCP 服务端,list_tools 发现工具,call_tool 真的调用
#
# 唯一的新东西,就一件:
#   把"工具从哪来、怎么执行",从【本地函数】换成【MCP】。
#   模型那一套(怎么决定调哪个、怎么点单)一个字都不用变。
# ======================================================================

import os
import json
import asyncio
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ========== 读配置(和 step5 一模一样,从 .env 来)==========
load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # .env 在项目根目录(上一层)
api_key    = os.environ.get("DEEPSEEK_API_KEY")
base_url   = os.environ.get("BASE_URL")
model_name = os.environ.get("MODEL")

if not api_key or not base_url or not model_name:
    raise SystemExit("请检查 .env:DEEPSEEK_API_KEY / BASE_URL / MODEL 是否都填了。")

# 注意:OpenAI(...) 只是"造一个客户端对象",并不会联网,所以不花额度。
openai_client = OpenAI(api_key=api_key, base_url=base_url)


# ======================================================================
# 【新东西①:把 MCP 的工具清单,翻译成 OpenAI API 能看懂的格式】
# ----------------------------------------------------------------------
# 两边都用 JSON Schema 描述工具,只是外层包装略有不同:
#   MCP 给的:    mcp_tool.name / .description / .inputSchema
#   OpenAI 要的: {"type":"function","function":{"name","description","parameters"}}
#
# 关键:MCP 的 inputSchema【正好】就是 OpenAI 要的 parameters(本来就是同一个
#       JSON Schema 标准),所以几乎是直接套进去,不用自己拼。
# ======================================================================
def convert_mcp_tools_to_openai_format(mcp_tools):
    """把 MCP 风格的工具清单,转成 OpenAI API 的 tools 格式并返回。"""
    openai_tools = []
    for mcp_tool in mcp_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": mcp_tool.name,
                "description": mcp_tool.description,
                "parameters": mcp_tool.inputSchema,
            },
        })
    return openai_tools


# ======================================================================
# 主流程(用 async def,因为 MCP 客户端是异步的)
# ======================================================================
async def run_agent_over_mcp():
    # —— 连 MCP 服务端:这三步你 step8 见过(启动+管道 → 会话 → 握手)——
    project_directory = Path(__file__).resolve().parent
    python_executable = project_directory.parent / ".venv" / "Scripts" / "python.exe"   # .venv 在根目录(上一层)
    server_file = project_directory / "step7_weather_mcp_server.py"

    server_parameters = StdioServerParameters(
        command=str(python_executable),
        args=[str(server_file)],
    )

    async with stdio_client(server_parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as client_session:
            await client_session.initialize()

            # 发现工具 → 翻译成模型能读的格式
            mcp_tools_response = await client_session.list_tools()
            openai_tools = convert_mcp_tools_to_openai_format(mcp_tools_response.tools)
            print(f"已从 MCP 发现并装载 {len(openai_tools)} 个工具,交给模型备用。\n")

            # ================================================================
            # 下面这段 agent 循环,和 step5 几乎一模一样 —— 你已经很熟了
            # ================================================================
            system_prompt = "你是一个简洁友好的中文助手,能查实时天气和城市人口。回答简短。"
            user_question = "北京今天天气怎么样?另外北京大概有多少人口?"
            print(f"你:{user_question}\n")

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question},
            ]

            max_rounds = 5   # 防止万一陷入死循环
            for _ in range(max_rounds):
                # 同步的 OpenAI 调用(和 step5 一样)。
                # 【诚实说明】严格讲,在 async 里应该用异步版 AsyncOpenAI;
                #   但为了跟 step5 保持一致、不给你引入新东西,这里先用同步版。
                #   单用户跑完全没问题,以后要扛并发再换异步版。
                model_response = openai_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=openai_tools,
                )
                assistant_message = model_response.choices[0].message

                # 情况 A:模型不点工具了 → 给最终答复 → 结束
                if not assistant_message.tool_calls:
                    print(f"助手:{assistant_message.content}")
                    break

                # 情况 B:模型点工具了 → 通过 MCP 执行,把结果喂回
                messages.append(assistant_message)
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_arguments = json.loads(tool_call.function.arguments)

                    # ★★★ step9 唯一的关键改动就在这一行 ★★★
                    #   step5 是: tool_result = 本地函数(**参数)
                    #   step9 是: 通过 MCP 让【另一个程序】去执行
                    mcp_call_result = await client_session.call_tool(tool_name, tool_arguments)
                    tool_result_text = mcp_call_result.content[0].text

                    print(f"   (模型决定调 {tool_name},参数 {tool_arguments} → 经 MCP 得到:{tool_result_text})")

                    # 把工具结果贴上取餐号,作为 role=tool 的消息喂回(和 step5 一样)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result_text,
                    })
            # 回到 for 顶部,带着工具结果再问模型一次,直到它给出最终答复。


if __name__ == "__main__":
    asyncio.run(run_agent_over_mcp())
