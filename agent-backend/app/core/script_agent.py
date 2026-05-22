"""LangChain 脚本生成 Agent"""

import json
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.prompts.templates import SCRIPT_GENERATION_PROMPT
from app.models import ProjectRequest


class ScriptAgent:
    """根据文档内容 + 用户需求 → 生成视频解说脚本"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0.7,
            request_timeout=120,  # 120s 超时，防止 API 卡死
        )

    async def generate(
        self,
        request: ProjectRequest,
        doc_context: str = "",
    ) -> str:
        prompt = ChatPromptTemplate.from_template(SCRIPT_GENERATION_PROMPT)

        chain = prompt | self.llm | StrOutputParser()

        script = await chain.ainvoke({
            "user_request": f"标题: {request.title}\n描述: {request.description}\n风格: {request.style_keywords}",
            "doc_context": doc_context or "（无文档参考，根据需求直接创作）",
            "total_duration": request.total_duration_seconds,
            "language": request.narration_language or "zh-CN",
            "scene_count": request.scene_count,
        })

        return script.strip()
