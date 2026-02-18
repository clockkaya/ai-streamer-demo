import os
import faiss
import numpy as np
# ⚠️ 换成了新版的包名
from google import genai
from app.core.config import settings

# ⚠️ 新版 SDK 统一使用 Client 实例进行调用
client = genai.Client(api_key=settings.GEMINI_API_KEY)

class FAISSKnowledgeBase:
    def __init__(self):
        self.dimension = 3072
        self.index = faiss.IndexFlatL2(self.dimension)
        self.chunks = []  # 保存原始文本段落

    def _get_embedding(self, text: str) -> list:
        """调用 Gemini 接口将文字转换为向量"""
        # ⚠️ 新版 SDK 的调用方式发生改变
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
        )
        # ⚠️ 新版 SDK 提取向量值的路径变了
        return result.embeddings[0].values

    def load_corpus(self, file_path: str):
        if not os.path.exists(file_path):
            print(f"⚠️ 找不到知识库文件: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        raw_chunks = [c.strip() for c in content.split('\n\n') if c.strip()]

        if not raw_chunks:
            return

        embeddings = []
        for chunk in raw_chunks:
            self.chunks.append(chunk)
            embeddings.append(self._get_embedding(chunk))

        emb_matrix = np.array(embeddings, dtype=np.float32)
        self.index.add(emb_matrix)
        print(f"✅ RAG 知识库加载完成，共入库 {len(self.chunks)} 条独家设定！")

    def search(self, query: str, top_k: int = 1) -> str:
        if self.index.ntotal == 0:
            return ""

        q_emb = np.array([self._get_embedding(query)], dtype=np.float32)
        distances, indices = self.index.search(q_emb, top_k)

        results = []
        for idx in indices[0]:
            if idx != -1 and idx < len(self.chunks):
                results.append(self.chunks[idx])

        return "\n".join(results)

# 实例化单例
rag_store = FAISSKnowledgeBase()