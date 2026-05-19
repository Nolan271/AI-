"""LangChain 主流程编排器：串联整个视频制作流水线"""

import uuid
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.models import ProjectRequest, VideoProject
from app.core.document_processor import extract_text
from app.core.rag_service import rag_service
from app.core.script_agent import ScriptAgent
from app.core.scene_planner import ScenePlanner, HTMLComposer
from app.core.render_service import RenderService
from app.design_system.master import DesignSystem, parse_master_md, get_default_design_system


class VideoPipeline:
    """视频生成主流水线"""

    def __init__(self):
        self.script_agent = ScriptAgent()
        self.scene_planner = ScenePlanner()
        self.html_composer = HTMLComposer()
        self.render_service = RenderService()

    async def run(
        self,
        request: ProjectRequest,
        document_paths: Optional[list[Path]] = None,
        design_system: Optional[DesignSystem] = None,
        tts_audio_path: Optional[Path] = None,
    ) -> VideoProject:
        """执行完整的文档→视频流水线"""
        project_id = str(uuid.uuid4())[:8]

        # === Step 1: 文档摄入 + RAG 索引 ===
        doc_context = ""
        if document_paths:
            all_texts = []
            for doc_path in document_paths:
                text = extract_text(doc_path)
                all_texts.append(text)
                # 写入向量库
                rag_service.index_document(text, source=doc_path.name)

            doc_context = "\n\n=====\n\n".join(all_texts)

        # === Step 2: 使用默认或自定义设计系统 ===
        if design_system is None:
            design_system = get_default_design_system()

        # === Step 3: 生成脚本 ===
        script = await self.script_agent.generate(
            request=request,
            doc_context=doc_context,
        )

        # === Step 4: 场景规划 + 设计注入 ===
        scenes = await self.scene_planner.plan_scenes(
            script=script,
            request=request,
            design_system=design_system,
        )

        # === Step 5: 生成 HTML（每场景 + 主文件）===
        scene_htmls = {}
        for scene in scenes:
            comp_id = f"scene{scene.index}"
            html = await self.html_composer.generate_scene_html(
                scene=scene,
                design_system=design_system,
                composition_id=comp_id,
            )
            scene_htmls[scene.index] = html

        index_html = await self.html_composer.compose_index_html(
            scenes=scenes,
            design_system=design_system,
            narration_audio_path=str(tts_audio_path) if tts_audio_path else None,
        )

        # === Step 6: 写入 HyperFrames 项目 ===
        written = await self.render_service.write_compositions(
            index_html=index_html,
            scene_htmls=scene_htmls,
        )

        # === Step 7: 触发渲染 ===
        render_result = await self.render_service.trigger_render()

        # === 构建返回结果 ===
        project = VideoProject(
            id=project_id,
            request=request,
            script=script,
            scenes=scenes,
            status="rendered" if render_result["success"] else "failed",
            output_path=render_result.get("video_path"),
        )

        # 若渲染成功，复制到 output 目录
        if render_result.get("video_path"):
            self.render_service.copy_to_output(render_result["video_path"])

        return project
