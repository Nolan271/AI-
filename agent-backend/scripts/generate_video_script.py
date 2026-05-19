"""使用 DeepSeek 直接生成新员工入职视频脚本（不使用 LangChain/RAG）"""

import json
import sys
from pathlib import Path

from openai import OpenAI

# 读取员工手册
handbook_path = Path(__file__).parent.parent / "handbook_text.txt"
handbook_text = handbook_path.read_text(encoding="utf-8")

# DeepSeek 客户端
client = OpenAI(
    api_key="sk-d18abb950e8944e6bb17aa7f784a1b52",
    base_url="https://api.deepseek.com/v1",
)

prompt = f"""你是一个专业的视频脚本编写专家。请根据以下员工手册内容，为新员工入职培训视频编写完整的视频脚本。

员工手册内容：
{handbook_text[:12000]}

要求：
1. 视频总时长约 170 秒，分为 7 个场景
2. 每个场景需要有：标题、旁白文本（中文配音用）、视觉描述
3. 旁白文本要口语化、亲切自然，适合 TTS 语音合成
4. 整体风格：企业宣传风格，现代、专业、温暖
5. 视觉描述要简洁，说明每个画面的设计风格和元素

请按以下 JSON 格式输出（不要包含其他内容）：

```json
{{
    "title": "恒海实业集团 - 新员工入职指南",
    "total_duration_seconds": 170,
    "scenes": [
        {{
            "index": 1,
            "title": "场景标题",
            "duration_seconds": 25,
            "narration_text": "旁白文本，要自然口语化...",
            "visual_description": "画面视觉描述：背景色、文字、装饰元素等"
        }}
    ]
}}
```"""

print("正在生成视频脚本...")
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "你是一个专业的视频脚本编写专家。"},
        {"role": "user", "content": prompt},
    ],
    temperature=0.7,
    max_tokens=4000,
)

content = response.choices[0].message.content

# 提取 JSON
json_start = content.find("```json")
if json_start != -1:
    json_start = content.find("\n", json_start) + 1
    json_end = content.rfind("```")
    content = content[json_start:json_end].strip()

# Validate JSON
data = json.loads(content)

# Save
output_path = Path(__file__).parent / "video_script.json"
output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"✅ 脚本生成完成！共 {len(data['scenes'])} 个场景")
for scene in data["scenes"]:
    print(f"  场景 {scene['index']}: {scene['title']} ({scene['duration_seconds']}s)")

print(f"  旁白总字数: {sum(len(s['narration_text']) for s in data['scenes'])}")
print(f"  保存至: {output_path}")
