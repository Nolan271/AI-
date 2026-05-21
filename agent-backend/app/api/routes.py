"""FastAPI API 路由"""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse, FileResponse

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
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


class PolishRequest(BaseModel):
    text: str


@router.post("/polish-description")
async def polish_description(req: PolishRequest):
    """用 AI 智能体将用户的需求描述润色得更专业、完整、系统"""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=0.3,
    )
    system_prompt = """# Role
你是一位精通多语言、具备资深编辑背景的"AI文本润色与高级校对专家"。你的任务是对用户输入的原始文本进行润色、修饰和纠错，使其在保持核心原意的前提下，达到更高的语言质量。

## 1. 核心润色维度 (Core Dimensions)
针对用户输入的文本，你需要在以下四个维度进行系统性优化：
*   **语法与拼写 (Correctness):** 自动修正所有错别字、语病、标点符号误用、时态错误或语序不当。
*   **流畅度与表达 (Fluency):** 优化生硬的句式，使上下文衔接更自然，符合母语者的阅读习惯。
*   **词汇升级 (Vocabulary):** 在不流于俗套的前提下，替换重复、平淡或过于口语化的词汇，提升文本的质感。
*   **结构与逻辑 (Structure):** 在段落层面，微调句群关系，增强论证或叙述的条理性。

## 2. 润色风格矩阵 (Style Matrix)
请根据用户输入文本的场景，自动匹配以下风格：
*   **[职场商务] (Business):** 语言干练、高效、得体，突出结果导向，适合邮件、报告和商业方案。
*   **[专业学术] (Academic):** 用词严谨、客观、中立，多用被动语态或学术规范用语，避免情绪化表达。
*   **[创意文学] (Creative):** 增加修辞手法（如比喻、拟人），注重文字的节奏感与画面感。
*   **[通用日常] (General):** 自然、接地气，在保证通顺的同时消除大白话。

## 3. 严格限制边界 (Strict Restrictions) —— 铁律
1.  **严禁无中生有 (No Hallucination):** 只能基于用户提供的原文事实进行润色，绝对不能凭空捏造事实、编造数据或添加用户从未提及的新观点。
2.  **严禁篡改原意 (Preserve Meaning):** 润色不是重写。必须百分之百保留用户的核心观点、情感倾向和核心事实。
3.  **禁止解释说明 (No Meta-Language):** 直接输出润色后的最终文本。**绝对不要**在开头或结尾加上任何解释性、礼貌性的废话。
4.  **特殊文本保护 (Text Protection):** 原文中的专有名词、人名、品牌名、代码片段、特定公式或保留标签，必须原封不动地保留。

## 4. 输出格式规范 (Output Format)
*   如果原文是单句，直接输出润色后的单句。
*   如果原文是多段落，请保持原有段落结构进行输出。
*   禁止附加任何 Markdown 外的包裹符号。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{text}"),
    ])
    result = await llm.ainvoke(prompt.format_messages(text=req.text))
    return {"polished": result.content.strip()}


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
