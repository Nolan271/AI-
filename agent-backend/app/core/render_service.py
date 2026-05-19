"""HyperFrames 渲染触发服务"""

import subprocess
import json
import shutil
from pathlib import Path
from typing import Optional

from app.config import settings


class RenderService:
    """管理 HyperFrames 视频渲染"""

    async def write_compositions(
        self,
        index_html: str,
        scene_htmls: dict[int, str],
        project_dir: Optional[Path] = None,
    ):
        """将生成的 HTML 写入 HyperFrames 项目目录"""
        if project_dir is None:
            project_dir = settings.hyperframes_abs_path

        # 写入 index.html
        index_path = project_dir / "index.html"
        index_path.write_text(index_html, encoding="utf-8")

        # 写入场景文件
        comp_dir = project_dir / "compositions"
        comp_dir.mkdir(parents=True, exist_ok=True)

        for scene_index, html_content in scene_htmls.items():
            scene_path = comp_dir / f"scene{scene_index}.html"
            scene_path.write_text(html_content, encoding="utf-8")

        return {
            "index": str(index_path),
            "scenes": [str(comp_dir / f"scene{i}.html") for i in sorted(scene_htmls.keys())],
        }

    async def trigger_render(self, project_dir: Optional[Path] = None) -> dict:
        """调用 HyperFrames CLI 执行渲染"""
        if project_dir is None:
            project_dir = settings.hyperframes_abs_path

        cmd = f'npx --yes hyperframes@0.6.20 render'

        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or result.stdout,
                "stdout": result.stdout,
            }

        # 查找渲染输出
        output_dir = project_dir / "renders" / "output"
        video_files = list(output_dir.glob("*.mp4")) if output_dir.exists() else []

        return {
            "success": True,
            "stdout": result.stdout,
            "video_path": str(video_files[0]) if video_files else None,
            "output_dir": str(output_dir),
        }

    def copy_to_output(self, video_path: str) -> str:
        """将渲染好的视频复制到 agent 的输出目录"""
        src = Path(video_path)
        dst = settings.output_abs_path / src.name
        shutil.copy2(str(src), str(dst))
        return str(dst)
