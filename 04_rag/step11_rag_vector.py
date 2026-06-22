# step11_rag_vector.py
# 第 11 步:把 RAG 的"检索"从【抠字面】升级成【按意思找】—— 向量检索。
#
# ======================================================================
# 和 step10 比,骨架【一模一样】(切块→检索→拼答→grounding→调模型),
# 只换了"检索"那一块:
#     step10  关键词重叠打分(抠字面)  → "七大维度"被挤到第 7,漏了
#     step11  向量余弦相似度(比意思)  → "七大维度"回到第 2,捞回来了
#
# 用的是【本地】向量模型 BAAI/bge-small-zh-v1.5(已下载缓存,之后离线秒开)。
# ★ 本地跑 embedding,正是"私有化部署"最常用的做法 —— 数据不出客户的门。
# ======================================================================

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"   # 关掉 Windows 上一条无害的缓存警告

import numpy
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


# ========== 配置(和 step10 一样,从根目录 .env 读)==========
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
api_key    = os.environ.get("DEEPSEEK_API_KEY")
base_url   = os.environ.get("BASE_URL")
model_name = os.environ.get("MODEL")
if not api_key or not base_url or not model_name:
    raise SystemExit("请检查根目录 .env:DEEPSEEK_API_KEY / BASE_URL / MODEL。")
client = OpenAI(api_key=api_key, base_url=base_url)


# ========== 加载本地向量模型 ==========
# 【RAG 概念:embedding 模型 = "把文字变成向量"的那个工具】
#   它读一段文字,吐出一串数字(向量),这串数字代表这段文字的【意思】。
#   意思相近的文字 → 向量也相近。这就是"按意思检索"的地基。
print("正在加载本地向量模型(已缓存,秒开)...")
embedding_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
print("向量模型就绪。\n")


# ======================================================================
# 第 ① 步:切块(和 step10 完全一样)
# ======================================================================
def split_into_chunks(full_text):
    """把长文本按行(段落)切成一块一块。"""
    chunks = []
    for line in full_text.split("\n"):
        cleaned_line = line.strip()
        if cleaned_line:
            chunks.append(cleaned_line)
    return chunks


# ======================================================================
# 第 ② 步:把每块转成向量(这就是真正的"建索引")
# ======================================================================
# 【RAG 概念:这一步 step10 是"啥也没干"(直接放列表);step11 才真正建了索引】
#   normalize_embeddings=True:把每个向量缩放成"长度为 1"。
#   好处:归一化之后,两个向量的【点积】正好等于【余弦相似度】,算起来最省事。
def embed_texts(list_of_texts):
    """把一批文字转成一批向量(已归一化)。返回一个 numpy 数组。"""
    return embedding_model.encode(list_of_texts, normalize_embeddings=True)


# ======================================================================
# 第 ③ 步:检索 —— 这次比的是"向量有多接近",不是"字面有多重叠"
# ======================================================================
# 【对比 step10】这个函数的【形状】和 step10 的 retrieve_top_chunks 一模一样:
#   都是"给每块算个相关分 → 排序 → 取前几名"。
#   唯一的不同:相关分从"数有几个字重叠"换成了"两个向量的余弦相似度"。
def retrieve_top_chunks(question, chunks, chunk_vectors, how_many=3):
    # 把【问题】也转成向量(注意:要和 chunk 用同一个模型转)
    question_vector = embedding_model.encode(question, normalize_embeddings=True)

    scored_chunks = []
    for index in range(len(chunks)):
        # 【RAG 概念:余弦相似度】
        #   两个【已归一化】向量的点积 = 余弦相似度,范围 -1~1,越接近 1 越像。
        #   numpy.dot(a, b) = 对应位置相乘再求和(就是"点积")。
        similarity = float(numpy.dot(chunk_vectors[index], question_vector))
        scored_chunks.append((similarity, chunks[index]))

    scored_chunks.sort(reverse=True)     # 元组默认按第一项(相似度)从大到小排
    return scored_chunks[:how_many]


# ======================================================================
# 主流程
# ======================================================================
if __name__ == "__main__":
    # ① 切块
    corpus_path = Path(__file__).resolve().parent / "corpus.txt"
    corpus_text = corpus_path.read_text(encoding="utf-8")
    chunks = split_into_chunks(corpus_text)

    # ② 建索引:把所有块一次性转成向量(只需建一次,之后反复用)
    print(f"正在为 {len(chunks)} 个片段建立向量索引...")
    chunk_vectors = embed_texts(chunks)
    print("索引建好了。\n")

    # —— 用 step10 答不好的那个问题,看向量检索能不能救回来 ——
    question = "这个平台能评测哪些安全维度?"
    print(f"你问:{question}\n")

    # ③ 检索(按意思)
    top_chunks = retrieve_top_chunks(question, chunks, chunk_vectors, how_many=3)
    print("检索到的相关片段(相似度越高越相关):")
    for similarity, chunk in top_chunks:
        preview = chunk[:48] + ("…" if len(chunk) > 48 else "")
        print(f"  [相似度 {similarity:.3f}] {preview}")
    print()

    # ④ 拼答 + grounding(这一段和 step10 一字不差)
    retrieved_context = "\n\n".join(chunk for similarity, chunk in top_chunks)
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
    print("模型的回答(基于向量检索到的资料):")
    print(response.choices[0].message.content)
