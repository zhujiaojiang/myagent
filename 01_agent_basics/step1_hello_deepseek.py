# step1_hello_deepseek.py
# 第 1 步(DeepSeek 版):第一次"裸调"大模型 API
# 目标:和 Claude 版一模一样 —— 感受"大模型 = 一个函数:输入文字,输出文字"。
#       对照着看,你会发现:换厂商只是换了"电话线",原理完全不变。

import os
from pathlib import Path
from openai import OpenAI            # DeepSeek 走 OpenAI 兼容接口,所以用 openai 这个库
from dotenv import load_dotenv      # 读取 .env 文件里的密钥

# ① 从同目录的 .env 文件,把密钥加载进环境变量。
#    好处:key 只存在 .env 里(已被 .gitignore 忽略),不进代码、不进命令历史,更安全。
load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # .env 在项目根目录(上一层)

api_key = os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit("没找到 DEEPSEEK_API_KEY —— 请在 myagent\\.env 文件里填好你的 key(见下方说明)。")

# ② 创建客户端。
#    关键区别:比 Claude 多一个 base_url —— 它告诉 openai 库:
#    "别连 OpenAI,改连 DeepSeek 的服务器。" 这就是那根"电话线"换了号码。
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",   # DeepSeek 的接口地址
)

# ③ 发起一次调用。这就是整个 agent 最底层的"原子操作"。
response = client.chat.completions.create(
    model="deepseek-chat",       # DeepSeek 的通用对话模型(改这个字符串就能换模型)
    max_tokens=1024,             # 最多生成多少 token
    messages=[
        # messages 同样是"对话历史"。API 一样是无状态的,
        # 每次都要把完整历史发过去(第 5 步我们会处理"记忆")。
        {"role": "user", "content": "用一句话解释:什么是 AI agent?"}
    ],
)

# ④ 取出回复。
#    和 Claude 的区别:这里回复直接就是一个字符串,放在 choices[0].message.content,
#    不像 Claude 那样是"块列表"。少了一层,但本质一样:把模型的话拿出来。
print(response.choices[0].message.content)

# ⑤ 看一眼成本(DeepSeek 用的字段名是 prompt_tokens / completion_tokens)。
print("-" * 40)
print(f"输入 token: {response.usage.prompt_tokens}  |  输出 token: {response.usage.completion_tokens}")
print(f"本次停止原因(finish_reason): {response.choices[0].finish_reason}")
