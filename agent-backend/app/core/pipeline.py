"""LangChain 主流程编排器：串联整个视频制作流水线"""

import asyncio
import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional, Callable, Awaitable

logger = logging.getLogger("pipeline")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.models import ProjectRequest, VideoProject, ScenePlan
from app.core.document_processor import extract_text
from app.core.script_agent import ScriptAgent
from app.core.scene_planner import ScenePlanner, HTMLComposer
from app.core.tts_service import VolcTTSService
from app.core.audio_utils import get_audio_duration, compose_audio_video
from app.design_system.master import DesignSystem, parse_master_md, get_default_design_system

# 检测 npx 路径（HyperFrames 渲染依赖 Node.js/npx）
_NPX_PATH: Optional[str] = None
_npx_found = shutil.which("npx")
if _npx_found:
    _NPX_PATH = _npx_found
else:
    import warnings
    warnings.warn(
        "npx (Node.js) not found on PATH. HyperFrames video rendering will fail. "
        "Install Node.js from https://nodejs.org/"
    )


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
                # 截断每个文档到 8000 字，防止 LLM 请求过长导致超时
                if len(text) > 8000:
                    text = text[:8000] + "\n\n[文档过长，已截断...]"
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

        # === Step 5: TTS 语音合成（使用场景规划的解说词，清理后的纯文本）===
        await _progress("tts", "正在合成语音配音...")
        audio_path = None
        narration_text = ""
        if scenes:
            narration_text = " ".join(
                s.narration_text for s in scenes if s.narration_text.strip()
            )

        # 限制解说词长度以避免 TTS 音频超出预期时长
        # 中文语速约 3.5 字/秒，留 20% 余量
        if generate_tts and narration_text.strip():
            max_chars = int(request.total_duration_seconds * 3.5 * 1.2)
            if len(narration_text) > max_chars:
                truncated = narration_text[:max_chars] + "。"
                logger.info("Narration truncated: %d → %d chars (max %d for %ss)",
                            len(narration_text), len(truncated), max_chars, request.total_duration_seconds)
                narration_text = truncated

        if generate_tts and narration_text.strip():
            try:
                audio_dir = settings.output_abs_path / "audio"
                audio_dir.mkdir(parents=True, exist_ok=True)
                tts_path = audio_dir / f"{project_id}_narration.mp3"
                tts = VolcTTSService(voice_type=request.voice_type)
                await tts.synthesize(narration_text, tts_path)
                audio_path = str(tts_path)
            except Exception as e:
                err_msg = f"语音合成失败，将跳过配音: {e}"
                logger.warning("TTS failed: %s", e)
                await _progress("tts_warning", err_msg)

        # === Step 6: HTML 场景生成（AI 生成每个场景的视觉画面 + 主合成文件）===
        # 即使 TTS 失败，HTML 场景生成仍应继续
        await _progress("html", "AI 正在生成视频场景 HTML...")
        output_dir: Optional[Path] = None
        adjusted_scenes = scenes
        audio_duration = None

        if scenes:
            try:
                # 6a. 如果有音频，测量实际音频时长并调整场景时长
                if audio_path:
                    audio_duration = await get_audio_duration(Path(audio_path))
                    max_dur = float(request.total_duration_seconds) if request.total_duration_seconds else None
                    adjusted_scenes = _adjust_scene_timings(
                        scenes, audio_duration, max_duration=max_dur,
                    )

                # 6b. 创建输出目录
                output_dir = settings.output_abs_path / project_id
                output_dir.mkdir(parents=True, exist_ok=True)

                # 6c. 如果有音频，复制到 assets/
                if audio_path:
                    assets_dir = output_dir / "assets"
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(audio_path, assets_dir / "narration.mp3")

                # 6d. 创建 hyperframes.json
                _write_hyperframes_json(output_dir)

                # 6e. AI 生成每个场景的 HTML
                composer = HTMLComposer()
                compositions_dir = output_dir / "compositions"
                compositions_dir.mkdir(parents=True, exist_ok=True)

                for scene in adjusted_scenes:
                    await _progress("html", f"正在生成场景 {scene.index}/{len(adjusted_scenes)}: {scene.title}")
                    scene_html = await composer.generate_scene_html(
                        scene=scene,
                        design_system=design_system,
                        composition_id=f"scene{scene.index}",
                    )
                    (compositions_dir / f"scene{scene.index}.html").write_text(
                        scene_html, encoding="utf-8"
                    )

                # 6f. 生成主合成 index.html（固定模板，不使用 LLM，避免 HyperFrames 协议兼容问题）
                index_html = _build_index_html(adjusted_scenes, audio_duration)
                (output_dir / "index.html").write_text(index_html, encoding="utf-8")

            except Exception as e:
                err_msg = f"场景 HTML 生成失败: {e}"
                logger.error("HTML scene generation failed: %s", e, exc_info=True)
                await _progress("html_warning", err_msg)

        # === Step 7: HyperFrames 渲染（将 HTML → MP4 视频画面）===
        rendered_video: Optional[Path] = None
        if output_dir and (output_dir / "index.html").exists():
            await _progress("rendering", "正在渲染视频画面...（约需 1-3 分钟）")
            try:
                logger.info("Starting HyperFrames render in %s", output_dir)
                rendered_video = await self._run_hyperframes_render(output_dir)
                logger.info("Render completed: %s", rendered_video)
            except Exception as e:
                logger.error("HyperFrames render failed: %s", e, exc_info=True)

        # === Step 8: 音频 + 视频合成 ===
        final_video: Optional[str] = None
        if rendered_video and audio_path:
            await _progress("composing", "正在合成音频和视频...")
            try:
                final_output = output_dir / f"{project_id}_final.mp4"
                await compose_audio_video(rendered_video, Path(audio_path), final_output)
                final_video = str(final_output)
            except Exception as e:
                logger.error("Audio-video composition failed: %s", e, exc_info=True)

        # === Step 9: 构建返回结果 ===
        if final_video:
            status = "completed"
        elif rendered_video:
            status = "rendered"
        elif output_dir:
            status = "html_generated"
        else:
            status = "generated"

        project = VideoProject(
            id=project_id,
            request=request,
            script=script,
            scenes=adjusted_scenes,
            status=status,
            audio_path=audio_path,
            audio_duration=audio_duration,
            video_path=final_video,
            output_dir=str(output_dir.resolve()) if output_dir else None,
        )

        return project

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _run_hyperframes_render(output_dir: Path) -> Optional[Path]:
        """Run npx hyperframes render in the output directory.

        Uses create_subprocess_exec with cmd.exe /c on Windows to
        work around two constraints:
          1. shutil.which('npx') returns npx.CMD (a batch file, not a PE
             executable), so create_subprocess_exec can't run it directly.
          2. uv-managed Python's asyncio event loop raises NotImplementedError
             on create_subprocess_shell.
        """
        import sys as _sys
        if _NPX_PATH is None:
            raise RuntimeError(
                "npx not found. Install Node.js from https://nodejs.org/ "
                "and ensure it's on your PATH."
            )

        output_path = output_dir / "renders" / "output.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if _sys.platform == "win32":
            # Windows: cmd.exe 可以执行 .CMD 批处理文件，分开传参避免引号问题
            cmd = [
                "cmd.exe", "/c",
                "npx", "--yes", "hyperframes@0.6.25", "render", ".",
                "--output", str(output_path), "--no-audio",
            ]
        else:
            # Linux/Mac: npx 是可执行文件，直接 exec
            cmd = [
                "npx", "--yes", "hyperframes@0.6.25", "render", ".",
                "--output", str(output_path), "--no-audio",
            ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(output_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode('utf-8', errors='replace')[:2000]
        stderr_str = stderr.decode('utf-8', errors='replace')[:2000]
        logger.info("HyperFrames render stderr:\n%s", stderr_str)
        if proc.returncode != 0:
            raise RuntimeError(
                f"HyperFrames render failed (code {proc.returncode}): {stderr_str[:500]}"
            )

        renders_dir = output_dir / "renders"
        if renders_dir.exists():
            mp4_files = sorted(
                renders_dir.glob("*.mp4"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if mp4_files:
                return mp4_files[0]
        return None


# =========================================================================
# Module-level helpers
# =========================================================================


def _adjust_scene_timings(
    scenes: list[ScenePlan],
    audio_duration: float,
    max_duration: Optional[float] = None,
) -> list[ScenePlan]:
    """Scale scene durations proportionally by narration text length to match audio_duration.

    If max_duration is set, the effective duration is capped to min(audio_duration, max_duration).
    """
    effective_duration = audio_duration
    if max_duration is not None:
        effective_duration = min(audio_duration, max_duration)

    total_chars = sum(len(s.narration_text) for s in scenes)
    if total_chars == 0:
        return scenes
    current_time = 0.0
    adjusted = []
    for i, scene in enumerate(scenes):
        if i == len(scenes) - 1:
            duration = round(effective_duration - current_time, 1)
        else:
            raw_duration = (len(scene.narration_text) / total_chars) * effective_duration
            duration = round(raw_duration, 1)
        adjusted.append(ScenePlan(
            index=scene.index,
            start_time=round(current_time, 1),
            duration=max(duration, 1.0),
            title=scene.title,
            narration_text=scene.narration_text,
            visual_style=scene.visual_style,
            visual_keywords=scene.visual_keywords,
        ))
        current_time += duration
    return adjusted


def _write_hyperframes_json(output_dir: Path):
    """Write hyperframes.json project config."""
    config = {
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
        "paths": {
            "blocks": "compositions",
            "components": "compositions/components",
            "assets": "assets",
        },
    }
    (output_dir / "hyperframes.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )


def _build_index_html(scenes: list[ScenePlan], total_duration: float) -> str:
    """Build a HyperFrames-compatible index.html using a fixed template.

    Uses data-composition-src to reference per-scene composition files
    generated separately, avoiding the risk of LLM hallucinating
    HyperFrames protocol requirements.
    """
    scene_divs = []
    for s in scenes:
        scene_divs.append(
            f'    <div id="el-scene{s.index}" class="clip" '
            f'data-composition-src="compositions/scene{s.index}.html" '
            f'data-composition-id="scene{s.index}" '
            f'data-start="{s.start_time}" '
            f'data-duration="{s.duration}"></div>'
        )

    fade_duration = 0.5  # seconds for crossfade

    return (
        '<!doctype html>\n'
        '<html lang="zh-CN">\n'
        '<head>\n'
        '  <meta charset="UTF-8" />\n'
        '  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>\n'
        '  <style>\n'
        '    * { margin: 0; padding: 0; box-sizing: border-box; }\n'
        '    html, body {\n'
        '      margin: 0; width: 1920px; height: 1080px;\n'
        '      overflow: hidden;\n'
        '    }\n'
        '    .clip { position: absolute; inset: 0; }\n'
        '  </style>\n'
        '</head>\n'
        '<body>\n'
        f'<div id="root" data-composition-id="main" '
        f'data-start="0" data-duration="{total_duration}" '
        f'data-width="1920" data-height="1080">\n'
        '\n'
        f'  <div data-composition-id="narration" '
        f'data-start="0" data-duration="{total_duration}" class="clip">\n'
        f'    <audio src="assets/narration.mp3" '
        f'data-start="0" data-duration="{total_duration}"></audio>\n'
        '  </div>\n'
        '\n'
        + '\n'.join(scene_divs) + '\n'
        '\n'
        '</div>\n'
        '\n'
        '<script>\n'
        '  window.__timelines = window.__timelines || {};\n'
        '  window.__hf = {\n'
        f'    duration: {total_duration},\n'
        '    seek: function(t) {\n'
        '      var tl = window.__timelines["main"];\n'
        '      if (tl) tl.seek(t);\n'
        '    }\n'
        '  };\n'
        '\n'
        '  var tl = gsap.timeline({ paused: true });\n'
        '  tl.set(".clip", { opacity: 0 });\n'
        '\n'
        + ''.join(
            _scene_timeline_code(s, fade_duration)
            for s in scenes
        ) + '\n'
        '  window.__timelines["main"] = tl;\n'
        '</script>\n'
        '</body>\n'
        '</html>\n'
    )


def _scene_timeline_code(scene: ScenePlan, fade_duration: float) -> str:
    """Generate GSAP timeline entries for a single scene."""
    end = scene.start_time + scene.duration
    return (
        f'  tl.to("#el-scene{scene.index}", {{ opacity: 1, duration: {fade_duration} }}, {scene.start_time});\n'
        f'  tl.to("#el-scene{scene.index}", {{ opacity: 0, duration: {fade_duration} }}, {end - fade_duration});\n'
    )
