"""LangChain 场景规划 + 设计注入 Agent"""

import json
import re
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.prompts.templates import SCENE_PLAN_PROMPT
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
            request_timeout=120,  # 120s 超时
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
        json_match = re.search(r"\[.*\]", content, re.DOTALL)
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
                    template_type=item.get("template_type", "content_card"),
                ))
            return scenes
        except (json.JSONDecodeError, KeyError) as e:
            return self._fallback_split(script)

    def _fallback_split(self, script: str) -> list[ScenePlan]:
        """兜底方案：清理脚本文本后按段落切分"""
        # 去掉 markdown 表格、分隔线、| 字符等非正文内容
        cleaned = re.sub(r'\|.*?\|.*?\|', '', script, flags=re.DOTALL)
        # 去掉 | --- | --- | 类型的行
        cleaned = re.sub(r'\|[\s\-:]+\|', '', cleaned)
        # 去掉多余的竖线
        cleaned = cleaned.replace('|', '')
        # 去掉所有 markdown 标记符号
        cleaned = re.sub(r'\*\*|__|`|#+ ', '', cleaned)
        # 去掉行首的空白和编号（如 "1. "、"**场景一：**"）
        cleaned = re.sub(r'^\s*(?:[\d一二三四五六七八九十]+[\.、)]?\s*|场景[一二三四五六七八九十]+[：:]\s*)', '', cleaned, flags=re.MULTILINE)
        # 去掉空行
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()

        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        # 过滤掉太短（<15字）或明显是标题的行
        paragraphs = [p for p in paragraphs if len(p) > 15 and not p.startswith('---')]

        if not paragraphs:
            # 如果清理后没有段落，直接按原始脚本切句子
            sentences = re.split(r'[。！？\n]+', script)
            paragraphs = [s.strip() for s in sentences if len(s.strip()) > 20]

        total = len(paragraphs)
        if total == 0:
            # 极端兜底：固定 5 个默认场景
            paragraphs = ["开场白", "公司简介", "业务介绍", "企业文化", "未来展望"]
            total = 5

        # 按文本长度比例分配总时长（默认 173s）
        total_duration = 173.0
        total_chars = sum(len(p) for p in paragraphs)

        scenes = []
        current_time = 0.0
        for i, para in enumerate(paragraphs):
            if i == total - 1:
                duration = max(round(total_duration - current_time, 1), 3.0)
            else:
                raw = (len(para) / total_chars) * total_duration
                duration = max(round(raw, 1), 3.0)

            # 选择模板类型：首尾用 title_card / conclusion，中间用 content_card
            if i == 0:
                tt = "title_card"
            elif i == total - 1:
                tt = "conclusion"
            else:
                tt = "content_card"

            scenes.append(ScenePlan(
                index=i + 1,
                start_time=round(current_time, 1),
                duration=duration,
                title=f"场景 {i + 1}",
                narration_text=para,
                visual_style="标准企业风格",
                visual_keywords=["corporate", "professional"],
                template_type=tt,
            ))
            current_time += duration
        return scenes


class HTMLComposer:
    """使用固定模板渲染每个场景的 HTML（不调用 LLM）"""

    async def generate_scene_html(
        self,
        scene: ScenePlan,
        design_system: DesignSystem,
        composition_id: str,
    ) -> str:
        """使用模板系统渲染 HyperFrames 兼容的场景 HTML"""
        from app.core.scene_templates import render_scene_html
        return render_scene_html(scene, design_system, composition_id)


from typing import Optional
