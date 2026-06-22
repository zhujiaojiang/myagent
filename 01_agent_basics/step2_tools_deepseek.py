# step2_tools_deepseek.py
# 第 2 步:给模型一份"工具说明书",看它如何"点单"
# 目标:理解 tool use(工具调用)协议 ——
#   模型本身不能查天气、不能执行任何动作;
#   但你给它一份"工具清单"后,它会在回复里说:"我想调用 get_weather,参数 city=北京"。
#   ⚠️ 它只是"提出请求(点单)",真正的执行要靠你的代码(下一步)。

import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # .env 在项目根目录(上一层)

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# ① 工具"说明书":告诉模型"你有哪些工具、每个叫什么、干嘛的、要什么参数"。
#    这不是函数本体,只是一张"菜单"——模型读它来决定要不要用、参数怎么填。
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",                      # 工具名字
            "description": "查询某个城市的当前天气",        # 干嘛用的(模型靠这句判断"何时该用")
            "parameters": {                              # 这个工具需要什么参数(用 JSON Schema 描述)
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称,例如:北京、上海",
                    }
                },
                "required": ["city"],                    # city 是必填项
            },
        },
    }
]

# ② 像第 1 步一样调用,唯一的新增:多带上 tools=工具说明书。
messages = [
    {"role": "user", "content": "北京今天天气怎么样?"}
]
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=tools,                 # ← 把"菜单"递给模型
)

message = response.choices[0].message

# ③ 看模型的反应。
#    关键:模型不会直接回答天气(它根本不知道),而是把"想调用的工具+参数"
#    放进 message.tool_calls 里。
print("模型直接说的话(content):", message.content)                       # 点单时通常是 None
print("停止原因(finish_reason):", response.choices[0].finish_reason)     # 会变成 tool_calls
print("-" * 40)

if message.tool_calls:
    print("✅ 模型决定点单!它想调用:")
    for tc in message.tool_calls:
        # ⚠️ 常见坑:tc.function.arguments 是一个【JSON 字符串】,不是字典!
        #    要用 json.loads() 把它解析成 Python 字典才能用。
        args = json.loads(tc.function.arguments)
        print(f"   工具名 : {tc.function.name}")
        print(f"   参数   : {args}        (类型: {type(args).__name__})")
        print(f"   调用ID : {tc.id}   ← 第3步喂结果时要用它来对应")
else:
    print("模型没点单,直接回答了:", message.content)

print("-" * 40)
print("到这里程序就结束了 —— 模型只是'点了单',并没有真的查到天气。")
print("因为'执行工具'得靠你的代码。这正是第 3 步要补上的。")
