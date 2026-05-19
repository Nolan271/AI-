"""RAG 向量检索服务：文档分块 → 嵌入 → ChromaDB 存储与检索"""

from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from app.config import settings
from app.core.document_processor import chunk_text


class RAGService:
    def __init__(self, collection_name: str = "video_docs"):
        self.collection_name = collection_name
        self._vector_store: Optional[Chroma] = None
        self._embeddings: Optional[OpenAIEmbeddings] = None

    def _get_embeddings(self) -> OpenAIEmbeddings:
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                model=settings.embedding_model,
                openai_api_key=settings.openai_api_key,
                openai_api_base=settings.openai_base_url,
            )
        return self._embeddings

    def _get_vector_store(self) -> Chroma:
        if self._vector_store is None:
            persist_dir = Path(settings.chroma_persist_dir)
            persist_dir.mkdir(parents=True, exist_ok=True)

            self._vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self._get_embeddings(),
                persist_directory=str(persist_dir),
            )
        return self._vector_store

    def index_document(self, text: str, source: str) -> int:
        """将文档文本分块后写入向量库"""
        chunks = chunk_text(text)
        documents = [
            Document(
                page_content=chunk,
                metadata={"source": source, "chunk_index": i},
            )
            for i, chunk in enumerate(chunks)
        ]

        if not documents:
            return 0

        vector_store = self._get_vector_store()
        vector_store.add_documents(documents)
        return len(documents)

    def search(self, query: str, k: int = 5) -> list[Document]:
        """检索与查询最相关的文档段落"""
        vector_store = self._get_vector_store()
        results = vector_store.similarity_search(query, k=k)
        return results

    def get_context(self, query: str, k: int = 3) -> str:
        """检索并拼接成 LLM 友好的上下文文本"""
        docs = self.search(query, k=k)
        if not docs:
            return ""

        sections = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "unknown")
            sections.append(f"[来源: {source}]\n{doc.page_content}")

        return "\n\n---\n\n".join(sections)

    def clear(self):
        """清空当前集合"""
        vector_store = self._get_vector_store()
        vector_store.delete_collection()
        self._vector_store = None


# 全局单例
rag_service = RAGService()
