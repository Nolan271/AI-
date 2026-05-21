# Voice Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a voice selector to the video creation flow — user picks from 15 voices, selection propagates through the pipeline to TTS.

**Architecture:** Backend exposes voice list as a categorized API endpoint; frontend renders a grouped `<select>`. The selected `voice_type` flows as a form parameter through `ProjectRequest` → `Pipeline` → `VolcTTSService`.

**Tech Stack:** Python FastAPI + LangChain (backend), React 18 + Vite (frontend), Volcengine Seed-TTS 2.0 (TTS)

**Spec:** `docs/superpowers/specs/2026-05-21-voice-selection-design.md`

---

### Task 1: Expand VOLC_VOICES to 15 + add VOICE_CATEGORIES

**Files:**
- Modify: `agent-backend/app/core/tts_service.py`

- [ ] **Step 1: Replace the VOLC_VOICES dict**

Old code (lines 54-60):
```python
VOLC_VOICES = {
    "Vivi 2.0": "zh_female_vv_uranus_bigtts",
    "TVB女声 2.0": "zh_female_tvbnv_uranus_bigtts",
    "甜美桃子 2.0": "zh_female_tianmeitaozi_mars_bigtts",
    "爽朗少年 2.0": "zh_female_shuangkuaisisi_moon_bigtts",
    "译制片男 2.0": "zh_male_yizhipiannan_uranus_bigtts",
}
```

New code:
```python
VOLC_VOICES = {
    # 专业沉稳
    "云舟 — 沉稳清爽": "zh_male_yunzhou_jupiter_bigtts",
    "James — 清晰解说": "zh_male_jieshuonansheng_mars_bigtts",
    "小天 — 磁性亲和": "zh_male_xiaotian_jupiter_bigtts",
    "Charlotte — 清冷御姐": "zh_female_gaolengyujie_moon_bigtts",
    # 温暖亲和
    "Mark — 温暖男声": "zh_male_wennuanahu_moon_bigtts",
    "阳光青年 — 阳光积极": "zh_male_yangguangqingnian_moon_bigtts",
    "Emma — 温柔淑女": "zh_female_wenroushunv_mars_bigtts",
    "Sophia — 温暖贴心": "zh_female_tiexinnvsheng_mars_bigtts",
    "Grace — 温柔知性": "zh_female_jitangmeimei_mars_bigtts",
    "Olivia — 清晰通用": "zh_female_qingxinnvsheng_mars_bigtts",
    # 活力生动
    "Vivi — 专业活力": "zh_female_vv_jupiter_bigtts",
    "Mia — 生动活泼": "zh_female_qiaopinvsheng_mars_bigtts",
    "Lily — 清晰生动": "zh_female_linjia_mars_bigtts",
    "Aria — 爽快利落": "zh_female_shuangkuaisisi_moon_bigtts",
    "Ethan — 少年自信": "zh_male_shaonianzixin_moon_bigtts",
}
```

- [ ] **Step 2: Add VOICE_CATEGORIES after VOLC_VOICES**

```python
VOICE_CATEGORIES = {
    "专业沉稳": [
        "云舟 — 沉稳清爽",
        "James — 清晰解说",
        "小天 — 磁性亲和",
        "Charlotte — 清冷御姐",
    ],
    "温暖亲和": [
        "Mark — 温暖男声",
        "阳光青年 — 阳光积极",
        "Emma — 温柔淑女",
        "Sophia — 温暖贴心",
        "Grace — 温柔知性",
        "Olivia — 清晰通用",
    ],
    "活力生动": [
        "Vivi — 专业活力",
        "Mia — 生动活泼",
        "Lily — 清晰生动",
        "Aria — 爽快利落",
        "Ethan — 少年自信",
    ],
}
```

- [ ] **Step 3: Update the default voice_type in VolcTTSService.__init__**

Old: `voice_type: str = "zh_female_vv_uranus_bigtts"`
New: `voice_type: str = "zh_female_vv_jupiter_bigtts"`

- [ ] **Step 4: Verify**

```bash
cd agent-backend
python -c "from app.core.tts_service import VOLC_VOICES, VOICE_CATEGORIES; print(f'{len(VOLC_VOICES)} voices, {len(VOICE_CATEGORIES)} categories'); print('OK')"
```
Expected: `15 voices, 3 categories`

- [ ] **Step 5: Commit**

```bash
git add agent-backend/app/core/tts_service.py
git commit -m "feat(tts): expand voice list to 15 with style categories"
```

---

### Task 2: Add voice_type to ProjectRequest model

**Files:**
- Modify: `agent-backend/app/models.py`

- [ ] **Step 1: Add voice_type field to ProjectRequest**

Add after `design_system_path` (line 15):
```python
voice_type: str = "zh_female_vv_jupiter_bigtts"  # default Vivi
```

- [ ] **Step 2: Commit**

```bash
git add agent-backend/app/models.py
git commit -m "feat(models): add voice_type field to ProjectRequest"
```

---

### Task 3: Update Pipeline to pass voice_type to TTS

**Files:**
- Modify: `agent-backend/app/core/pipeline.py`

- [ ] **Step 1: Pass voice_type when initializing VolcTTSService**

In `__init__` (line 27), keep the default:
```python
self.tts_service = VolcTTSService()
```

In `run()` method, before TTS synthesis around line 74, replace:
```python
await self.tts_service.synthesize(script, tts_path)
```

with:
```python
# Use voice_type from request if provided
tts = VolcTTSService(voice_type=request.voice_type)
await tts.synthesize(script, tts_path)
```

So the full TTS section becomes:
```python
tts = VolcTTSService(voice_type=request.voice_type)
audio_path = None
if generate_tts and script.strip():
    try:
        audio_dir = settings.output_abs_path / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        tts_path = audio_dir / f"{project_id}_narration.mp3"
        await tts.synthesize(script, tts_path)
        audio_path = str(tts_path)
    except Exception as e:
        print(f"[TTS Warning] Speech synthesis failed: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add agent-backend/app/core/pipeline.py
git commit -m "feat(pipeline): pass voice_type from request to TTS service"
```

---

### Task 4: Update API routes — accept voice_type, expose voice list

**Files:**
- Modify: `agent-backend/app/api/routes.py`

- [ ] **Step 1: Import VOICE_CATEGORIES at top of file**

The import line already exists (line 14):
```python
from app.core.tts_service import VolcTTSService
```

Change to:
```python
from app.core.tts_service import VolcTTSService, VOLC_VOICES, VOICE_CATEGORIES
```

(The `VOLC_VOICES` import already exists on line 125 in `list_tts_voices`, so we just add `VOICE_CATEGORIES` and keep `VOLC_VOICES`.)

Wait, let me check the existing import pattern. Line 14 imports:
```python
from app.core.tts_service import VolcTTSService
```

And the `list_tts_voices` function (line 123) does:
```python
from app.core.tts_service import VOLC_VOICES
return VOLC_VOICES
```

I should move the import to the top and add VOICE_CATEGORIES:
```python
from app.core.tts_service import VolcTTSService, VOLC_VOICES, VOICE_CATEGORIES
```

And update `list_tts_voices` to remove its local import.

- [ ] **Step 2: Add voice_type form parameter to POST /api/v1/projects**

Add after `narration_language: str = Form("zh-CN")`:
```python
voice_type: str = Form("zh_female_vv_jupiter_bigtts"),
```

And add it to the ProjectRequest construction:
```python
request = ProjectRequest(
    title=title,
    description=description,
    style_keywords=style_keywords,
    scene_count=scene_count,
    total_duration_seconds=total_duration_seconds,
    narration_language=narration_language,
    voice_type=voice_type,
)
```

- [ ] **Step 3: Update GET /api/v1/tts/voices to return grouped data**

Replace existing function body:
```python
@router.get("/tts/voices")
async def list_tts_voices():
    """获取分组音色列表（供前端选择器使用）"""
    grouped = {}
    for category, names in VOICE_CATEGORIES.items():
        grouped[category] = [
            {"name": name, "id": VOLC_VOICES[name]}
            for name in names
        ]
    return grouped
```

- [ ] **Step 4: Verify routes**

```bash
cd agent-backend
python -c "
from app.api.routes import router
# Find the voices endpoint
for r in router.routes:
    if '/tts/voices' in r.path:
        print(f'Found: {r.methods} {r.path}')
        break
print('Routes OK')
"
```

- [ ] **Step 5: Commit**

```bash
git add agent-backend/app/api/routes.py
git commit -m "feat(api): accept voice_type in project creation, return grouped voices"
```

---

### Task 5: Frontend — voice selector dropdown

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add voice state and fetch logic**

Add these new imports at the top (after existing imports):
```typescript
import { useState, useRef, FormEvent, useEffect } from 'react'
```

Add these state variables after existing state (after line 38 `const [error, setError] = useState('')`):
```typescript
const [voices, setVoices] = useState<Record<string, Array<{name: string, id: string}>>>({})
const [voiceType, setVoiceType] = useState('zh_female_vv_jupiter_bigtts')
```

Add fetch logic after the state declarations (before `const fileRef`):
```typescript
useEffect(() => {
  fetch(`${API_BASE}/tts/voices`)
    .then(res => res.json())
    .then(data => setVoices(data))
    .catch(() => {})
}, [])
```

Pass `voiceType` in the form submission. After `formData.append('narration_language', 'zh-CN')`, add:
```typescript
formData.append('voice_type', voiceType)
```

- [ ] **Step 2: Add voice selector UI to the form**

Insert this block between the "总时长" input and "上传文档素材" section (after line 152, the `</div>` closing the duration field, and before line 155 the "上传文档素材" label):

```tsx
<div className="form-group">
  <label>配音音色</label>
  <select
    value={voiceType}
    onChange={e => setVoiceType(e.target.value)}
    style={{
      width: '100%',
      padding: '10px 14px',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      fontSize: 14,
      background: 'white',
      cursor: 'pointer',
    }}
  >
    {Object.entries(voices).map(([category, items]) => (
      <optgroup label={category} key={category}>
        {items.map(v => (
          <option key={v.id} value={v.id}>
            {v.name}
          </option>
        ))}
      </optgroup>
    ))}
  </select>
</div>
```

- [ ] **Step 3: Verify frontend compiles**

```bash
cd frontend
npx tsc --noEmit
```
Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): add voice selector dropdown with grouped options"
```

---

### Self-Review

1. **Spec coverage:** All spec sections covered — voice list expansion (Task 1), model field (Task 2), pipeline wiring (Task 3), API endpoints (Task 4), frontend selector (Task 5). No gaps.

2. **Placeholder scan:** No TBD, TODO, or placeholder code. All code blocks contain exact implementations.

3. **Type consistency:** `voice_type: str = "zh_female_vv_jupiter_bigtts"` — same default value across `VOLC_VOICES`, `ProjectRequest`, route form param, and frontend state. Consistent.
