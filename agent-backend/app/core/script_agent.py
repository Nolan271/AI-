"""LangChain 脚本生成 Agent"""

import json
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.prompts.templates import SCRIPT_GENERATION_PROMPT
from app.models import ProjectRequest
from app.core.rag_service import rag_service


class ScriptAgent:
    """根据文档内容 + 用户需求 → 生成视频解说脚本"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0.7,
        )

    async def generate(
        self,
        request: ProjectRequest,
        doc_context: str = "",
    ) -> str:
        prompt = ChatPromptTemplate.from_template(SCRIPT_GENERATION_PROMPT)

        # RAG 增强：从文档中检索相关内容
        rag_context = ""
        if doc_context:
            # 如果已经提供了上下文，直接用
            rag_context = doc_context
        else:
            # 尝试通过 RAG 获取相关上下文
            rag_context = rag_service.get_context(
                f"{request.title} {request.description}", k=5
            )

        chain = prompt | self.llm | StrOutputParser()

        script = await chain.ainvoke({
            "user_request": f"标题: {request.title}\n描述: {request.description}\n风格: {request.style_keywords}",
            "doc_context": rag_context or "（无文档参考，根据需求直接创作）",
            "total_duration": request.total_duration_seconds,
            "language": request.narration_language or "zh-CN",
            "scene_count": request.scene_count,
        })

        return script.strip()
