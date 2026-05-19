import { useState, useRef, FormEvent } from 'react'
import { FileText, Upload, Play, ExternalLink, Loader } from 'lucide-react'

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
    title: string
    duration: number
    narration_text: string
    visual_style: string
  }>
  status: string
  output_path: string | null
}

function App() {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [styleKeywords, setStyleKeywords] = useState('corporate, professional, clean')
  const [sceneCount, setSceneCount] = useState(7)
  const [duration, setDuration] = useState(173)
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [project, setProject] = useState<Project | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files))
    }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    setLoading(true)
    setError('')
    setProject(null)

    try {
      const formData = new FormData()
      formData.append('title', title)
      formData.append('description', description)
      formData.append('style_keywords', styleKeywords)
      formData.append('scene_count', String(sceneCount))
      formData.append('total_duration_seconds', String(duration))
      formData.append('narration_language', 'zh-CN')

      for (const file of files) {
        formData.append('files', file)
      }

      const res = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '创建项目失败')
      }

      const data: Project = await res.json()
      setProject(data)
      setProjects(prev => [data, ...prev])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
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
            <label>需求描述</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="描述视频的目的、风格、受众..."
              rows={3}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="form-group">
              <label>风格关键词</label>
              <input
                value={styleKeywords}
                onChange={e => setStyleKeywords(e.target.value)}
                placeholder="corporate, professional, clean"
              />
            </div>
            <div className="form-group">
              <label>场景数量</label>
              <input
                type="number"
                value={sceneCount}
                onChange={e => setSceneCount(Number(e.target.value))}
                min={1}
                max={20}
              />
            </div>
          </div>

          <div className="form-group">
            <label>总时长（秒）</label>
            <input
              type="number"
              value={duration}
              onChange={e => setDuration(Number(e.target.value))}
              min={10}
              max={600}
            />
          </div>

          <div className="form-group">
            <label>上传文档素材（Word / PDF / TXT）</label>
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
                AI 正在生成视频...
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
                {project.status === 'rendered' ? '渲染完成' :
                 project.status === 'generating' ? '生成中' :
                 project.status === 'failed' ? '失败' : '待处理'}
              </span>
            </div>

            {project.output_path && (
              <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: 12, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Play size={16} color="#16a34a" />
                <span style={{ fontSize: 14 }}>视频已生成</span>
                <a
                  href={`http://localhost:8000/output/${project.output_path?.split('/').pop() || project.output_path?.split('\\').pop()}`}
                  target="_blank"
                  style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, color: '#16a34a', fontSize: 13 }}
                >
                  查看视频 <ExternalLink size={12} />
                </a>
              </div>
            )}

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
