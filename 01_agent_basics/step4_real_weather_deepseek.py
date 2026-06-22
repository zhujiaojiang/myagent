# step4_real_weather_deepseek.py
# 第 4 步:把"假天气"换成【真·联网查询】,继续扛多步任务。
# 和第 3 步唯一的实质区别:get_weather 不再返回假数据,而是真的去网上查。
# 这一版注释写得很细,把 op / append / role 这些都解释清楚,文件本身就能当笔记看。

import os
import json
import urllib.request          # Python 自带的"联网"工具(不用额外安装),用来发 HTTP 请求
import urllib.parse            # 用来把"北京"这种中文,安全地塞进网址里
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # .env 在项目根目录(上一层)
client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://open.bigmodel.cn/api/paas/v4/")

# ========== 第一块:工具的"菜谱" —— 你自己写的真函数 ==========

def get_weather(city: str) -> str:
    """真·联网查天气。用 wttr.in 这个免费、不需要 API key 的天气服务。"""
    try:
        # ① 拼网址。urllib.parse.quote("北京") 把中文转成网址能识别的形式(%E5%8C%97...)。
        #    ?format=%C+%t 让它只返回"天气状况+气温"一小段;lang=zh 让状况用中文(晴/多云)。
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=%C+%t&lang=zh"

        # ② 造一个请求。带上 User-Agent 伪装成 curl,wttr.in 才会返回纯文本
        #    (否则它会以为是浏览器,给你一大堆网页 HTML)。
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})

        # ③ 真正发出请求、读回结果。timeout=10:最多等 10 秒,避免卡死。
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8").strip()   # 读回来是字节(bytes),decode 成中文字符串

        return f"{city}当前天气:{text}"
    except Exception as e:
        # 联网可能失败(断网、超时、城市名查不到)。
        # 工具要"优雅地报错",返回一句说明,而不是让整个程序崩掉。
        return f"查询 {city} 天气失败:{e}"


def calculate(a: float, b: float, op: str) -> str:
    """做一步四则运算(真算)。
    参数说明:
      a / b : 两个数(operand,运算数)
      op    : 运算符(operator 的缩写,所以叫 op),只能是 + - * / 之一
    注意:这个工具一次只能算【一步】。"128加256再乘以2"这种两步运算,
         模型会自动拆成两次调用(你在第 3 步已经亲眼见过了)。
    """
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
# tools 是给【模型】看的说明书:模型读 description 判断"何时该用",读 parameters 知道"参数怎么填"。
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某个城市的当前真实天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名,如 北京、上海"}},
                "required": ["city"],            # required:这个参数必须填
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
                    "a": {"type": "number", "description": "第一个数"},
                    "b": {"type": "number", "description": "第二个数"},
                    # enum 限定 op 只能是这四个【符号】之一。
                    # 所以你嘴上说"加",模型会自动翻译成 "+" 再填进来。
                    "op": {"type": "string", "enum": ["+", "-", "*", "/"], "description": "运算符"},
                },
                "required": ["a", "b", "op"],
            },
        },
    },
]

# 注册表:把"工具名(字符串)" 映射到 "真函数"。
# 模型点单时只给名字字符串 "get_weather",这张表帮我们把字符串换成真正能调用的函数。
available_tools = {
    "get_weather": get_weather,
    "calculate": calculate,
}


# ========== 第三块:agent 循环 —— 心脏 ==========
# messages 是"对话历史",一个【列表】。列表里每条消息都有两个字段:
#   role(谁说的): "user"=用户你 / "assistant"=模型 / "tool"=工具结果 / "system"=给模型的设定
#   content(说了什么内容)
# API 是无状态的(模型自己不记事),所以每一轮都要把这份完整历史重新发回去。
messages = [
    {"role": "user", "content": "北京天气怎么样?顺便帮我算一下 128 加 256 再乘以 2。"}
]

for turn in range(5):          # 最多循环 5 轮,防止万一陷入死循环
    print(f"\n—— 第 {turn + 1} 轮:把当前对话发给模型 ——")
    response = client.chat.completions.create(model="glm-4.7", messages=messages, tools=tools)
    message = response.choices[0].message

    # 情况 A:模型【没】点单 → 它给最终答复了 → 打印,结束循环。
    if not message.tool_calls:
        print("\n✅ 模型给出最终答复:")
        print(message.content)
        break

    # 情况 B:模型点单了 → 执行工具,把结果喂回去。

    # ① append = 往列表【末尾追加一项】。这里把模型刚说的"点单"消息加进历史。
    #    必须先加它:对话要连贯 —— 先有"我要调工具"的请求,后面才能跟上"工具结果"。
    messages.append(message)

    # ② 逐单执行(可能不止一单)。
    for tc in message.tool_calls:
        name = tc.function.name                       # 工具名(字符串),如 "get_weather"
        args = json.loads(tc.function.arguments)      # 参数:JSON 字符串 → 字典 dict
        print(f"   🔧 执行 {name},参数 {args}")

        func = available_tools[name]                  # 用名字从注册表里找到真函数
        result = func(**args)                         # **args:把 {'city':'北京'} 拆成 city='北京' 传进去
        print(f"      结果:{result}")

        # ③ 把结果作为一条 role="tool" 的消息,追加进历史,并贴上取餐号 tool_call_id(对号入座)。
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })
    # 本轮结束,带着工具结果回到循环顶部,再问模型一次。
else:
    # for 循环正常跑满 5 轮都没 break,才会执行这里(防死循环的兜底)。
    print("\n达到最大轮数,停止。")
