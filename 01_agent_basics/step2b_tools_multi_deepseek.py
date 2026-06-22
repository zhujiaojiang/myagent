# step2b_tools_multi_deepseek.py
# 第 2 步(加强版):放【多个】工具,看模型自己挑该用哪个、甚至一次用好几个。
# 这一版注释写得特别细,假设你是刚学编程的大学生。

import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# 从同目录的 .env 文件,把 DeepSeek 的钥匙读进来(和上一步完全一样)。
load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # .env 在项目根目录(上一层)

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# ① 工具"菜单":这次我们放【三个】工具。
#    tools 是一个【列表】(用 [] 包起来),里面每一项 {...} 就是一个工具的说明书。
#    模型会读每个工具的 description,自己判断你的问题该用哪个(或哪几个)。
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",                          # 工具1:查天气
            "description": "查询某个城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名,例如 北京、上海"},
                },
                "required": ["city"],                        # city 必填
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",                           # 工具2:做算术
            "description": "计算一个数学表达式的结果,例如 128+256、(15+27)*3",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式,例如 128+256"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "translate",                            # 工具3:翻译
            "description": "把一段文字翻译成指定语言",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要翻译的原文"},
                    "to_language": {"type": "string", "description": "目标语言,例如 英文、日文"},
                },
                "required": ["text", "to_language"],          # 这个工具需要两个参数
            },
        },
    },
]

# ② 提一个【需要用到两个工具】的问题,看模型会不会"一次点两单"。
#    想做实验?把下面这句换成别的问题,再跑一次(实验清单见对话里我给你的列表)。
question = "北京天气如何?再把'谢谢'翻译成英文，晚上好"
messages = [{"role": "user", "content": question}]

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=tools,
)
message = response.choices[0].message

print("你问的问题:", question)
print("停止原因(finish_reason):", response.choices[0].finish_reason)
print("=" * 50)

# ③ 看模型点了几单。
#    message.tool_calls 是一个【列表】:可能是空的(没点单)、1 个,也可能好几个。
if not message.tool_calls:
    print("模型没点单,直接回答了:", message.content)
else:
    print(f"模型一共点了 {len(message.tool_calls)} 单:\n")    # len() = 数一数列表里有几项
    # enumerate(..., start=1):一边遍历列表,一边给每项配个序号 i(从 1 开始)。
    for i, tc in enumerate(message.tool_calls, start=1):
        # tc.function.arguments 是 JSON 字符串,用 json.loads() 转成字典(dict)。
        args = json.loads(tc.function.arguments)
        print(f"第 {i} 单:")
        print(f"   工具名 : {tc.function.name}")
        print(f"   参数   : {args}   ← 这是一个 dict,可用 args['名字'] 取值")
        print(f"   取餐号 : {tc.id}   ← 第3步交结果时凭这个号对应")
        print()

print("=" * 50)
print("注意:模型只是【点单】,并没有真的查天气/算数/翻译。")
print("每一单都有自己的【取餐号(调用ID)】—— 第3步把结果交回去时,要凭号对应。")
