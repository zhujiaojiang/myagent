# step10_rag_minimal.py
# 第 10 步:你的第一个 RAG(检索增强生成)—— 最小骨架版。
#
# ======================================================================
# RAG 四步,这个文件一步不少,但每步都用【最朴素】的做法,先看清骨架:
#   ① 切块   把 corpus.txt 切成一小段一小段
#   ② 存     这一版就放进一个列表(真 RAG 这步是"转向量、存向量库",step11 再上)
#   ③ 检索   用户提问 → 给每块打"相关分" → 挑最相关的几块
#   ④ 拼答   把"检索到的块 + 问题"一起给模型 → 模型据此回答
#
# ★ 关键体验:问题的答案,模型【本来不知道】(那是你的私有产品资料)。
#   它能答对,全靠第 ③ 步检索来的料。这就是 RAG。
#
# ★ 这一版的检索是"抠字面"的(关键词匹配),故意做得很朴素 ——
#   等你看清骨架,step11 再换成"按意思找"的向量检索。
# ======================================================================

import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv


# ========== 配置(和 step5/step9 一样,从根目录 .env 读)==========
load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # .env 在项目根目录(上两层)
api_key    = os.environ.get("DEEPSEEK_API_KEY")
base_url   = os.environ.get("BASE_URL")
model_name = os.environ.get("MODEL")
if not api_key or not base_url or not model_name:
    raise SystemExit("请检查根目录 .env:DEEPSEEK_API_KEY / BASE_URL / MODEL。")
client = OpenAI(api_key=api_key, base_url=base_url)


# ======================================================================
# 第 ① 步:切块(chunk)
# ======================================================================
# 【RAG 概念:为什么要切块?】
#   不能把整篇文档一股脑塞给模型——太长、费 token,而且"什么都给=等于没重点"。
#   所以先切成一小段一小段,检索时只挑出【和问题相关的那几段】塞给模型。
def split_into_chunks(full_text):
    """把一大段文本,按行(段落)切成一块一块,返回一个【列表】。"""
    chunks = []
    for line in full_text.split("\n"):   # split("\n") = 按换行符把长文本切成很多行
        cleaned_line = line.strip()      # 去掉行首尾空白
        if cleaned_line:                 # 跳过空行
            chunks.append(cleaned_line)
    return chunks
    # 说明:这是最朴素的切法(一行一块)。真实 RAG 会用更讲究的切法
    #       (定长 + 段落之间留重叠),以后再优化,现在先看骨架。


# ======================================================================
# 第 ③ 步:检索(retrieve)—— 给每块打"相关分",挑最高的几块
# ======================================================================
# 【Python 基础 + RAG 概念:怎么判断"一块和问题相关不相关"?】
#   最朴素的办法:看【字面重叠】。
#   把问题里每一组"相邻两个字"(如 "维度"、"评测"),拿去这块里找,
#   出现一次就 +1 分。重叠越多,越可能相关。
#   (中文没有空格分词,用"相邻两字"当关键词单位,简单又比单字靠谱。)
def relevance_score(question, chunk):
    """算问题和某一块的'相关分'。"""
    score = 0
    for index in range(len(question) - 1):
        two_chars = question[index:index + 2]   # 取相邻两个字,例:"维度"  【Python 基础:切片】
        if two_chars in chunk:                   # 这两个字在这块里出现吗  【Python 基础:in 判断包含】
            score += 1
    return score


def retrieve_top_chunks(question, chunks, how_many=3):
    """给所有块打分,返回分数最高的前 how_many 块。"""
    scored_chunks = []
    for chunk in chunks:
        score = relevance_score(question, chunk)
        if score > 0:                            # 完全不相关(0 分)的就不要了
            # 把"分数和块"打包成一个【元组 (score, chunk)】放进列表。 【Python 基础:元组=固定的一组值】
            scored_chunks.append((score, chunk))

    # 【Python 基础:给元组列表排序】
    #   元组默认【按第一个元素】比大小,这里第一个正好是分数。
    #   reverse=True = 从大到小。于是分数最高的排最前面。
    scored_chunks.sort(reverse=True)

    return scored_chunks[:how_many]              # 切片取前 how_many 个,返回 [(分数, 块), ...]


# ======================================================================
# 主流程
# ======================================================================
if __name__ == "__main__":
    # —— 先把语料读进来、切好块(① 切块)——
    corpus_path = Path(__file__).resolve().parent / "corpus.txt"   # 和本文件同目录
    corpus_text = corpus_path.read_text(encoding="utf-8")
    chunks = split_into_chunks(corpus_text)
    print(f"语料已切成 {len(chunks)} 块。\n")

    # —— 用户的问题 ——
    # (这一版朴素检索"抠字面",问"步骤"能稳稳命中那段;
    #  问"七大维度"反而会被一堆含"平台/评测"的段落挤掉 —— 那正是 step11 向量检索要解决的。)
    question = "大模型安全综合治理平台的评测分哪几个步骤?"
    print(f"你问:{question}\n")

    # —— ③ 检索:挑出最相关的几块 ——
    top_chunks = retrieve_top_chunks(question, chunks, how_many=3)
    print("检索到的相关片段(分数越高越相关):")
    for score, chunk in top_chunks:
        preview = chunk[:50] + ("…" if len(chunk) > 50 else "")
        print(f"  [相关分 {score}] {preview}")
    print()

    # —— ④ 拼答:把检索到的块当"参考资料",连同问题一起给模型 ——
    # 【RAG 概念:把检索结果拼进 prompt,这就是 "Augmented(增强)"】
    retrieved_context = "\n\n".join(chunk for score, chunk in top_chunks)

    # 【RAG 概念:接地(grounding)—— 防幻觉的关键一句】
    #   明确命令模型:只许根据【参考资料】回答;资料里没有就说没有,不准编。
    #   这正是你做售前最在意的"反幻觉"。
    system_prompt = (
        "你是严谨的产品助手。只能依据【参考资料】回答问题;"
        "参考资料里没有的内容,就回答'资料中未提及',绝对不要编造。"
    )
    user_prompt = f"【参考资料】\n{retrieved_context}\n\n【问题】\n{question}"

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    print("模型的回答(基于检索到的资料):")
    print(response.choices[0].message.content)
