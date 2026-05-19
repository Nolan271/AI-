# 需求分析提示词

从用户自由文本中提取结构化字段。逐个反问澄清。

## 提取字段
- **videoType**: corporate | educational | product | custom
- **topic**: 视频主题（简短描述）
- **duration**: 目标时长（秒）
- **style**: 风格关键词（现代/大气/温馨/活泼/简约等）
- **targetAudience**: 目标受众
- **keyPoints**: 核心要点列表
- **avatarPresence**: full | opening+closing | none
- **voiceStyle**: 参考音频文件名或风格描述

## 输出格式
```json
{
  "videoType": "...",
  "topic": "...",
  "duration": 120,
  "style": "...",
  "targetAudience": "...",
  "keyPoints": [],
  "avatarPresence": "opening+closing",
  "voiceStyle": "参考 assets/reference-audio/ 下的文件"
}
```
