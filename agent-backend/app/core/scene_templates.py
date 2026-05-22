"""HyperFrames 场景模板 — 固定模板，LLM 只决定用哪个 + 填内容，Python 渲染 HTML"""

import re
from html import escape

from app.models import ScenePlan
from app.design_system.master import DesignSystem

__all__ = ["render_scene_html", "TEMPLATE_CHOICES"]


TEMPLATE_CHOICES = [
    {"id": "title_card",    "label": "标题卡",     "desc": "大标题居中展示，适合开场/章节过渡/结尾"},
    {"id": "content_card",  "label": "内容卡",     "desc": "正文内容卡片展示，适合作信息陈述场景"},
    {"id": "bullet_points", "label": "要点列表",   "desc": "关键点逐条动画展示，适合列举功能/步骤"},
    {"id": "image_text",    "label": "图文混排",   "desc": "装饰图形+文字左右布局，适合视觉化内容"},
    {"id": "conclusion",    "label": "结尾号召",   "desc": "总结语+行动号召，适合视频结尾"},
]

_BASE_ATTRS = 'data-width="1920" data-height="1080"'
_FADE = 0.5  # default crossfade duration


def render_scene_html(
    scene: ScenePlan,
    design_system: DesignSystem,
    composition_id: str,
) -> str:
    """根据 scene.template_type 选择并渲染对应模板，包装为完整 HTML 文档。"""
    renderer = _RENDERERS.get(scene.template_type, _render_content_card)
    body_fragment = renderer(scene, design_system, composition_id)
    return (
        '<!doctype html>\n'
        '<html lang="zh-CN">\n'
        '<head><meta charset="UTF-8" /></head>\n'
        '<body>\n'
        f'{body_fragment}\n'
        '</body>\n'
        '</html>'
    )


def _e(text: str) -> str:
    """HTML-escape text content."""
    return escape(text)


# =====================================================================
# Template renderers — each returns a <body>-style fragment.
# The root <div> is the first real element; <style> comes right after it.
# =====================================================================

def _render_title_card(
    scene: ScenePlan,
    ds: DesignSystem,
    cid: str,
) -> str:
    bg = ds.colors.background
    accent = ds.colors.accent
    text_c = ds.colors.text
    h_font = ds.typography.heading_font
    b_font = ds.typography.body_font
    sub = _e(scene.narration_text[:80]) if scene.narration_text else ""

    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        f"<style>\n"
        f".scene-{cid} {{ position:relative; width:1920px; height:1080px; overflow:hidden;\n"
        f"  background:linear-gradient(135deg, {bg} 0%, #ffffff 100%);\n"
        f"  font-family:'{b_font}','Noto Sans SC',sans-serif; display:flex; align-items:center; justify-content:center; }}\n"
        f".scene-{cid} .bg-accent {{ position:absolute; top:-120px; right:-120px; width:400px; height:400px;\n"
        f"  border-radius:50%; background:radial-gradient(circle, {accent}22 0%, transparent 70%); }}\n"
        f".scene-{cid} .bg-accent2 {{ position:absolute; bottom:-80px; left:-80px; width:300px; height:300px;\n"
        f"  border-radius:50%; background:radial-gradient(circle, {accent}11 0%, transparent 70%); }}\n"
        f".scene-{cid} .bg-line {{ position:absolute; top:0; left:0; width:100%; height:6px; background:{accent}; }}\n"
        f".scene-{cid} .content {{ position:relative; text-align:center; z-index:1; padding:60px; max-width:1400px; }}\n"
        f".scene-{cid} h1 {{ font-family:'{h_font}','Noto Sans SC',sans-serif; font-size:72px; font-weight:700;\n"
        f"  color:{text_c}; margin:0 0 24px; line-height:1.2; }}\n"
        f".scene-{cid} .sub {{ font-size:28px; color:{ds.colors.secondary}; font-weight:400; line-height:1.5; }}\n"
        f"</style>\n"
        f"  <div class=\"bg-line\"></div>\n"
        f"  <div class=\"bg-accent\"></div>\n"
        f"  <div class=\"bg-accent2\"></div>\n"
        f"  <div class=\"content\">\n"
        f"    <h1 class=\"el-title\">{_e(scene.title)}</h1>\n"
        f"    <p class=\"sub el-sub\">{sub}</p>\n"
        f"  </div>\n"
        f"</div>\n"
        f"</div>\n"
        f"<script>\n"
        f"window.__timelines = window.__timelines || {{}};\n"
        f"(function(){{\n"
        f"  var tl = gsap.timeline({{paused:true}});\n"
        f'  tl.from(".scene-{cid} .el-title", {{opacity:0, y:60, duration:0.8, ease:"power3.out"}});\n'
        f'  if(document.querySelector(".scene-{cid} .el-sub")){{\n'
        f'    tl.from(".scene-{cid} .el-sub", {{opacity:0, y:30, duration:0.6, ease:"power2.out"}},"-=0.3");\n'
        f"  }}\n"
        f'  window.__timelines["{cid}"] = tl;\n'
        f"}})();\n"
        f"</script>"
    )


def _render_content_card(
    scene: ScenePlan,
    ds: DesignSystem,
    cid: str,
) -> str:
    bg = ds.colors.background
    accent = ds.colors.accent
    text_c = ds.colors.text
    h_font = ds.typography.heading_font
    b_font = ds.typography.body_font

    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        f"<style>\n"
        f".scene-{cid} {{ position:relative; width:1920px; height:1080px; overflow:hidden;\n"
        f"  background:{bg}; font-family:'{b_font}','Noto Sans SC',sans-serif;\n"
        f"  display:flex; align-items:center; justify-content:center; padding:80px; }}\n"
        f".scene-{cid} .card {{ position:relative; width:100%; max-width:1400px; padding:60px 80px;\n"
        f"  background:#ffffff; border-radius:16px; box-shadow:0 4px 24px rgba(0,0,0,0.06); }}\n"
        f".scene-{cid} .card::before {{ content:''; position:absolute; top:0; left:0; width:6px; height:100%;\n"
        f"  background:{accent}; border-radius:16px 0 0 16px; }}\n"
        f".scene-{cid} h2 {{ font-family:'{h_font}','Noto Sans SC',sans-serif; font-size:36px; font-weight:600;\n"
        f"  color:{text_c}; margin:0 0 24px; }}\n"
        f".scene-{cid} .body {{ font-size:22px; line-height:1.8; color:{text_c}; white-space:pre-wrap; }}\n"
        f"</style>\n"
        f"  <div class=\"card\">\n"
        f"    <h2 class=\"el-head\">{_e(scene.title)}</h2>\n"
        f"    <div class=\"body el-body\">{_e(scene.narration_text)}</div>\n"
        f"  </div>\n"
        f"</div>\n"
        f"</div>\n"
        f"<script>\n"
        f"window.__timelines = window.__timelines || {{}};\n"
        f"(function(){{\n"
        f"  var tl = gsap.timeline({{paused:true}});\n"
        f'  tl.from(".scene-{cid} .card", {{opacity:0, y:40, duration:0.5, ease:"power2.out"}});\n'
        f'  tl.from(".scene-{cid} .el-head", {{opacity:0, y:20, duration:0.4, ease:"power2.out"}},"-=0.2");\n'
        f'  tl.from(".scene-{cid} .el-body", {{opacity:0, y:20, duration:0.5, ease:"power2.out"}},"-=0.1");\n'
        f'  window.__timelines["{cid}"] = tl;\n'
        f"}})();\n"
        f"</script>"
    )


def _render_bullet_points(
    scene: ScenePlan,
    ds: DesignSystem,
    cid: str,
) -> str:
    bg = ds.colors.background
    accent = ds.colors.accent
    text_c = ds.colors.text
    h_font = ds.typography.heading_font
    b_font = ds.typography.body_font

    raw = scene.narration_text
    items = [s.strip() for s in re.split(r'[。；\n]+', raw) if len(s.strip()) > 4]
    if not items:
        items = [raw[:60]]

    bullets = "\n".join(
        f'    <div class="item el-b{i}"><span class="dot"></span><span>{_e(item)}</span></div>'
        for i, item in enumerate(items)
    )
    anim_lines = "\n".join(
        f'  tl.from(".scene-{cid} .el-b{i}", {{opacity:0, x:-30, duration:0.35, ease:"power2.out"}},"-=0.15");'
        for i in range(len(items))
    )

    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        f"<style>\n"
        f".scene-{cid} {{ position:relative; width:1920px; height:1080px; overflow:hidden;\n"
        f"  background:{bg}; font-family:'{b_font}','Noto Sans SC',sans-serif;\n"
        f"  display:flex; align-items:center; justify-content:center; padding:80px 120px; }}\n"
        f".scene-{cid} .inner {{ width:100%; max-width:1300px; }}\n"
        f".scene-{cid} h2 {{ font-family:'{h_font}','Noto Sans SC',sans-serif; font-size:36px; font-weight:600;\n"
        f"  color:{text_c}; margin:0 0 40px; }}\n"
        f".scene-{cid} .item {{ display:flex; align-items:flex-start; gap:16px; margin-bottom:20px;\n"
        f"  font-size:22px; line-height:1.6; color:{text_c}; }}\n"
        f".scene-{cid} .dot {{ flex-shrink:0; width:12px; height:12px; margin-top:8px;\n"
        f"  border-radius:50%; background:{accent}; }}\n"
        f"</style>\n"
        f"  <div class=\"inner\">\n"
        f"    <h2 class=\"el-head\">{_e(scene.title)}</h2>\n"
        f"{bullets}\n"
        f"  </div>\n"
        f"</div>\n"
        f"</div>\n"
        f"<script>\n"
        f"window.__timelines = window.__timelines || {{}};\n"
        f"(function(){{\n"
        f"  var tl = gsap.timeline({{paused:true}});\n"
        f'  tl.from(".scene-{cid} .el-head", {{opacity:0, y:-20, duration:0.4, ease:"power2.out"}});\n'
        f"{anim_lines}\n"
        f'  window.__timelines["{cid}"] = tl;\n'
        f"}})();\n"
        f"</script>"
    )


def _render_image_text(
    scene: ScenePlan,
    ds: DesignSystem,
    cid: str,
) -> str:
    bg = ds.colors.background
    accent = ds.colors.accent
    primary = ds.colors.primary
    text_c = ds.colors.text
    h_font = ds.typography.heading_font
    b_font = ds.typography.body_font
    kw = " ".join(scene.visual_keywords) if scene.visual_keywords else "corporate"

    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        f"<style>\n"
        f".scene-{cid} {{ position:relative; width:1920px; height:1080px; overflow:hidden;\n"
        f"  background:{bg}; font-family:'{b_font}','Noto Sans SC',sans-serif; display:flex; }}\n"
        f".scene-{cid} .panel-left {{ flex:0 0 720px; background:linear-gradient(135deg, {primary} 0%, {accent} 100%);\n"
        f"  display:flex; align-items:center; justify-content:center; position:relative; overflow:hidden; }}\n"
        f".scene-{cid} .panel-left .deco {{ width:360px; height:360px; border-radius:50%; background:rgba(255,255,255,0.12); }}\n"
        f".scene-{cid} .panel-left .deco2 {{ position:absolute; width:200px; height:200px; border-radius:50%;\n"
        f"  background:rgba(255,255,255,0.08); top:15%; right:10%; }}\n"
        f".scene-{cid} .panel-left .deco3 {{ position:absolute; width:120px; height:120px; border-radius:50%;\n"
        f"  background:rgba(255,255,255,0.06); bottom:20%; left:15%; }}\n"
        f".scene-{cid} .panel-right {{ flex:1; padding:80px 80px 80px 60px; display:flex; flex-direction:column; justify-content:center; }}\n"
        f".scene-{cid} .panel-right h2 {{ font-family:'{h_font}','Noto Sans SC',sans-serif; font-size:36px; font-weight:600; color:{text_c}; margin:0 0 28px; }}\n"
        f".scene-{cid} .panel-right p {{ font-size:22px; line-height:1.8; color:{text_c}; white-space:pre-wrap; }}\n"
        f".scene-{cid} .kw-badge {{ display:inline-block; margin-bottom:16px; padding:6px 16px;\n"
        f"  background:{accent}18; color:{accent}; border-radius:20px; font-size:14px; font-weight:500; }}\n"
        f"</style>\n"
        f"  <div class=\"panel-left el-left\">\n"
        f"    <div class=\"deco\"></div>\n"
        f"    <div class=\"deco2\"></div>\n"
        f"    <div class=\"deco3\"></div>\n"
        f"  </div>\n"
        f"  <div class=\"panel-right el-right\">\n"
        f'    <span class="kw-badge">{_e(kw[:30])}</span>\n'
        f"    <h2>{_e(scene.title)}</h2>\n"
        f"    <p>{_e(scene.narration_text)}</p>\n"
        f"  </div>\n"
        f"</div>\n"
        f"</div>\n"
        f"<script>\n"
        f"window.__timelines = window.__timelines || {{}};\n"
        f"(function(){{\n"
        f"  var tl = gsap.timeline({{paused:true}});\n"
        f'  tl.from(".scene-{cid} .el-left", {{opacity:0, x:-100, duration:0.6, ease:"power3.out"}});\n'
        f'  tl.from(".scene-{cid} .el-right", {{opacity:0, x:60, duration:0.6, ease:"power3.out"}},"-=0.3");\n'
        f'  window.__timelines["{cid}"] = tl;\n'
        f"}})();\n"
        f"</script>"
    )


def _render_conclusion(
    scene: ScenePlan,
    ds: DesignSystem,
    cid: str,
) -> str:
    bg = ds.colors.background
    accent = ds.colors.accent
    text_c = ds.colors.text
    h_font = ds.typography.heading_font
    b_font = ds.typography.body_font
    body = _e(scene.narration_text[:120]) if scene.narration_text else ""

    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        f"<style>\n"
        f".scene-{cid} {{ position:relative; width:1920px; height:1080px; overflow:hidden;\n"
        f"  background:linear-gradient(135deg, {bg} 0%, #ffffff 100%);\n"
        f"  font-family:'{b_font}','Noto Sans SC',sans-serif;\n"
        f"  display:flex; align-items:center; justify-content:center; text-align:center; padding:80px; }}\n"
        f".scene-{cid} .bg-bar {{ position:absolute; bottom:0; left:0; width:100%; height:8px;\n"
        f"  background:linear-gradient(90deg, {accent}, {ds.colors.primary}, {accent}); }}\n"
        f".scene-{cid} .content {{ position:relative; z-index:1; max-width:1300px; }}\n"
        f".scene-{cid} .badge {{ display:inline-block; padding:8px 24px; margin-bottom:32px;\n"
        f"  background:{accent}; color:#fff; border-radius:24px; font-size:16px; font-weight:600; }}\n"
        f".scene-{cid} h1 {{ font-family:'{h_font}','Noto Sans SC',sans-serif; font-size:64px; font-weight:700;\n"
        f"  color:{text_c}; margin:0 0 24px; line-height:1.2; }}\n"
        f".scene-{cid} .body {{ font-size:28px; color:{ds.colors.secondary}; line-height:1.6; margin-bottom:40px; }}\n"
        f".scene-{cid} .cta {{ display:inline-block; padding:16px 48px; background:{accent}; color:#fff;\n"
        f"  font-size:22px; font-weight:600; border-radius:12px; letter-spacing:2px; }}\n"
        f"</style>\n"
        f"  <div class=\"bg-bar\"></div>\n"
        f"  <div class=\"content\">\n"
        f'    <div class="badge el-badge">&#x603B;&#x7ED3;</div>\n'
        f"    <h1 class=\"el-title\">{_e(scene.title)}</h1>\n"
        f"    <div class=\"body el-body\">{body}</div>\n"
        f'    <div class="cta el-cta">&#x7ACB;&#x5373;&#x884C;&#x52A8;</div>\n'
        f"  </div>\n"
        f"</div>\n"
        f"</div>\n"
        f"<script>\n"
        f"window.__timelines = window.__timelines || {{}};\n"
        f"(function(){{\n"
        f"  var tl = gsap.timeline({{paused:true}});\n"
        f'  tl.from(".scene-{cid} .el-badge", {{opacity:0, y:-20, duration:0.4, ease:"power2.out"}});\n'
        f'  tl.from(".scene-{cid} .el-title", {{opacity:0, scale:0.8, duration:0.6, ease:"back.out(1.7)"}},"-=0.2");\n'
        f'  tl.from(".scene-{cid} .el-body", {{opacity:0, y:30, duration:0.5, ease:"power2.out"}},"-=0.2");\n'
        f'  tl.from(".scene-{cid} .el-cta", {{opacity:0, y:20, duration:0.4, ease:"power2.out"}},"-=0.1");\n'
        f'  window.__timelines["{cid}"] = tl;\n'
        f"}})();\n"
        f"</script>"
    )


_RENDERERS = {
    "title_card": _render_title_card,
    "content_card": _render_content_card,
    "bullet_points": _render_bullet_points,
    "image_text": _render_image_text,
    "conclusion": _render_conclusion,
}
