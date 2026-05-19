# Video Agent — 智能视频生成智能体设计文档

## 概述

基于 HyperFrames + Claude Code Skill 的通用视频生成智能体。用户输入需求文本，经多轮 AI 编排和人工确认，最终输出高美观度的 .mp4 视频。支持嵌入 3D 虚拟人做画中画口播。

---

## 一、系统架构

```
用户需求 (自由文本)
    │
    ▼
┌─────────────────────────────────────────┐
│          video-agent skill              │
│  (Claude Code Skill, 流程编排 + 决策)    │
│                                         │
│  ┌─ 需求分析 ─┬─ 用户确认 ─┬─ 脚本生成 ─┐ │
│  │ 模板匹配  │  视觉设计  │  合成输出  │ │
│  └───────────┴───────────┴───────────┘ │
└────────────────┬────────────────────────┘
    │
    ├──→ ui-ux-pro-max (各环节视觉优化)
    ├──→ hyperframes (场景合成生成)
    ├──→ three (3D 虚拟人渲染)
    └──→ hyperframes-media (TTS + 音频处理)
```

### 核心原则

- **Skill 做大脑**：不依赖 LangChain/RAG，Claude Code 自身就是编排引擎
- **文件系统做知识库**：`templates/` 分类型存放模板，直接按类型名称匹配
- **ui-ux-pro-max 做设计师**：每个视觉环节都调用该技能优化

---

## 二、项目目录结构（调整后完整版）

```
my-video/
│
├── agent/                          ← 智能体核心
│   ├── skill.yaml                  ← Skill 注册/定义
│   ├── workflows/
│   │   └── generate-video.md       ← 完整执行流程（CLAUD.md 将引用此文件）
│   └── prompts/
│       ├── analyze-requirement.md   ← 需求分析：从用户自由文本提取结构化信息
│       ├── generate-script.md       ← 脚本生成：按视频类型写对口播文案
│       ├── design-storyboard.md     ← 分镜设计：场景划分 + 视觉描述
│       ├── apply-style-tokens.md    ← 风格应用：把 ui-ux-pro-max 输出转为 CSS token
│       └── avatar-dialogue.md       ← 虚拟人口播：哪些场景出镜 + 台词分配
│
├── templates/                      ← 视频类型模板库（可扩展）
│   ├── corporate/                  ← 企业宣传片模板
│   │   ├── manifest.json           ← 模板元数据：场景数、风格倾向、虚拟人策略等
│   │   ├── scenes/
│   │   │   ├── 01-welcome.html     ← 固定开场
│   │   │   ├── 02-content.html     ← 内容主体（占位符替换）
│   │   │   ├── 03-avatar.html      ← 虚拟人口播场景
│   │   │   ├── 04-data.html        ← 数据展示
│   │   │   └── 05-closing.html     ← 结尾
│   │   └── style/
│   │       └── tokens.css          ← 默认风格 token
│   ├── educational/                ← 教学视频
│   │   ├── manifest.json
│   │   ├── scenes/
│   │   │   ├── 01-intro.html
│   │   │   ├── 02-lecture.html
│   │   │   ├── 03-avatar.html
│   │   │   └── 04-summary.html
│   │   └── style/
│   │       └── tokens.css
│   └── product/                    ← 产品介绍
│       ├── manifest.json
│       ├── scenes/
│       └── style/
│
├── compositions/                   ← 每次生成的实际输出（自动生成，不手动编辑）
│   └── [job-id]/
│       ├── index.html              ← 主时间线
│       ├── scene-1.html ~ scene-N.html
│       ├── avatar.js               ← 3D 虚拟人脚本
│       └── style.css
│
├── assets/
│   ├── narration.wav               ← 当前配音
│   ├── tts/                        ← TTS 生成音频
│   ├── reference-audio/            ← 参考音频（如 阳光甜美.mp3）
│   └── 3d-avatar/                  ← 3D 虚拟人模型资源
│       ├── avatar-model.glb
│       └── textures/
│
├── docs/
│   ├── script.txt
│   └── meta.json
│
├── design-system/
│   └── MASTER.md
│
├── renders/
│   ├── output/                     ← 成品 .mp4
│   └── work/                       ← 渲染临时文件 (.gitignore)
│
├── index.html                      ← 保留当前入口
├── package.json
├── hyperframes.json
└── .gitignore
```

---

## 三、用户交互流程（详细）

### Step 1：需求输入
用户输入任意文本，例如：
> "做一个恒海实业集团的招聘宣传片，2分钟，风格现代大气，重点展示工作环境和团队氛围"

### Step 2：智能提取（自动）
Skill 调用 `prompts/analyze-requirement.md` 提取结构化信息：

```json
{
  "videoType": "corporate-recruitment",
  "topic": "恒海实业集团招聘宣传",
  "duration": "120s",
  "style": "现代大气",
  "targetAudience": "求职者",
  "keyPoints": ["工作环境", "团队氛围", "发展前景"],
  "avatarPresence": "opening + closing",
  "voiceStyle": "参考阳光甜美.mp3"
}
```

### Step 3：用户确认 ①（需求卡片）
展示上述卡片，用户确认或修改。

### Step 4：风格设计（ui-ux-pro-max）
调用 `ui-ux-pro-max` 技能，输入视频类型和风格关键词，输出：

- 配色方案（主色/辅色/强调色 + 配色原理说明）
- 字体搭配
- 装饰风格（光影、渐变、粒子等）
- 动画节奏（快/中/慢 + GSAP 曲线建议）
- 虚拟人外观建议（服装色系、打光风格）

### Step 5：脚本生成
根据确认的需求 + 风格方案，调用 `prompts/generate-script.md` 生成：

- 分场景文案
- 虚拟人口播台词（标注哪些场景出镜）
- 画面描述（每段文案对应什么视觉）

### Step 6：用户确认 ②（脚本 + 分镜）
展示完整脚本，用户可逐段修改。

### Step 7：组合生成
1. 根据 `videoType` 选择 `templates/` 下对应模板
2. 注入文案内容
3. 注入风格 token（ui-ux-pro-max 输出）
4. 生成 3D 虚拟人场景（Three.js，画中画）
5. 生成主时间线（index.html + GSAP 转场）
6. 复制参考音频用于 TTS 风格匹配

### Step 8：渲染出片
`hyperframes render` → `renders/output/[job-id].mp4`

---

## 四、3D 虚拟人方案

### 技术栈
- **渲染引擎**：Three.js（通过 `three` 技能适配到 HyperFrames）
- **模型格式**：GLB/GLTF（可使用 Ready Player Me 等免费工具生成女性 3D 头像）
- **同步机制**：HyperFrames `hf-seek` 事件驱动虚拟人动画进度

### 虚拟人动作系统

| 动作 | 触发条件 | 实现方式 |
|------|---------|---------|
| 口型同步 | 有配音时段 | 下巴 bone 按音频音量/音素微动 |
| 眨眼 | 每 3-5 秒 | 眼睑 bone 动画循环 |
| 轻微晃动 | 全程 | 上半身 idle 动画（sine 波浪） |
| 手势 | 关键台词 | 预设手势动画（欢迎、强调等） |

### PiP 布局

```
┌──────────────────────────────────────────┐
│                                          │
│           场景主体内容                      │
│                                          │
│                              ┌──────────┐│
│                              │          ││
│                              │ 虚拟人   ││
│                              │ (320×480)││
│                              │          ││
│                              └──────────┘│
└──────────────────────────────────────────┘
     右下角悬浮，圆角 + 柔光阴影边框
```

### 出镜策略

| 视频类型 | 出镜场景 | 虚拟人角色 |
|---------|---------|-----------|
| 企业宣传 | 开场 + 结尾 | 主持人/向导 |
| 教学视频 | 全程（画面一角） | 讲师 |
| 产品介绍 | 开场 + 关键卖点 | 产品专家 |

---

## 五、ui-ux-pro-max 集成点

| 阶段 | ui-ux-pro-max 作用 | 输出 |
|------|-------------------|------|
| 需求分析后 | 根据类型+风格生成视觉方案 | 配色、字体、装饰风格 |
| 脚本生成后 | 优化画面描述、场景构图 | 场景布局建议 |
| 组合生成前 | 优化 token.css 动画曲线 | GSAP ease 参数 |
| 虚拟人设计 | 建议虚拟人外观、打光 | 3D 材质参数 |

---

## 六、技术风险与应对

| 风险 | 应对 |
|------|------|
| Three.js 3D 虚拟人性能开销 | 限制顶点数，使用低面数风格化模型 |
| TTS 声音不匹配参考音频 | 使用支持声音克隆的 TTS（如 Fish Audio / GPT-SoVITS） |
| HyperFrames + Three.js 同步精度 | 通过 hf-seek 事件驱动，逐帧同步 |
| 渲染耗时 | 首次渲染走快速模式预览，确认后再高质量输出 |
| 模板不足 | 初期支持 3 类模板，后续按需扩展 |

---

## 七、未来扩展

- [ ] HeyGen API 集成：用 HeyGen 官方数字人代替 Three.js 虚拟人
- [ ] WebUI 界面：用户通过浏览器填需求、预览分镜
- [ ] 多语言配音：英语、日语等多语言 TTS
- [ ] 团队协作：多人审片、批注功能
- [ ] LangChain 迁移版：如需独立部署再引入
