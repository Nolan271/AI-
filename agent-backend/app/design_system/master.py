"""设计系统解析器：读取 MASTER.md 并结构化"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import re

from app.config import settings


@dataclass
class ColorPalette:
    primary: str = "#64748B"
    secondary: str = "#94A3B8"
    accent: str = "#F97316"
    background: str = "#F8FAFC"
    text: str = "#334155"

    def to_css_vars(self) -> str:
        return f"""--color-primary: {self.primary};
--color-secondary: {self.secondary};
--color-cta: {self.accent};
--color-background: {self.background};
--color-text: {self.text};"""


@dataclass
class Typography:
    heading_font: str = "Lexend"
    body_font: str = "Source Sans 3"
    mood: list[str] = field(default_factory=lambda: ["corporate", "professional", "clean"])


@dataclass
class DesignSystem:
    colors: ColorPalette = field(default_factory=ColorPalette)
    typography: Typography = field(default_factory=Typography)
    style_name: str = "Trust & Authority"
    style_keywords: list[str] = field(default_factory=list)
    antipatterns: list[str] = field(default_factory=list)
    raw_markdown: str = ""

    def to_system_prompt(self) -> str:
        """生成 LLM System Prompt 片段，让 AI 理解并使用此设计系统"""
        antipatterns_str = "\n".join(f"- ❌ {a}" for a in self.antipatterns) if self.antipatterns else "- 无特殊禁止项"
        keywords_str = ", ".join(self.style_keywords) if self.style_keywords else "corporate, professional"
        return f"""## 视频设计规范

### 配色方案
- 主色: {self.colors.primary} | 辅色: {self.colors.secondary}
- 强调色 (CTA): {self.colors.accent}
- 背景色: {self.colors.background} | 文字色: {self.colors.text}

### 字体
- 标题字体: {self.typography.heading_font}
- 正文字体: {self.typography.body_font}
- 风格气质: {', '.join(self.typography.mood)}

### 视觉风格
- 风格名称: {self.style_name}
- 关键词: {keywords_str}

### 禁止项
{antipatterns_str}"""


def parse_master_md(path: Path) -> DesignSystem:
    """解析 MASTER.md 文件为结构化 DesignSystem 对象"""
    if not path.exists():
        return DesignSystem()

    raw = path.read_text(encoding="utf-8")
    ds = DesignSystem(raw_markdown=raw)

    # 提取颜色
    color_map = {
        "Primary": "primary",
        "Secondary": "secondary",
        "CTA/Accent": "accent",
        "Background": "background",
        "Text": "text",
    }
    for name, attr in color_map.items():
        match = re.search(rf"\| {re.escape(name)}\s*\|\s*`([^`]+)`", raw)
        if match:
            setattr(ds.colors, attr, match.group(1))

    # 提取字体
    heading_match = re.search(r"\*\*Heading Font:\*\*\s*(.+)", raw)
    if heading_match:
        ds.typography.heading_font = heading_match.group(1).strip()

    body_match = re.search(r"\*\*Body Font:\*\*\s*(.+)", raw)
    if body_match:
        ds.typography.body_font = body_match.group(1).strip()

    mood_match = re.search(r"\*\*Mood:\*\*\s*(.+)", raw)
    if mood_match:
        ds.typography.mood = [m.strip() for m in mood_match.group(1).split(",")]

    # 提取风格
    style_match = re.search(r"\*\*Style:\*\*\s*(.+)", raw)
    if style_match:
        ds.style_name = style_match.group(1).strip()

    keywords_match = re.search(r"\*\*Keywords:\*\*(.+?)(?:\*\*|$)", raw, re.DOTALL)
    if keywords_match:
        ds.style_keywords = [k.strip() for k in keywords_match.group(1).split(",") if k.strip()]

    # 提取禁止项
    antipatterns = re.findall(r"❌\s*(.+)", raw)
    ds.antipatterns = [a.strip() for a in antipatterns]

    return ds


def get_default_design_system() -> DesignSystem:
    """获取默认设计系统（从 my-video/design-system/MASTER.md 读取）"""
    default_path = Path(settings.hyperframes_project_path) / "design-system" / "MASTER.md"
    return parse_master_md(default_path)
