# step1_hello.py
# 第 1 步:第一次"裸调" Claude API
# 目标:亲手感受一个核心事实 —— 大模型 = 一个函数:输入文字,输出文字。
#       它本身不会执行任何动作,只会"读进去文字,吐出来文字"。

import anthropic

# ① 创建客户端。
#    不传任何参数时,它会自动去读环境变量 ANTHROPIC_API_KEY。
#    这就是你和 Claude 之间的"电话线"——负责把请求用 HTTP 发出去、把回复收回来。
client = anthropic.Anthropic()

# ② 发起一次调用。这一行就是整个 agent 最底层的"原子操作"。
response = client.messages.create(
    model="claude-opus-4-8",     # 用哪个模型(改这个字符串就能换模型)
    max_tokens=1024,             # 最多让它生成多少 token(防止失控/超长)
    messages=[
        # messages 是"对话历史"。现在只有一句用户的话。
        # 注意:API 是无状态的——它不记得上一次说过什么,
        #       每次调用你都要把完整历史发过去(第 5 步我们会处理"记忆")。
        {"role": "user", "content": "用一句话解释:什么是 AI agent?"}
    ],
)

# ③ 取出回复。
#    关键认知:response.content 不是一个字符串,而是一个"内容块(block)"列表。
#    一次回复里可能有多个块(文字块、思考块、工具调用块……)。
#    现在只有文字块,我们把它打印出来。
for block in response.content:
    if block.type == "text":
        print(block.text)

# ④ 顺手看一眼这次花了多少 token —— 从第一天就建立成本意识。
print("-" * 40)
print(f"输入 token: {response.usage.input_tokens}  |  输出 token: {response.usage.output_tokens}")
print(f"本次停止原因(stop_reason): {response.stop_reason}")
