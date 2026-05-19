"""FastAPI API 路由"""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.models import ProjectRequest, VideoProject
from app.core.pipeline import VideoPipeline
from app.core.document_processor import extract_text
from app.core.rag_service import rag_service
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
