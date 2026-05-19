"""LangChain 场景规划 + 设计注入 Agent"""

import json
import re
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.prompts.templates import SCENE_PLAN_PROMPT, HTML_GENERATION_PROMPT, INDEX_HTML_COMPOSER_PROMPT
from app.models import ProjectRequest, ScenePlan
from app.design_system.master import DesignSystem


class ScenePlanner:
    """将脚本拆分为场景 + 注入设计系统"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0.5,
        )

    async def plan_scenes(
        self,
        script: str,
        request: ProjectRequest,
        design_system: DesignSystem,
    ) -> list[ScenePlan]:
        """将脚本划分为多个场景"""
        prompt = ChatPromptTemplate.from_template(SCENE_PLAN_PROMPT)

        result = await self.llm.ainvoke(
            prompt.format_messages(
                design_system=design_system.to_system_prompt(),
                script=script,
                user_request=(
                    f"标题: {request.title}\n"
                    f"描述: {request.description}\n"
                    f"风格: {request.style_keywords}"
                ),
                scene_count=request.scene_count,
            )
        )

        return self._parse_scenes(result.content, script)

    def _parse_scenes(self, content: str, script: str) -> list[ScenePlan]:
        """解析 LLM 返回的场景 JSON"""
        # 提取 JSON 数组
        json_match = re.search(r"\[.*?\]", content, re.DOTALL)
        if not json_match:
            # 兜底：按段落简单切分
            return self._fallback_split(script)

        try:
            data = json.loads(json_match.group())
            scenes = []
            for item in data:
                scenes.append(ScenePlan(
                    index=item["index"],
                    start_time=float(item["start_time"]),
                    duration=float(item["duration"]),
                    title=item["title"],
                    narration_text=item["narration_text"],
                    visual_style=item.get("visual_style", ""),
                    visual_keywords=item.get("visual_keywords", []),
                ))
            return scenes
        except (json.JSONDecodeError, KeyError) as e:
            return self._fallback_split(script)

    def _fallback_split(self, script: str) -> list[ScenePlan]:
        """兜底方案：按段落切分"""
        paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
        total = len(paragraphs)
        duration_per = 173 / total if total > 0 else 173

        scenes = []
        current_time = 0.0
        for i, para in enumerate(paragraphs):
            scenes.append(ScenePlan(
                index=i + 1,
                start_time=round(current_time, 1),
                duration=round(duration_per, 1),
                title=f"场景 {i + 1}",
                narration_text=para,
                visual_style="标准企业风格",
                visual_keywords=["corporate", "professional"],
            ))
            current_time += duration_per
        return scenes


class HTMLComposer:
    """为每个场景生成 HTML + 主 index.html"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0.3,
        )

    async def generate_scene_html(
        self,
        scene: ScenePlan,
        design_system: DesignSystem,
        composition_id: str,
    ) -> str:
        """生成单个场景的 HTML 文件"""
        prompt = ChatPromptTemplate.from_template(HTML_GENERATION_PROMPT)

        scene_info = (
            f"场景 {scene.index}: {scene.title}\n"
            f"时长: {scene.duration}s\n"
            f"解说词: {scene.narration_text}\n"
            f"视觉风格: {scene.visual_style}\n"
            f"视觉关键词: {', '.join(scene.visual_keywords)}"
        )

        result = await self.llm.ainvoke(
            prompt.format_messages(
                scene_info=scene_info,
                design_system=design_system.to_system_prompt(),
                composition_id=composition_id,
            )
        )

        return self._clean_html(result.content)

    async def compose_index_html(
        self,
        scenes: list[ScenePlan],
        design_system: DesignSystem,
        narration_audio_path: Optional[str] = None,
    ) -> str:
        """生成主 index.html"""
        prompt = ChatPromptTemplate.from_template(INDEX_HTML_COMPOSER_PROMPT)

        scenes_json = json.dumps(
            [s.model_dump() for s in scenes],
            ensure_ascii=False,
            indent=2,
        )

        result = await self.llm.ainvoke(
            prompt.format_messages(
                scenes_json=scenes_json,
                design_system=design_system.to_system_prompt(),
            )
        )

        return self._clean_html(result.content)

    @staticmethod
    def _clean_html(content: str) -> str:
        """清理 LLM 返回的 HTML（去掉 markdown 包裹）"""
        content = content.strip()
        # 去掉 ```html ... ```
        if content.startswith("```"):
            lines = content.split("\n")
            # 去掉第一行 ``` 和最后一行 ```
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        return content


from typing import Optional
