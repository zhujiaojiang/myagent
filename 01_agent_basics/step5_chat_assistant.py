# step5_chat_assistant.py
# 第 5 步:工程化(上)—— 一个能连续对话、有记忆、有人设的助手。
# 这是"完整命名版":所有变量都用看名字就懂的全称,不用 tc / args 这种简写。
#
# 三个核心点(标了是【Python 基础】还是【agent 概念】):
#   ① system 系统提示词:给助手定人设。              【agent 概念】
#   ② input() + while:不停接收你的输入。            【Python 基础】
#   ③ messages 全程保留 = "记忆"。                   【agent 概念】

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv


# ========== 第一块:读取配置(全部来自 .env,换厂商只改 .env)==========
load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # .env 在项目根目录(上一层)

api_key    = os.environ.get("DEEPSEEK_API_KEY")   # 你的钥匙(.env 里放谁家的 key 就连谁家)
base_url   = os.environ.get("BASE_URL")           # 连谁家的服务器(在 .env 里配)
model_name = os.environ.get("MODEL")              # 用谁家的模型(在 .env 里配)

# 友好检查:.env 没填好就给一句看得懂的提示,而不是报天书。
if not api_key:
    raise SystemExit("没找到 API key —— 请在 .env 里填上 DEEPSEEK_API_KEY。")
if not base_url or not model_name:
    raise SystemExit("没找到 BASE_URL 或 MODEL —— 请把 .env 补全。")

client = OpenAI(api_key=api_key, base_url=base_url)


# ========== 第二块:工具的"菜谱"(你自己写的真函数)==========

def get_weather(city: str) -> str:
    """真·联网查天气(用 wttr.in,免费、不需要额外的 key)。"""
    try:
        request_url = f"https://wttr.in/{urllib.parse.quote(city)}?format=%C+%t&lang=zh"
        request = urllib.request.Request(request_url, headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            weather_text = response.read().decode("utf-8").strip()   # 读回来是字节,decode 成中文字符串
        return f"{city}当前天气:{weather_text}"
    except Exception as error:
        # 联网可能失败(断网、超时、城市查不到)。工具要"优雅报错",别让整个程序崩。
        return f"查询 {city} 天气失败:{error}"


def calculate(first_number: float, second_number: float, operator: str) -> str:
    """做一步四则运算(真算)。operator(运算符)只能是 + - * / 之一。"""
    if operator == "+":
        result = first_number + second_number
    elif operator == "-":
        result = first_number - second_number
    elif operator == "*":
        result = first_number * second_number
    elif operator == "/":
        result = first_number / second_number
    else:
        return f"不支持的运算符:{operator}"
    return f"{first_number} {operator} {second_number} = {result}"


# ========== 第三块:工具"菜单"(给模型看的说明书)+ 注册表 ==========
# tools 是给【模型】看的说明书:模型读 description 判断"何时该用",读 parameters 知道"参数怎么填"。
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某个城市的当前真实天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名,如 北京、上海"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "做一步基础四则运算(加、减、乘、除)",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_number":  {"type": "number", "description": "第一个数"},
                    "second_number": {"type": "number", "description": "第二个数"},
                    "operator":      {"type": "string", "enum": ["+", "-", "*", "/"], "description": "运算符"},
                },
                "required": ["first_number", "second_number", "operator"],
            },
        },
    },
]

# 注册表:把"工具名(字符串)" 对应到 "真函数"。
# 模型点单时只给名字字符串,这张表帮我们把字符串换成真正能调用的函数。
available_tools = {
    "get_weather": get_weather,
    "calculate": calculate,
}


# ========== 第四块:对话循环(心脏)==========

# ① 系统提示词:给助手定"人设/规则",贯穿整场对话。改这句,助手的性格就会变。 【agent 概念】
system_prompt = "你是一个简洁、友好的中文助手,能查天气和做计算。回答尽量简短,不啰嗦。"

# messages = 对话历史。一开始就放入 system,然后【全程保留、一路变长】—— 这就是"记忆"。 【agent 概念】
messages = [
    {"role": "system", "content": system_prompt}
]

print("助手已就绪!直接在下面打字跟我聊。(输入 退出 / quit 结束)\n")

max_rounds = 5   # 一句话内,最多让 agent 循环这么多轮,防止万一陷入死循环

# ② 外层"对话循环":while True = 一直循环,直到我们主动 break。  【Python 基础】
while True:
    user_input = input("你: ")        # input():程序停在这里,等你在终端打字、回车  【Python 基础】

    # 输入退出词就结束。.strip() 去掉首尾空格,避免多打了空格导致判断失败。
    if user_input.strip() in ("退出", "quit", "exit"):
        print("拜拜!")
        break

    # 把你这句话追加进对话历史(role = user)。
    messages.append({"role": "user", "content": user_input})

    # ③ 内层"agent 循环":模型点单 → 执行工具 → 喂回结果 → 直到模型给最终答复。
    #    下划线 _ 表示"只是要循环这么多次,这个计数本身用不到"。
    for _ in range(max_rounds):
        model_response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools,
        )
        assistant_message = model_response.choices[0].message

        # 情况 A:模型没点单 → 它给出最终答复了。
        if not assistant_message.tool_calls:
            messages.append(assistant_message)                  # ★ 把助手的回复也存进历史(它才记得自己说过啥)
            print(f"助手: {assistant_message.content}\n")
            break

        # 情况 B:模型点单了 → 执行工具,把结果喂回。
        messages.append(assistant_message)                      # 先把"点单"这条消息存进历史

        # 逐个处理模型点的每一张"订单"(一张订单 = 一次工具调用请求)。
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name                          # 要调用的工具名,如 "get_weather"
            tool_arguments = json.loads(tool_call.function.arguments)    # 参数:JSON 字符串 → 字典
            tool_function = available_tools[tool_name]                   # 用名字从注册表里找到真函数
            tool_result = tool_function(**tool_arguments)                # 执行!** 把字典拆成关键字参数传进去

            print(f"   (后台调用 {tool_name} → {tool_result})")          # 让你看见它在后台干活(纯调试)

            # 把工具结果作为一条 role="tool" 的消息,贴上取餐号,追加进历史。
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })
        # 内层这一轮结束,回到 for 顶部,带着工具结果再问模型一次。
    # 回到 while 顶部,等你下一句话 —— messages 里存着到此为止的全部对话。
