# step6_streaming.py
# 第 6 步:流式输出(streaming)—— 让助手像打字机一样,一个字一个字往外蹦,
#          而不是憋半天再一次性吐出来。
# 这版【没有工具】,专门把"流式"这一个新概念讲清楚。对话循环你已经在 step5 熟过了。

import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# 配置照旧从 .env 读(和 step5 一样)。
load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # .env 在项目根目录(上一层)
api_key    = os.environ.get("DEEPSEEK_API_KEY")
base_url   = os.environ.get("BASE_URL")
model_name = os.environ.get("MODEL")
client = OpenAI(api_key=api_key, base_url=base_url)

system_prompt = "你是一个喜剧大师，请用幽默风趣的方式回答用户的问题。"
messages = [{"role": "system", "content": system_prompt}]

print("助手已就绪(流式版)!直接打字跟我聊。(输入 退出 结束)\n")

while True:
    user_input = input("你: ")
    if user_input.strip() in ("退出", "quit", "exit"):
        print("拜拜!")
        break

    messages.append({"role": "user", "content": user_input})

    # ★ 这一步唯一的新东西:stream=True。           【API 概念】
    #   不加它(step5 那样):模型把整段答复憋完,一次性返回 → 你要等。
    #   加了它:模型【一边生成、一边往回传】小碎片,我们收到一片就立刻打印一片。
    response_stream = client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=True,            # ← 打开"流式"开关
    )

    # end="" 表示打印后【不换行】;flush=True 表示【立刻显示、不要缓存】。 【Python 基础】
    # 这两个加在一起,才能做出"字一个个连续蹦出来"的效果。
    print("助手: ", end="", flush=True)

    full_reply = ""             # 一边流式打印,一边把碎片拼成【完整答复】(后面要存进历史)
    for chunk in response_stream:
        # response_stream 不是一段完整文字,而是【一串小碎片(chunk)】,要用 for 一片片取。
        # 每一片新增的文字,放在 chunk.choices[0].delta.content 里。
        # (delta = 增量;注意区别:step5 不流式时是 message.content = 一整段)
        piece = chunk.choices[0].delta.content

        # 有些碎片可能没有文字(比如开头/结尾只带元信息),所以先判断一下再打印。
        if piece:
            print(piece, end="", flush=True)   # 立刻打印这一小片(不换行、不缓存)→ 打字机效果
            full_reply += piece                # 同时把它拼进完整答复

    print("\n")                 # 这一段答复流完了,补一个换行,好看一点

    # 把【完整答复】存进历史(和 step5 一样:它才记得自己说过啥)。
    # 注意:流式模式下,我们是自己把碎片拼成 full_reply 再存的。
    messages.append({"role": "assistant", "content": full_reply})
