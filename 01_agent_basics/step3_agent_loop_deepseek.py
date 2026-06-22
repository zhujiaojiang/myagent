# step3_agent_loop_deepseek.py
# 第 3 步:agent 循环 —— agent 的"心脏"
# 流程:模型点单 → 你的代码真的执行工具 → 把结果喂回 → 模型给最终答复。
# 之所以是"循环",是因为模型拿到结果后,可能还要再点单,直到它觉得够了为止。

import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # .env 在项目根目录(上一层)
client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")


# ========== 第一块:工具的"菜谱" —— 你自己写的真函数 ==========
# 这就是上次说的:工具的真正实现,是你提前写好、放在本地的。模型永远拿不到这段代码。

def get_weather(city: str) -> str:
    """查天气。真实场景这里会去调天气 API;现在先返回假数据,把流程跑通。"""
    return f"{city}今天晴,气温 26°C,微风。(这是假数据)"

def calculate(a: float, b: float, op: str) -> str:
    """做四则运算。这个是【真算】的,不是假数据。"""
    if op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    elif op == "*":
        result = a * b
    elif op == "/":
        result = a / b
    else:
        return f"不支持的运算符:{op}"
    return f"{a} {op} {b} = {result}"


# ========== 第二块:工具"菜单"(给模型看的说明书)+ 注册表 ==========
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某个城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名,如 北京"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "做基础四则运算(加、减、乘、除)",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个数"},
                    "b": {"type": "number", "description": "第二个数"},
                    "op": {"type": "string", "enum": ["+", "-", "*", "/"], "description": "运算符"},
                },
                "required": ["a", "b", "op"],
            },
        },
    },
]

# "名字 → 真函数" 的对照表(注册表)。
# 模型点单时只给一个名字字符串 "get_weather",我们靠这张表把字符串变成真函数。
available_tools = {
    "get_weather": get_weather,
    "calculate": calculate,
}


# ========== 第三块:agent 循环 —— 心脏开始跳动 ==========
messages = [
    {"role": "user", "content": "北京天气怎么样?顺便帮我算一下 128 加 256再乘以 2。"}
]

# range(5):最多循环 5 轮,防止万一陷入死循环(这是个好习惯)。
for turn in range(5):
    print(f"\n—— 第 {turn + 1} 轮:把当前对话发给模型 ——")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
    )
    message = response.choices[0].message

    # 情况 A:模型【没有】点单 → 说明它已经给出最终答复,循环结束。
    if not message.tool_calls:
        print("\n✅ 模型给出最终答复:")
        print(message.content)
        break

    # 情况 B:模型点单了 → 执行工具,再把结果喂回去。

    # ① 关键一步:先把模型这条"点单"消息原样存进对话历史。
    #    不存的话,下一轮模型/接口会发现"有结果却没有对应的请求",直接报错。
    messages.append(message)

    # ② 逐单执行(可能不止一单)。
    for tc in message.tool_calls:
        name = tc.function.name                       # 工具名,如 "get_weather"
        args = json.loads(tc.function.arguments)      # 参数 dict,如 {"city": "北京"}
        print(f"   🔧 执行工具 {name},参数 {args}")

        func = available_tools[name]                  # 用名字从注册表里找到那个真函数
        result = func(**args)                         # 真正执行!**args 把字典拆成关键字参数
        print(f"      结果:{result}")                 #   例:get_weather(**{'city':'北京'}) == get_weather(city='北京')

        # ③ 把结果交回模型:role 必须写 "tool",并贴上取餐号 tool_call_id(对号入座)。
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })
    # 本轮结束,带着"工具结果"回到循环顶部,再问模型一次 → 它这次多半会给最终答复。
else:
    # for 循环正常跑满 5 轮都没 break,才会执行这里(防死循环兜底)。
    print("\n达到最大轮数,停止。")
