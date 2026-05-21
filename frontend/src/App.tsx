import { useState, useRef, FormEvent, useEffect } from 'react'
import { FileText, Upload, Play, Loader } from 'lucide-react'

const API_BASE = '/api/v1'

interface Project {
  id: string
  request: {
    title: string
    description: string
    style_keywords: string
    scene_count: number
    total_duration_seconds: number
    narration_language: string
  }
  script: string
  scenes: Array<{
    index: number
    start_time: number
    title: string
    duration: number
    narration_text: string
    visual_style: string
  }>
  status: string
}

function App() {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [polishing, setPolishing] = useState(false)
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [project, setProject] = useState<Project | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState('')
  const [voices, setVoices] = useState<Record<string, Array<{name: string, id: string}>>>({})
  const [voiceType, setVoiceType] = useState('zh_female_vv_jupiter_bigtts')
  const [progressMsg, setProgressMsg] = useState('')

  useEffect(() => {
    fetch(`${API_BASE}/tts/voices`)
      .then(res => res.json())
      .then(data => setVoices(data))
      .catch(() => {})
  }, [])

  const fileRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files))
    }
  }

  const handlePolish = async () => {
    if (!description.trim()) return
    setPolishing(true)
    try {
      const res = await fetch(`${API_BASE}/polish-description`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: description }),
      })
      if (!res.ok) throw new Error('润色失败')
      const data = await res.json()
      setDescription(data.polished)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setPolishing(false)
    }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !description.trim()) {
      setError('请填写项目标题和需求描述')
      return
    }
    if (files.length === 0) {
      setError('请上传至少一个文档素材')
      return
    }

    setLoading(true)
    setError('')
    setProject(null)
    setProgressMsg('正在上传文档...')

    try {
      const formData = new FormData()
      formData.append('title', title)
      formData.append('description', description)
      formData.append('narration_language', 'zh-CN')
      formData.append('voice_type', voiceType)

      for (const file of files) {
        formData.append('files', file)
      }

      const res = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || '创建项目失败')
      }

      // 读取 SSE 流
      const reader = res.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'progress') {
              setProgressMsg(event.message)
            } else if (event.type === 'complete') {
              setProject(event.project)
              setProjects(prev => [event.project, ...prev])
            } else if (event.type === 'error') {
              throw new Error(event.message)
            }
          } catch { /* skip malformed events */ }
        }
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
      setProgressMsg('')
    }
  }

  return (
    <div>
      <header className="app-header">
        <FileText size={22} color="#f97316" />
        <h1>Video Agent</h1>
        <span className="badge">AI v0.1</span>
      </header>

      <div className="container">
        {/* 创建项目表单 */}
        <form className="card" onSubmit={handleSubmit}>
          <h2 style={{ fontSize: 18, marginBottom: 20, fontWeight: 600 }}>
            创建视频项目
          </h2>

          <div className="form-group">
            <label>项目标题 *</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="例如：恒海实业集团员工手册"
              required
            />
          </div>

          <div className="form-group">
            <label>需求描述 *</label>
            <div style={{ position: 'relative' }}>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="描述视频的目的、风格、受众..."
                rows={4}
                required
              />
              <button
                type="button"
                className="btn btn-secondary"
                disabled={polishing || !description.trim()}
                onClick={handlePolish}
                style={{ position: 'absolute', bottom: 8, right: 8, padding: '4px 12px', fontSize: 12 }}
              >
                {polishing ? '润色中...' : 'AI 润色'}
              </button>
            </div>
          </div>

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

          <div className="form-group">
            <label>上传文档素材 *（Word / PDF / TXT）</label>
            <div
              className={`file-upload ${files.length > 0 ? 'has-files' : ''}`}
              onClick={() => fileRef.current?.click()}
            >
              <input
                ref={fileRef}
                type="file"
                multiple
                accept=".docx,.pdf,.txt"
                onChange={handleFileChange}
                style={{ display: 'none' }}
                required
              />
              <Upload size={24} style={{ marginBottom: 8 }} />
              <div>
                {files.length > 0
                  ? `已选择 ${files.length} 个文件`
                  : '点击上传或拖拽文档到这里'}
              </div>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !title.trim()}
            style={{ marginTop: 8, width: '100%', justifyContent: 'center' }}
          >
            {loading ? (
              <>
                <span className="loading-spinner" />
                {progressMsg || 'AI 正在生成视频...'}
              </>
            ) : (
              <>
                <Play size={16} />
                开始生成视频
              </>
            )}
          </button>

          {loading && (
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: '60%' }} />
            </div>
          )}

          {error && (
            <p style={{ color: 'var(--color-error)', fontSize: 13, marginTop: 12 }}>
              {error}
            </p>
          )}
        </form>

        {/* 项目结果展示 */}
        {project && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 600 }}>生成结果</h2>
              <span className={`status-badge ${project.status}`}>
                {project.status === 'generated' ? '生成完成' :
                 project.status === 'generating' ? '生成中' :
                 project.status === 'failed' ? '失败' : '待处理'}
              </span>
            </div>

            <div style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 15, fontWeight: 500, marginBottom: 8 }}>解说脚本</h3>
              <div style={{ background: '#f8fafc', padding: 12, borderRadius: 8, fontSize: 13, lineHeight: 1.7, maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                {project.script}
              </div>
            </div>

            <div>
              <h3 style={{ fontSize: 15, fontWeight: 500, marginBottom: 8 }}>
                场景规划（{project.scenes.length} 个场景）
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {project.scenes.map((scene) => (
                  <div key={scene.index} style={{ display: 'flex', gap: 12, padding: '10px 12px', background: '#f8fafc', borderRadius: 8, fontSize: 13 }}>
                    <span style={{ color: '#f97316', fontWeight: 600, minWidth: 24 }}>#{scene.index}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500 }}>{scene.title}</div>
                      <div style={{ color: '#64748b', fontSize: 12, marginTop: 2 }}>
                        {scene.start_time}s → {(scene.start_time + scene.duration).toFixed(1)}s ({scene.duration}s)
                      </div>
                    </div>
                    <span style={{ color: '#64748b', fontSize: 12, alignSelf: 'center' }}>{scene.visual_style}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 项目列表 */}
        {projects.length > 0 && (
          <div className="card">
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>历史项目</h2>
            <div className="project-list">
              {projects.map(p => (
                <div key={p.id} className="project-item">
                  <div className="info">
                    <h3>{p.request.title}</h3>
                    <p>{p.request.description}</p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span className={`status-badge ${p.status}`}>
                      {p.status}
                    </span>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '6px 12px', fontSize: 12 }}
                      onClick={() => setProject(p)}
                    >
                      查看
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
