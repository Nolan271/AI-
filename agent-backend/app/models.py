from pydantic import BaseModel
from typing import Optional


class ProjectRequest(BaseModel):
    """用户提交的视频制作请求"""
    title: str
    description: str
    style_keywords: Optional[str] = "corporate, professional, clean"

    scene_count: Optional[int] = 7
    total_duration_seconds: Optional[int] = 173
    narration_language: Optional[str] = "zh-CN"

    design_system_path: Optional[str] = None  # 用户可自定义设计系统

    voice_type: str = "zh_female_vv_jupiter_bigtts"  # TTS 音色


class ScenePlan(BaseModel):
    """AI 生成的场景规划"""
    index: int
    start_time: float
    duration: float
    title: str
    narration_text: str
    visual_style: str
    visual_keywords: list[str]
    template_type: str = "content_card"
    # template_type: title_card | content_card | bullet_points | image_text | conclusion


class VideoProject(BaseModel):
    """完整的视频项目"""
    id: str
    request: ProjectRequest
    script: str
    scenes: list[ScenePlan]
    status: str = "pending"  # pending | generating | generated | html_generated | rendered | completed | failed
    audio_path: Optional[str] = None  # TTS 合成音频路径
    audio_duration: Optional[float] = None  # 实际音频时长（秒）
    video_path: Optional[str] = None  # 最终合成视频 MP4 路径
    output_dir: Optional[str] = None  # 项目输出目录
