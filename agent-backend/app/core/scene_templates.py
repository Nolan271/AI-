"""HyperFrames scene templates.

The LLM only chooses a template and fills scene content. This module renders
stable, video-friendly HTML/CSS for knowledge explainer scenes.
"""

import re
from html import escape

from app.models import ScenePlan
from app.design_system.master import DesignSystem

__all__ = ["render_scene_html", "TEMPLATE_CHOICES"]


TEMPLATE_CHOICES = [
    {"id": "title_card", "label": "标题开场", "desc": "大标题开场，适合引入主题、章节过渡"},
    {"id": "content_card", "label": "知识卡片", "desc": "重点概念解释，适合承载正文与关键结论"},
    {"id": "bullet_points", "label": "要点列表", "desc": "逐条展示关键点、步骤、原因或方法"},
    {"id": "image_text", "label": "图文解释", "desc": "左侧抽象图形，右侧解释文本，适合视觉化说明"},
    {"id": "conclusion", "label": "总结收束", "desc": "结尾总结、行动建议或核心记忆点"},
]

_BASE_ATTRS = 'data-width="1920" data-height="1080"'


def render_scene_html(
    scene: ScenePlan,
    design_system: DesignSystem,
    composition_id: str,
) -> str:
    """Render one scene as a complete HyperFrames composition document."""
    renderer = _RENDERERS.get(scene.template_type, _render_content_card)
    body_fragment = renderer(scene, design_system, composition_id)
    return (
        '<!doctype html>\n'
        '<html lang="zh-CN">\n'
        '<head>\n'
        '  <meta charset="UTF-8" />\n'
        '  <style>html,body{margin:0;width:1920px;height:1080px;overflow:hidden;}</style>\n'
        '</head>\n'
        '<body>\n'
        f'{body_fragment}\n'
        '</body>\n'
        '</html>'
    )


def _e(text: str) -> str:
    return escape(text or "")


def _short(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def _split_sentences(text: str, limit: int = 5) -> list[str]:
    parts = [s.strip() for s in re.split(r"[。；;！!？?\n]+", text or "") if s.strip()]
    if not parts and text:
        parts = [text.strip()]
    return parts[:limit]


def _keywords(scene: ScenePlan, fallback: str = "知识科普") -> list[str]:
    words = [w.strip() for w in (scene.visual_keywords or []) if w and w.strip()]
    if not words:
        words = [fallback]
    return words[:4]


def _keyword_badges(words: list[str], class_name: str = "tag") -> str:
    return "\n".join(f'      <span class="{class_name}">{_e(_short(word, 12))}</span>' for word in words)


def _common_css(cid: str, ds: DesignSystem) -> str:
    bg = ds.colors.background
    primary = ds.colors.primary
    secondary = ds.colors.secondary
    accent = ds.colors.accent
    text_c = ds.colors.text
    h_font = ds.typography.heading_font
    b_font = ds.typography.body_font
    return (
        f".scene-{cid} {{ position:relative; width:1920px; height:1080px; overflow:hidden;\n"
        f"  color:{text_c}; background:{bg}; font-family:'{b_font}','Noto Sans SC',sans-serif;\n"
        f"  box-sizing:border-box; isolation:isolate; }}\n"
        f".scene-{cid} * {{ box-sizing:border-box; }}\n"
        f".scene-{cid} .stage-bg {{ position:absolute; inset:0; z-index:-3;\n"
        f"  background:\n"
        f"    linear-gradient(120deg, {bg} 0%, #ffffff 42%, {secondary}18 100%),\n"
        f"    radial-gradient(circle at 16% 18%, {accent}24 0, transparent 30%),\n"
        f"    radial-gradient(circle at 88% 76%, {primary}22 0, transparent 34%); }}\n"
        f".scene-{cid} .grid {{ position:absolute; inset:0; z-index:-2; opacity:.45;\n"
        f"  background-image:linear-gradient({text_c}0d 1px, transparent 1px), linear-gradient(90deg, {text_c}0d 1px, transparent 1px);\n"
        f"  background-size:64px 64px; mask-image:linear-gradient(90deg, transparent, #000 18%, #000 82%, transparent); }}\n"
        f".scene-{cid} .grain {{ position:absolute; inset:0; z-index:-1; opacity:.22;\n"
        f"  background-image:repeating-linear-gradient(135deg, #00000008 0 1px, transparent 1px 7px); }}\n"
        f".scene-{cid} .kicker {{ display:flex; align-items:center; gap:12px; color:{accent}; font-size:24px; font-weight:700; letter-spacing:0; }}\n"
        f".scene-{cid} .kicker::before {{ content:''; width:42px; height:4px; border-radius:999px; background:{accent}; }}\n"
        f".scene-{cid} .tag {{ display:inline-flex; align-items:center; height:38px; padding:0 18px; border-radius:999px;\n"
        f"  background:{accent}14; border:1px solid {accent}35; color:{accent}; font-size:18px; font-weight:700; }}\n"
        f".scene-{cid} .eyebrow {{ color:{secondary}; font-size:18px; font-weight:700; text-transform:uppercase; letter-spacing:0; }}\n"
        f".scene-{cid} h1, .scene-{cid} h2 {{ font-family:'{h_font}','Noto Sans SC',sans-serif; letter-spacing:0; }}\n"
        f".scene-{cid} .hairline {{ height:1px; background:linear-gradient(90deg, transparent, {text_c}20, transparent); }}\n"
    )


def _script(cid: str, lines: list[str]) -> str:
    return (
        "<script>\n"
        "window.__timelines = window.__timelines || {};\n"
        "(function(){\n"
        "  if (!window.gsap) {\n"
        f'    window.__timelines["{cid}"] = {{ seek: function(){{}} }};\n'
        "    return;\n"
        "  }\n"
        "  var tl = gsap.timeline({paused:true});\n"
        + "\n".join(lines)
        + "\n"
        f'  window.__timelines["{cid}"] = tl;\n'
        "})();\n"
        "</script>"
    )


def _render_title_card(scene: ScenePlan, ds: DesignSystem, cid: str) -> str:
    words = _keyword_badges(_keywords(scene))
    sub = _e(_short(scene.narration_text, 110))
    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        "<style>\n"
        f"{_common_css(cid, ds)}"
        f".scene-{cid} {{ display:grid; place-items:center; padding:92px 120px; }}\n"
        f".scene-{cid} .halo {{ position:absolute; width:780px; height:780px; border-radius:50%; right:-170px; top:-210px;\n"
        f"  border:1px solid {ds.colors.accent}30; background:radial-gradient(circle, {ds.colors.accent}18, transparent 62%); }}\n"
        f".scene-{cid} .orbit {{ position:absolute; width:520px; height:520px; border-radius:50%; left:96px; bottom:88px;\n"
        f"  border:2px dashed {ds.colors.primary}2e; }}\n"
        f".scene-{cid} .content {{ width:1500px; position:relative; z-index:1; }}\n"
        f".scene-{cid} .chapter {{ display:grid; grid-template-columns:210px 1fr; gap:56px; align-items:start; }}\n"
        f".scene-{cid} .num {{ font-family:'{ds.typography.heading_font}','Noto Sans SC',sans-serif; font-size:124px; line-height:.86;\n"
        f"  color:{ds.colors.accent}; font-weight:800; }}\n"
        f".scene-{cid} .label {{ margin-top:24px; color:{ds.colors.secondary}; font-size:22px; font-weight:700; }}\n"
        f".scene-{cid} h1 {{ margin:0; font-size:86px; line-height:1.08; font-weight:800; color:{ds.colors.text}; max-width:1180px; }}\n"
        f".scene-{cid} .sub {{ margin-top:34px; width:1060px; font-size:30px; line-height:1.55; color:{ds.colors.secondary}; }}\n"
        f".scene-{cid} .tags {{ display:flex; flex-wrap:wrap; gap:14px; margin-top:44px; }}\n"
        f".scene-{cid} .footer {{ position:absolute; left:120px; right:120px; bottom:72px; display:flex; justify-content:space-between; align-items:center;\n"
        f"  color:{ds.colors.secondary}; font-size:18px; font-weight:700; }}\n"
        "</style>\n"
        '  <div class="stage-bg"></div><div class="grid"></div><div class="grain"></div>\n'
        '  <div class="halo el-halo"></div><div class="orbit el-orbit"></div>\n'
        '  <main class="content">\n'
        '    <div class="chapter">\n'
        f'      <aside><div class="num el-num">{scene.index:02d}</div><div class="label el-label">EXPLAINER</div></aside>\n'
        '      <section>\n'
        f'        <div class="kicker el-kicker">本节主题</div>\n'
        f'        <h1 class="el-title">{_e(scene.title)}</h1>\n'
        f'        <p class="sub el-sub">{sub}</p>\n'
        f'        <div class="tags el-tags">\n{words}\n        </div>\n'
        '      </section>\n'
        '    </div>\n'
        '  </main>\n'
        f'  <div class="footer el-footer"><span>KNOWLEDGE NOTES</span><span>{_e(ds.style_name)}</span></div>\n'
        "</div>\n"
        "</div>\n"
        + _script(cid, [
            f'  tl.from(".scene-{cid} .el-halo", {{opacity:0, scale:.82, duration:.7, ease:"power2.out"}});',
            f'  tl.from(".scene-{cid} .el-orbit", {{opacity:0, rotate:-20, duration:.7, ease:"power2.out"}},"-=.55");',
            f'  tl.from(".scene-{cid} .el-num", {{opacity:0, y:44, duration:.55, ease:"power3.out"}},"-=.45");',
            f'  tl.from(".scene-{cid} .el-kicker", {{opacity:0, x:-26, duration:.45, ease:"power2.out"}},"-=.3");',
            f'  tl.from(".scene-{cid} .el-title", {{opacity:0, y:56, duration:.75, ease:"power3.out"}},"-=.2");',
            f'  tl.from(".scene-{cid} .el-sub", {{opacity:0, y:26, duration:.5, ease:"power2.out"}},"-=.35");',
            f'  tl.from(".scene-{cid} .el-tags .tag", {{opacity:0, y:18, stagger:.08, duration:.35, ease:"power2.out"}},"-=.25");',
            f'  tl.from(".scene-{cid} .el-footer", {{opacity:0, y:16, duration:.4, ease:"power2.out"}},"-=.2");',
        ])
    )


def _render_content_card(scene: ScenePlan, ds: DesignSystem, cid: str) -> str:
    body = _e(scene.narration_text)
    words = _keyword_badges(_keywords(scene))
    summary = _e(_short(scene.narration_text, 52))
    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        "<style>\n"
        f"{_common_css(cid, ds)}"
        f".scene-{cid} {{ display:grid; grid-template-columns:420px 1fr; gap:54px; padding:86px 110px; align-items:stretch; }}\n"
        f".scene-{cid} .side {{ border-right:1px solid {ds.colors.text}18; padding-right:44px; display:flex; flex-direction:column; justify-content:space-between; }}\n"
        f".scene-{cid} .index {{ font-family:'{ds.typography.heading_font}','Noto Sans SC',sans-serif; font-size:92px; line-height:1; color:{ds.colors.accent}; font-weight:800; }}\n"
        f".scene-{cid} .mini {{ margin-top:24px; font-size:23px; line-height:1.5; color:{ds.colors.secondary}; }}\n"
        f".scene-{cid} .meter {{ height:10px; border-radius:999px; background:{ds.colors.text}12; overflow:hidden; margin-top:30px; }}\n"
        f".scene-{cid} .meter span {{ display:block; width:68%; height:100%; border-radius:999px; background:linear-gradient(90deg,{ds.colors.primary},{ds.colors.accent}); }}\n"
        f".scene-{cid} .card {{ position:relative; align-self:center; padding:64px 72px 58px; border-radius:8px;\n"
        f"  background:rgba(255,255,255,.88); border:1px solid {ds.colors.text}12; box-shadow:0 24px 80px rgba(15,23,42,.12); }}\n"
        f".scene-{cid} .card::before {{ content:''; position:absolute; inset:0 auto 0 0; width:10px; background:linear-gradient(180deg,{ds.colors.accent},{ds.colors.primary}); border-radius:8px 0 0 8px; }}\n"
        f".scene-{cid} h2 {{ margin:0; color:{ds.colors.text}; font-size:50px; line-height:1.18; font-weight:800; }}\n"
        f".scene-{cid} .body {{ margin-top:30px; font-size:27px; line-height:1.72; color:{ds.colors.text}; white-space:pre-wrap; }}\n"
        f".scene-{cid} .tags {{ display:flex; flex-wrap:wrap; gap:12px; margin-top:34px; }}\n"
        f".scene-{cid} .note {{ margin-top:38px; padding:22px 28px; border-radius:8px; background:{ds.colors.accent}12; border:1px solid {ds.colors.accent}28;\n"
        f"  color:{ds.colors.text}; font-size:22px; line-height:1.45; font-weight:700; }}\n"
        "</style>\n"
        '  <div class="stage-bg"></div><div class="grid"></div><div class="grain"></div>\n'
        '  <aside class="side el-side">\n'
        '    <div>\n'
        f'      <div class="eyebrow">Concept</div><div class="index">{scene.index:02d}</div>\n'
        f'      <div class="mini">{summary}</div><div class="meter"><span></span></div>\n'
        '    </div>\n'
        f'    <div class="tags">\n{words}\n    </div>\n'
        '  </aside>\n'
        '  <main class="card el-card">\n'
        f'    <div class="kicker el-kicker">核心概念</div>\n'
        f'    <h2 class="el-head">{_e(scene.title)}</h2>\n'
        f'    <div class="body el-body">{body}</div>\n'
        f'    <div class="note el-note">记忆点：{summary}</div>\n'
        '  </main>\n'
        "</div>\n"
        "</div>\n"
        + _script(cid, [
            f'  tl.from(".scene-{cid} .el-side", {{opacity:0, x:-48, duration:.55, ease:"power3.out"}});',
            f'  tl.from(".scene-{cid} .el-card", {{opacity:0, y:42, duration:.6, ease:"power3.out"}},"-=.35");',
            f'  tl.from(".scene-{cid} .el-kicker", {{opacity:0, x:-20, duration:.35, ease:"power2.out"}},"-=.25");',
            f'  tl.from(".scene-{cid} .el-head", {{opacity:0, y:26, duration:.45, ease:"power2.out"}},"-=.15");',
            f'  tl.from(".scene-{cid} .el-body", {{opacity:0, y:24, duration:.5, ease:"power2.out"}},"-=.1");',
            f'  tl.from(".scene-{cid} .el-note", {{opacity:0, y:18, duration:.4, ease:"power2.out"}},"-=.1");',
        ])
    )


def _render_bullet_points(scene: ScenePlan, ds: DesignSystem, cid: str) -> str:
    items = _split_sentences(scene.narration_text, 5)
    if not items:
        items = [scene.title]
    bullets = "\n".join(
        f'      <li class="item el-b{i}"><span class="num">{i + 1:02d}</span><span>{_e(item)}</span></li>'
        for i, item in enumerate(items)
    )
    anim = [
        f'  tl.from(".scene-{cid} .el-b{i}", {{opacity:0, x:-34, duration:.38, ease:"power2.out"}},"-=.16");'
        for i in range(len(items))
    ]
    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        "<style>\n"
        f"{_common_css(cid, ds)}"
        f".scene-{cid} {{ display:grid; grid-template-columns:610px 1fr; gap:70px; padding:90px 120px; align-items:center; }}\n"
        f".scene-{cid} .lead {{ position:relative; padding:48px 0; }}\n"
        f".scene-{cid} h2 {{ margin:22px 0 0; font-size:62px; line-height:1.14; font-weight:800; color:{ds.colors.text}; }}\n"
        f".scene-{cid} .caption {{ margin-top:28px; font-size:25px; line-height:1.55; color:{ds.colors.secondary}; }}\n"
        f".scene-{cid} .diagram {{ margin-top:46px; height:180px; display:flex; align-items:center; gap:18px; }}\n"
        f".scene-{cid} .node {{ width:82px; height:82px; border-radius:50%; background:#fff; border:1px solid {ds.colors.text}15; box-shadow:0 18px 42px rgba(15,23,42,.12); }}\n"
        f".scene-{cid} .node:nth-child(2) {{ background:{ds.colors.accent}; transform:translateY(-24px); }}\n"
        f".scene-{cid} .node:nth-child(4) {{ background:{ds.colors.primary}; transform:translateY(22px); }}\n"
        f".scene-{cid} .line {{ width:64px; height:3px; border-radius:999px; background:{ds.colors.text}20; }}\n"
        f".scene-{cid} ol {{ list-style:none; margin:0; padding:0; display:grid; gap:18px; }}\n"
        f".scene-{cid} .item {{ display:grid; grid-template-columns:80px 1fr; gap:22px; align-items:start; min-height:104px; padding:24px 28px;\n"
        f"  border-radius:8px; background:rgba(255,255,255,.86); border:1px solid {ds.colors.text}12; box-shadow:0 16px 46px rgba(15,23,42,.08);\n"
        f"  font-size:25px; line-height:1.48; color:{ds.colors.text}; }}\n"
        f".scene-{cid} .item .num {{ width:52px; height:52px; display:grid; place-items:center; border-radius:8px;\n"
        f"  background:{ds.colors.accent}16; color:{ds.colors.accent}; font-size:20px; font-weight:800; }}\n"
        "</style>\n"
        '  <div class="stage-bg"></div><div class="grid"></div><div class="grain"></div>\n'
        '  <section class="lead el-lead">\n'
        f'    <div class="kicker">拆成几步看</div>\n'
        f'    <h2>{_e(scene.title)}</h2>\n'
        f'    <p class="caption">{_e(_short(scene.narration_text, 92))}</p>\n'
        '    <div class="diagram el-diagram"><span class="node"></span><span class="line"></span><span class="node"></span><span class="line"></span><span class="node"></span></div>\n'
        '  </section>\n'
        '  <ol class="list">\n'
        f'{bullets}\n'
        '  </ol>\n'
        "</div>\n"
        "</div>\n"
        + _script(cid, [
            f'  tl.from(".scene-{cid} .el-lead", {{opacity:0, x:-46, duration:.55, ease:"power3.out"}});',
            f'  tl.from(".scene-{cid} .el-diagram .node, .scene-{cid} .el-diagram .line", {{opacity:0, scale:.86, stagger:.07, duration:.35, ease:"back.out(1.4)"}},"-=.25");',
            *anim,
        ])
    )


def _render_image_text(scene: ScenePlan, ds: DesignSystem, cid: str) -> str:
    words = _keyword_badges(_keywords(scene), "chip")
    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        "<style>\n"
        f"{_common_css(cid, ds)}"
        f".scene-{cid} {{ display:grid; grid-template-columns:760px 1fr; min-height:1080px; }}\n"
        f".scene-{cid} .visual {{ position:relative; overflow:hidden; background:linear-gradient(145deg,{ds.colors.primary},{ds.colors.accent}); }}\n"
        f".scene-{cid} .visual::before {{ content:''; position:absolute; inset:62px; border:1px solid rgba(255,255,255,.32); border-radius:8px; }}\n"
        f".scene-{cid} .ring {{ position:absolute; border-radius:50%; border:2px solid rgba(255,255,255,.28); }}\n"
        f".scene-{cid} .ring.a {{ width:520px; height:520px; left:118px; top:152px; }}\n"
        f".scene-{cid} .ring.b {{ width:310px; height:310px; left:228px; top:258px; background:rgba(255,255,255,.13); }}\n"
        f".scene-{cid} .ring.c {{ width:148px; height:148px; left:306px; top:340px; background:#fff; box-shadow:0 24px 80px rgba(0,0,0,.22); }}\n"
        f".scene-{cid} .axis {{ position:absolute; left:122px; right:122px; top:540px; height:2px; background:rgba(255,255,255,.45); transform:rotate(-18deg); }}\n"
        f".scene-{cid} .caption-card {{ position:absolute; left:96px; right:96px; bottom:88px; padding:26px 30px; border-radius:8px;\n"
        f"  background:rgba(255,255,255,.9); color:{ds.colors.text}; box-shadow:0 22px 62px rgba(15,23,42,.2); }}\n"
        f".scene-{cid} .caption-card strong {{ display:block; font-size:23px; margin-bottom:8px; }}\n"
        f".scene-{cid} .caption-card span {{ font-size:18px; color:{ds.colors.secondary}; }}\n"
        f".scene-{cid} .copy {{ padding:96px 116px 86px 78px; display:flex; flex-direction:column; justify-content:center; }}\n"
        f".scene-{cid} .chips {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:30px; }}\n"
        f".scene-{cid} .chip {{ height:38px; padding:0 16px; display:inline-flex; align-items:center; border-radius:999px;\n"
        f"  background:{ds.colors.primary}12; border:1px solid {ds.colors.primary}26; color:{ds.colors.primary}; font-size:17px; font-weight:800; }}\n"
        f".scene-{cid} h2 {{ margin:0; font-size:58px; line-height:1.15; font-weight:800; color:{ds.colors.text}; }}\n"
        f".scene-{cid} p {{ margin:32px 0 0; font-size:27px; line-height:1.72; color:{ds.colors.text}; white-space:pre-wrap; }}\n"
        f".scene-{cid} .quote {{ margin-top:40px; padding-left:28px; border-left:6px solid {ds.colors.accent}; color:{ds.colors.secondary}; font-size:23px; line-height:1.5; font-weight:700; }}\n"
        "</style>\n"
        '  <div class="stage-bg"></div><div class="grid"></div><div class="grain"></div>\n'
        '  <aside class="visual el-left">\n'
        '    <div class="ring a"></div><div class="ring b"></div><div class="ring c"></div><div class="axis"></div>\n'
        '    <div class="caption-card el-caption"><strong>可视化理解</strong><span>把抽象知识转成结构关系</span></div>\n'
        '  </aside>\n'
        '  <main class="copy el-right">\n'
        f'    <div class="chips">\n{words}\n    </div>\n'
        f'    <h2>{_e(scene.title)}</h2>\n'
        f'    <p>{_e(scene.narration_text)}</p>\n'
        f'    <div class="quote">关键不是记住结论，而是看清它背后的因果链条。</div>\n'
        '  </main>\n'
        "</div>\n"
        "</div>\n"
        + _script(cid, [
            f'  tl.from(".scene-{cid} .el-left", {{opacity:0, x:-90, duration:.65, ease:"power3.out"}});',
            f'  tl.from(".scene-{cid} .ring", {{opacity:0, scale:.78, stagger:.12, duration:.55, ease:"back.out(1.35)"}},"-=.35");',
            f'  tl.from(".scene-{cid} .el-caption", {{opacity:0, y:28, duration:.4, ease:"power2.out"}},"-=.2");',
            f'  tl.from(".scene-{cid} .el-right", {{opacity:0, x:62, duration:.6, ease:"power3.out"}},"-=.42");',
            f'  tl.from(".scene-{cid} .chip", {{opacity:0, y:14, stagger:.06, duration:.28, ease:"power2.out"}},"-=.25");',
        ])
    )


def _render_conclusion(scene: ScenePlan, ds: DesignSystem, cid: str) -> str:
    points = _split_sentences(scene.narration_text, 3)
    if not points:
        points = [scene.title]
    rows = "\n".join(
        f'      <div class="take el-t{i}"><span>{i + 1}</span><p>{_e(_short(point, 46))}</p></div>'
        for i, point in enumerate(points)
    )
    anim = [
        f'  tl.from(".scene-{cid} .el-t{i}", {{opacity:0, y:22, duration:.34, ease:"power2.out"}},"-=.13");'
        for i in range(len(points))
    ]
    return (
        f'<div data-composition-id="{cid}" {_BASE_ATTRS}>\n'
        f'<div class="scene-{cid}">\n'
        "<style>\n"
        f"{_common_css(cid, ds)}"
        f".scene-{cid} {{ display:grid; place-items:center; padding:86px 120px; text-align:center; }}\n"
        f".scene-{cid} .panel {{ width:1460px; position:relative; padding:76px 92px 70px; border-radius:8px;\n"
        f"  background:rgba(255,255,255,.9); border:1px solid {ds.colors.text}12; box-shadow:0 26px 86px rgba(15,23,42,.13); }}\n"
        f".scene-{cid} .panel::before {{ content:''; position:absolute; left:0; top:0; right:0; height:10px; border-radius:8px 8px 0 0;\n"
        f"  background:linear-gradient(90deg,{ds.colors.accent},{ds.colors.primary},{ds.colors.secondary}); }}\n"
        f".scene-{cid} .badge {{ display:inline-flex; align-items:center; height:44px; padding:0 22px; border-radius:999px; background:{ds.colors.accent};\n"
        f"  color:#fff; font-size:19px; font-weight:800; }}\n"
        f".scene-{cid} h1 {{ margin:28px auto 22px; max-width:1080px; font-size:70px; line-height:1.12; color:{ds.colors.text}; font-weight:800; }}\n"
        f".scene-{cid} .body {{ margin:0 auto; max-width:1020px; font-size:28px; line-height:1.58; color:{ds.colors.secondary}; }}\n"
        f".scene-{cid} .takes {{ margin:46px auto 0; display:grid; grid-template-columns:repeat(3, 1fr); gap:18px; text-align:left; }}\n"
        f".scene-{cid} .take {{ min-height:142px; padding:24px 24px 22px; border-radius:8px; background:{ds.colors.background}; border:1px solid {ds.colors.text}12; }}\n"
        f".scene-{cid} .take span {{ display:grid; place-items:center; width:42px; height:42px; border-radius:8px; background:{ds.colors.accent}18;\n"
        f"  color:{ds.colors.accent}; font-weight:900; margin-bottom:18px; }}\n"
        f".scene-{cid} .take p {{ margin:0; font-size:22px; line-height:1.45; color:{ds.colors.text}; font-weight:700; }}\n"
        f".scene-{cid} .cta {{ margin-top:42px; display:inline-flex; align-items:center; justify-content:center; height:62px; padding:0 38px;\n"
        f"  border-radius:8px; background:{ds.colors.text}; color:#fff; font-size:22px; font-weight:800; }}\n"
        "</style>\n"
        '  <div class="stage-bg"></div><div class="grid"></div><div class="grain"></div>\n'
        '  <main class="panel el-panel">\n'
        '    <div class="badge el-badge">总结</div>\n'
        f'    <h1 class="el-title">{_e(scene.title)}</h1>\n'
        f'    <div class="body el-body">{_e(_short(scene.narration_text, 118))}</div>\n'
        f'    <div class="takes">\n{rows}\n    </div>\n'
        '    <div class="cta el-cta">带走这 3 个关键点</div>\n'
        '  </main>\n'
        "</div>\n"
        "</div>\n"
        + _script(cid, [
            f'  tl.from(".scene-{cid} .el-panel", {{opacity:0, y:46, duration:.58, ease:"power3.out"}});',
            f'  tl.from(".scene-{cid} .el-badge", {{opacity:0, y:-18, duration:.35, ease:"power2.out"}},"-=.3");',
            f'  tl.from(".scene-{cid} .el-title", {{opacity:0, scale:.94, duration:.55, ease:"power2.out"}},"-=.18");',
            f'  tl.from(".scene-{cid} .el-body", {{opacity:0, y:20, duration:.4, ease:"power2.out"}},"-=.2");',
            *anim,
            f'  tl.from(".scene-{cid} .el-cta", {{opacity:0, y:18, duration:.35, ease:"power2.out"}},"-=.05");',
        ])
    )


_RENDERERS = {
    "title_card": _render_title_card,
    "content_card": _render_content_card,
    "bullet_points": _render_bullet_points,
    "image_text": _render_image_text,
    "conclusion": _render_conclusion,
}
