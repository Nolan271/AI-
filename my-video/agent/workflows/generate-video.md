# Video Generation Workflow

> 用户输入需求 → 多轮确认 + ui-ux-pro-max 美化 → 3D虚拟人口播 → 渲染出片

## Step-by-Step

### Step 1: 接收用户需求
用户输入自由文本描述想要的视频。

### Step 2: 结构化提取
读取 `agent/prompts/analyze-requirement.md` 并执行提取逻辑。
输出 JSON 格式的需求卡片。

### Step 3: 用户确认需求 (Checkpoint 1)
展示:
```json
{
  "videoType": "corporate",
  "topic": "...",
  "duration": "...",
  "style": "...",
  "avatarPresence": "opening+closing"
}
```
用户确认或修改。

### Step 4: 视觉风格设计
- 调用 `ui-ux-pro-max` 技能
- 输入: 视频类型 + 风格关键词
- 输出: 配色方案 / 字体搭配 / 装饰风格 / 动画节奏 / 虚拟人外观建议

### Step 5: 脚本生成
读取 `agent/prompts/generate-script.md`。
调用 `agent/prompts/avatar-dialogue.md` 决定虚拟人哪些场景出镜。

### Step 6: 用户确认脚本 (Checkpoint 2)
展示完整分场景文案，用户可逐段修改。

### Step 7: 模板匹配与组合
1. 根据 videoType 选择 `templates/{type}/`
2. 读取 manifest.json 获取场景配置
3. 注入文案到模板占位符 `{{PLACEHOLDER}}`
4. 注入 `tokens.css` + ui-ux-pro-max 优化后的样式
5. 处理虚拟人场景: 写入正确的 `{{AVATAR_SCRIPT_PATH}}`
6. 生成主时间线 `index.html`
7. 复制音频参考用于 TTS

### Step 8: 渲染
```bash
cd [project]
npm run render
```

## 用户跳过确认
- 如果用户说"直接出片"，跳过 Step 3 和 Step 6
- 如果用户说"只确认一次"，默认在 Step 6 确认
