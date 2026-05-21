"""FastAPI API 路由"""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from app.models import ProjectRequest, VideoProject, ScenePlan
from app.core.pipeline import VideoPipeline
from app.core.document_processor import extract_text
from app.core.rag_service import rag_service
from app.core.tts_service import VolcTTSService, VOLC_VOICES, VOICE_CATEGORIES
from app.design_system.master import get_default_design_system, parse_master_md

router = APIRouter(prefix="/api/v1", tags=["video"])

# 内存中的项目状态（生产环境应使用数据库）
projects: dict[str, VideoProject] = {}
pipeline = VideoPipeline()


@router.post("/projects")
async def create_project(
    title: str = Form(...),
    description: str = Form(...),
    style_keywords: str = Form("corporate, professional, clean"),
    scene_count: int = Form(7),
    total_duration_seconds: int = Form(173),
    narration_language: str = Form("zh-CN"),
    voice_type: str = Form("zh_female_vv_jupiter_bigtts"),
    files: list[UploadFile] = File(default=None),
):
    """创建视频项目：上传文档 → AI 分析 → 生成视频"""
    request = ProjectRequest(
        title=title,
        description=description,
        style_keywords=style_keywords,
        scene_count=scene_count,
        total_duration_seconds=total_duration_seconds,
        narration_language=narration_language,
        voice_type=voice_type,
    )

    # 保存上传文件
    doc_paths = []
    if files:
        upload_dir = Path("./uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            file_path = upload_dir / f"{uuid.uuid4().hex}_{f.filename}"
            content = await f.read()
            file_path.write_bytes(content)
            doc_paths.append(file_path)

    try:
        project = await pipeline.run(
            request=request,
            document_paths=doc_paths or None,
        )
        projects[project.id] = project
        return project.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """获取项目状态和结果"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return projects[project_id].model_dump()


@router.get("/projects")
async def list_projects():
    """列出所有项目"""
    return [p.model_dump() for p in projects.values()]


@router.post("/projects/{project_id}/rerender")
async def rerender_project(project_id: str):
    """重新生成已生成的项目（仅重新运行 pipeline）"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects[project_id]
    project.status = "generating"

    try:
        new_project = await pipeline.run(request=project.request)
        project.script = new_project.script
        project.scenes = new_project.scenes
        project.status = "generated"
        return project.model_dump()
    except Exception as e:
        project.status = "failed"
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/design-system")
async def get_design_system():
    """获取当前默认设计系统信息"""
    ds = get_default_design_system()
    return {
        "colors": {
            "primary": ds.colors.primary,
            "secondary": ds.colors.secondary,
            "accent": ds.colors.accent,
            "background": ds.colors.background,
            "text": ds.colors.text,
        },
        "typography": {
            "heading_font": ds.typography.heading_font,
            "body_font": ds.typography.body_font,
            "mood": ds.typography.mood,
        },
        "style_name": ds.style_name,
        "style_keywords": ds.style_keywords,
    }


@router.get("/tts/voices")
async def list_tts_voices():
    """获取分组音色列表（供前端选择器使用）"""
    grouped = {}
    for category, names in VOICE_CATEGORIES.items():
        grouped[category] = [
            {"name": name, "id": VOLC_VOICES[name]}
            for name in names
        ]
    return grouped


@router.post("/tts/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice_type: str = Form("BV056_streaming"),
):
    """将文本合成为语音（火山引擎 TTS），返回音频文件"""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        svc = VolcTTSService(voice_type=voice_type)
        audio_dir = Path("./output/tts")
        audio_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex}_tts.mp3"
        audio_path = audio_dir / file_name
        await svc.synthesize(text, audio_path)
        return FileResponse(
            path=str(audio_path),
            media_type="audio/mpeg",
            filename=file_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/audio")
async def get_project_audio(project_id: str):
    """获取项目的 TTS 合成音频"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects[project_id]
    if not project.audio_path:
        raise HTTPException(status_code=404, detail="No audio generated for this project")

    audio_path = Path(project.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=f"{project_id}_narration.mp3",
    )
