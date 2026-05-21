# Voice Selection — 音色选择功能设计

## 概述

为 hhDome 文档转视频系统增加音色选择功能，用户可在前端选择配音音色，所选音色贯穿整个视频的 TTS 合成。

## 改动范围

### 后端

**1. `app/core/tts_service.py`**
- `VOLC_VOICES` 从 5 个音色扩展为 15 个，保留原有 key=名称 value=ID 格式
- 新增 `VOICE_CATEGORIES` 字典，按风格分组：专业沉稳、温暖亲和、活力生动
- 类默认值 `voice_type` 改为 `zh_female_vv_jupiter_bigtts` (Vivi)

**2. `app/models.py`**
- `ProjectRequest` 新增字段：`voice_type: str = "zh_female_vv_jupiter_bigtts"`

**3. `app/core/pipeline.py`**
- `Pipeline.run()` 中 `VolcTTSService` 初始化时传入 `request.voice_type`

**4. `app/api/routes.py`**
- `POST /api/v1/projects` 新增 `voice_type: str = Form("zh_female_vv_jupiter_bigtts")` 参数
- `GET /api/v1/tts/voices` 返回按风格分组的数据结构供前端渲染

### 前端

**`src/App.tsx`**
- 新增 `voiceType` state，默认值 `zh_female_vv_jupiter_bigtts`
- `useEffect` 加载时请求 `GET /api/v1/tts/voices` 获取音色分组数据
- 表单中新增分组 `<select>`，使用 `<optgroup>` 按风格分组
- 每个选项显示"名称 (性别) — 风格"，如 `Vivi (女) — 专业活力`
- 提交表单时 `voice_type` 随 FormData 一起发送

## 音色列表（15 个）

### 专业沉稳（4 个）
| 显示名 | 音色 ID | 性别 |
|--------|---------|------|
| 云舟 — 沉稳清爽 | `zh_male_yunzhou_jupiter_bigtts` | 男 |
| James — 清晰解说 | `zh_male_jieshuonansheng_mars_bigtts` | 男 |
| 小天 — 磁性亲和 | `zh_male_xiaotian_jupiter_bigtts` | 男 |
| Charlotte — 清冷御姐 | `zh_female_gaolengyujie_moon_bigtts` | 女 |

### 温暖亲和（6 个）
| 显示名 | 音色 ID | 性别 |
|--------|---------|------|
| Mark — 温暖男声 | `zh_male_wennuanahu_moon_bigtts` | 男 |
| 阳光青年 — 阳光积极 | `zh_male_yangguangqingnian_moon_bigtts` | 男 |
| Emma — 温柔淑女 | `zh_female_wenroushunv_mars_bigtts` | 女 |
| Sophia — 温暖贴心 | `zh_female_tiexinnvsheng_mars_bigtts` | 女 |
| Grace — 温柔知性 | `zh_female_jitangmeimei_mars_bigtts` | 女 |
| Olivia — 清晰通用 | `zh_female_qingxinnvsheng_mars_bigtts` | 女 |

### 活力生动（5 个）
| 显示名 | 音色 ID | 性别 |
|--------|---------|------|
| Vivi — 专业活力 | `zh_female_vv_jupiter_bigtts` | 女 |
| Mia — 生动活泼 | `zh_female_qiaopinvsheng_mars_bigtts` | 女 |
| Lily — 清晰生动 | `zh_female_linjia_mars_bigtts` | 女 |
| Aria — 爽快利落 | `zh_female_shuangkuaisisi_moon_bigtts` | 女 |
| Ethan — 少年自信 | `zh_male_shaonianzixin_moon_bigtts` | 男 |

## 数据流

```
前端选择音色 → POST /api/v1/projects (voice_type in FormData)
  → routes.py 解析 → ProjectRequest(voice_type=...)
    → Pipeline.run() → VolcTTSService(voice_type=...)
      → TTS WebSocket 合成 → MP3 音频（使用所选音色）
```

## 不涉及

- 不同场景不同音色（全局统一）
- 音色试听功能
- 音色搜索/筛选
- 方言或英文音色（后续可按需扩展）
