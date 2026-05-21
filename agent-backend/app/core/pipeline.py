"""LangChain 主流程编排器：串联整个视频制作流水线"""

import uuid
from pathlib import Path
from typing import Optional, Callable, Awaitable

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.models import ProjectRequest, VideoProject
from app.core.document_processor import extract_text
from app.core.script_agent import ScriptAgent
from app.core.scene_planner import ScenePlanner
from app.core.tts_service import VolcTTSService
from app.design_system.master import DesignSystem, parse_master_md, get_default_design_system


class VideoPipeline:
    """视频生成主流水线"""

    def __init__(self):
        self.script_agent = ScriptAgent()
        self.scene_planner = ScenePlanner()
        self.tts_service = VolcTTSService()

    async def run(
        self,
        request: ProjectRequest,
        document_paths: Optional[list[Path]] = None,
        design_system: Optional[DesignSystem] = None,
        tts_audio_path: Optional[Path] = None,
        generate_tts: bool = True,
        progress_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ) -> VideoProject:
        """执行完整的文档→视频流水线（含 TTS 语音合成）"""
        project_id = str(uuid.uuid4())[:8]

        async def _progress(step: str, msg: str):
            if progress_callback:
                await progress_callback(step, msg)

        # === Step 1: 文档提取 ===
        await _progress("extracting", "正在提取文档内容...")
        doc_context = ""
        if document_paths:
            all_texts = []
            for doc_path in document_paths:
                text = extract_text(doc_path)
                all_texts.append(text)
            doc_context = "\n\n=====\n\n".join(all_texts)

        # === Step 2: 使用默认或自定义设计系统 ===
        if design_system is None:
            design_system = get_default_design_system()

        # === Step 3: 生成脚本 ===
        await _progress("script", "AI 正在生成解说脚本...（约需 30-60 秒）")
        script = await self.script_agent.generate(
            request=request,
            doc_context=doc_context,
        )

        # === Step 4: 场景规划 + 设计注入 ===
        await _progress("scenes", "AI 正在规划视频场景...")
        scenes = await self.scene_planner.plan_scenes(
            script=script,
            request=request,
            design_system=design_system,
        )

        # === Step 5: TTS 语音合成（使用火山引擎 API，选用指定音色）===
        await _progress("tts", "正在合成语音配音...")
        audio_path = None
        if generate_tts and script.strip():
            try:
                audio_dir = settings.output_abs_path / "audio"
                audio_dir.mkdir(parents=True, exist_ok=True)
                tts_path = audio_dir / f"{project_id}_narration.mp3"
                tts = VolcTTSService(voice_type=request.voice_type)
                await tts.synthesize(script, tts_path)
                audio_path = str(tts_path)
            except Exception as e:
                # TTS 失败不阻塞整体流程
                print(f"[TTS Warning] Speech synthesis failed: {e}")

        # === Step 6: 构建返回结果 ===
        project = VideoProject(
            id=project_id,
            request=request,
            script=script,
            scenes=scenes,
            status="generated",
            audio_path=audio_path,
        )

        return project
