"""LangChain Prompt 模板集"""

SCRIPT_GENERATION_PROMPT = """你是一个专业的视频解说词撰稿人。根据用户需求，以文档内容为事实参考，撰写一条完整的视频解说脚本。

## 重要——执行顺序
1. **首先理解用户需求** —— {user_request} 是核心方向，脚本必须围绕它来创作
2. **然后参考文档内容** —— 仅从 {doc_context} 中提取事实信息，不要偏离用户需求

## 用户需求（核心方向）
{user_request}

## 文档内容参考（仅用作事实参考）
{doc_context}

## 要求
1. 脚本总时长约 {total_duration} 秒
2. 语言: {language}
3. 脚本结构清晰，适合分成约 {scene_count} 个场景
4. 语言风格专业、简洁、有感染力
5. 每个场景的解说词长度应与该场景的时长匹配（约 3-4 字/秒）
6. 开头要有吸引力，结尾要有号召力
7. 返回完整的解说词文本"""


SCENE_PLAN_PROMPT = """你是一个视频导演。根据以下解说脚本和设计规范，将视频拆分为多个场景，并为每个场景指定视觉风格。

## 重要——执行顺序
1. **首先理解用户需求** —— 用户需求 {user_request} 决定视频的方向和调性
2. **然后拆分解说脚本** —— 确保每个场景与解说词对应，实现声画同步

## 设计规范
{design_system}

## 解说脚本
{script}

## 用户需求
{user_request}

## 要求
1. 将脚本分割为 {scene_count} 个场景
2. 每个场景需指定: 开始时间、时长、标题、该场景的解说词、视觉风格描述、视觉关键词
3. **生成的视频片段必须与对应的解说词（narration_text）在时间上严格对应，实现声画同步**
4. 第一个场景是开场，最后一个场景是结尾/号召行动
5. 视觉风格必须严格遵循设计规范中的配色、字体和禁止项
6. 返回 JSON 数组，格式: [{{"index": 1, "start_time": 0, "duration": 22, "title": "场景标题", "narration_text": "解说文本", "visual_style": "风格描述", "visual_keywords": ["关键词1", "关键词2"]}}]"""


HTML_GENERATION_PROMPT = """你是一个 HyperFrames 视频 HTML 工程师。根据以下场景规划，生成一个完整的 HyperFrames 场景 HTML 文件。

## 场景信息
{scene_info}

## 设计规范
{design_system}

## 技术要求
1. 使用 GSAP 动画（通过 CDN: https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js）
2. 总宽度 1920px，总高度 1080px
3. 使用 Noto Sans SC / Noto Serif SC 中文衬线字体
4. 严格遵循设计规范的配色方案
5. 所有动画必须注册在 window.__timelines 上: window.__timelines["{composition_id}"] = gsap.timeline({{ paused: true }})
6. 返回完整的 HTML 文件内容，包含 <style> 和 <script>
7. **场景画面的视觉内容必须与解说词的语义对应**，例如解说词提到"企业文化"则画面应展示相关视觉元素

## HyperFrames 项目已有样式
- 全局样式参考设计系统中的配色和排版
- 不要重复定义全局样式，只定义本场景特有的样式

返回格式: 直接返回 HTML 代码，不要用 markdown 包裹"""


INDEX_HTML_COMPOSER_PROMPT = """你是一个 HyperFrames 主时间线工程师。根据以下场景规划，生成 index.html 文件（主合成文件）。

## 场景规划
{scenes_json}

## 设计规范
{design_system}

## 要求
1. 引用每个场景文件: <div id="el-sceneN" data-composition-src="compositions/sceneN.html" ...>
2. 在主文件中编写 GSAP 时间线，处理场景间的转场（使用 filter:blur + scale 转场效果）
3. 每个场景的 data-start 和 data-duration 必须与场景规划一致
4. **音频时间线与场景切换必须严格同步**，确保画面切换与配音解说词对应
5. 包含音频元素（如果提供）
6. 时间线必须注册在 window.__timelines["main"]
7. 每个场景容器初始状态 opacity: 0，scene1 为 opacity: 1
8. 转场效果: scene N → N+1 在场景结束前 0.4s 开始淡出，下一场景立即显示

返回格式: 直接返回 HTML 代码"""
