import { useState, useEffect } from 'react'
import { gateway } from '../gateway'

const PANEL_NAMES: Record<string, string> = {
  writing: '创作工作台',
  rules: '规则管理',
  outline: '大纲管理',
  characters: '角色管理',
  worldbuilding: '世界观设定',
  records: '创作记录',
  inspiration: '灵感采集',
  assets: '资产管理',
  skills: '技能面板',
  knowledge: '知识库',
  search: '全局搜索',
  toolbox: '百宝箱',
  solutions: '方案管理',
  market: '资源市场',
  misc: '其他设置',
}

interface NavData {
  loading: boolean
  error?: string
  data: unknown
}

interface EditorPanelProps {
  activeNav: string
  onDataChange?: (nav: string, data: unknown) => void
}

export function EditorPanel({ activeNav, onDataChange }: EditorPanelProps) {
  const [title, setTitle] = useState('第一章 风起云涌')
  const [content, setContent] = useState('')
  const [navData, setNavData] = useState<NavData>({ loading: false, data: null })

  // 导航切换 → 加载后端数据
  useEffect(() => {
    if (activeNav === 'writing') return

    const loadData = async () => {
      setNavData({ loading: true, data: null })
      try {
        let result: unknown = null
        switch (activeNav) {
          case 'rules':
            result = await gateway.getRules()
            break
          case 'outline':
            result = await gateway.getOutline()
            break
          case 'characters':
            result = await gateway.getCharacters()
            break
          case 'worldbuilding':
            result = await gateway.getWorldbuilding()
            break
          case 'records':
            result = await gateway.getRecords()
            break
          case 'skills':
            result = await gateway.getSkills()
            break
          case 'solutions':
            result = await gateway.getSolutions()
            break
        }
        setNavData({ loading: false, data: result })
        onDataChange?.(activeNav, result)
      } catch (err) {
        setNavData({ loading: false, error: String(err), data: null })
      }
    }
    void loadData()
  }, [activeNav, onDataChange])

  // ── 创作工作台（默认视图） ───────────────────────
  if (activeNav === 'writing') {
    return (
      <div className="hermes3-editor">
        <div className="hermes3-editor-toolbar">
          <span>📝</span>
          <input
            className="hermes3-editor-title"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="章节标题"
          />
          <span style={{ fontSize: 11, color: '#6c7293', whiteSpace: 'nowrap' }}>
            {content.length} 字
          </span>
        </div>
        <div className="hermes3-editor-content">
          <textarea
            className="hermes3-editor-textarea"
            value={content}
            onChange={e => setContent(e.target.value)}
            placeholder="在此开始你的创作…"
          />
        </div>
      </div>
    )
  }

  // ── 管理面板（侧边栏导航） ─────────────────────
  const renderData = () => {
    if (navData.loading) {
      return <p style={{ color: '#6c7293' }}>加载中...</p>
    }
    if (navData.error) {
      return (
        <div>
          <p style={{ color: '#ef4444' }}>加载失败: {navData.error}</p>
          <p style={{ color: '#6c7293', fontSize: 13, marginTop: 8 }}>
            请确保已在 hermes3 项目目录中执行了初始化：
            <br />
            <code style={{ background: '#1a1a3e', padding: '2px 6px', borderRadius: 4 }}>
              python -m hermes3.init_project --name "你的小说" --author "作者"
            </code>
          </p>
        </div>
      )
    }

    // 根据导航项渲染不同内容
    return (
      <div style={{ fontSize: 14, lineHeight: 1.6 }}>
        {activeNav === 'rules' && renderRules(navData.data)}
        {activeNav === 'outline' && renderOutline(navData.data)}
        {activeNav === 'characters' && renderCharacters(navData.data)}
        {activeNav === 'worldbuilding' && renderWorldbuilding(navData.data)}
        {activeNav === 'records' && renderRecords(navData.data)}
        {activeNav === 'skills' && renderSkills(navData.data)}
        {activeNav === 'solutions' && renderSolutions(navData.data)}
        {activeNav === 'search' && renderSearch()}
        {activeNav === 'toolbox' && renderToolbox()}
        {activeNav === 'market' && <p>资源市场 — 后端开发中</p>}
        {activeNav === 'misc' && <p>项目设置 — 后端开发中</p>}
        {activeNav === 'inspiration' && <p>灵感采集 — 后端开发中</p>}
        {activeNav === 'assets' && <p>资产管理 — 后端开发中</p>}
        {activeNav === 'knowledge' && <p>知识库 — 后端开发中</p>}
      </div>
    )
  }

  return (
    <div className="hermes3-panel">
      <div className="hermes3-panel-header">{PANEL_NAMES[activeNav] || activeNav}</div>
      <div className="hermes3-panel-body">{renderData()}</div>
    </div>
  )
}

// ── 各面板渲染函数 ──────────────────────────────

function renderRules(data: unknown) {
  const rules = (data as { rules?: string[] })?.rules
  if (!rules || rules.length === 0) return <p style={{ color: '#6c7293' }}>暂无规则文件，请在 .feelfish/rules/ 目录中创建 .md 文件</p>
  return (
    <ul style={{ listStyle: 'none', padding: 0 }}>
      {rules.map(r => <li key={r} style={{ padding: '6px 0', borderBottom: '1px solid #2a2a4a' }}>📏 {r}</li>)}
    </ul>
  )
}

function renderOutline(data: unknown) {
  const content = (data as { content?: string })?.content
  if (!content) return <p style={{ color: '#6c7293' }}>暂无大纲，请通过对话面板让大纲 Agent 生成</p>
  return <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0 }}>{content}</pre>
}

function renderCharacters(data: unknown) {
  const chars = (data as { characters?: string[] })?.characters
  if (!chars || chars.length === 0) return <p style={{ color: '#6c7293' }}>暂无角色，请通过对话面板让人设 Agent 创建</p>
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
      {chars.map(c => (
        <div key={c} style={{ padding: 12, background: '#1a1a3e', borderRadius: 8, border: '1px solid #2a2a4a' }}>
          👤 <strong>{c}</strong>
        </div>
      ))}
    </div>
  )
}

function renderWorldbuilding(data: unknown) {
  const cats = (data as { categories?: Record<string, string[]> })?.categories
  if (!cats || Object.keys(cats).length === 0) return <p style={{ color: '#6c7293' }}>暂无世界观设定</p>
  return (
    <div>
      {Object.entries(cats).map(([cat, items]) => (
        <div key={cat} style={{ marginBottom: 16 }}>
          <h4 style={{ margin: '0 0 8px', color: '#e94560' }}>🌍 {cat}</h4>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {items.map(i => <li key={i} style={{ padding: '4px 0', color: '#a0a0b8' }}>{i}</li>)}
          </ul>
        </div>
      ))}
    </div>
  )
}

function renderRecords(data: unknown) {
  const stats = data as { sessions?: number; characters?: number }
  return (
    <div style={{ display: 'flex', gap: 16 }}>
      <div style={{ flex: 1, padding: 16, background: '#1a1a3e', borderRadius: 8, textAlign: 'center' }}>
        <div style={{ fontSize: 28, fontWeight: 700, color: '#e94560' }}>{stats?.sessions ?? 0}</div>
        <div style={{ fontSize: 12, color: '#6c7293', marginTop: 4 }}>章节</div>
      </div>
      <div style={{ flex: 1, padding: 16, background: '#1a1a3e', borderRadius: 8, textAlign: 'center' }}>
        <div style={{ fontSize: 28, fontWeight: 700, color: '#4ade80' }}>{stats?.characters ?? 0}</div>
        <div style={{ fontSize: 12, color: '#6c7293', marginTop: 4 }}>角色</div>
      </div>
    </div>
  )
}

function renderSkills(data: unknown) {
  const skills = (data as { skills?: string[] })?.skills
  if (!skills || skills.length === 0) return <p style={{ color: '#6c7293' }}>暂无技能文件</p>
  return (
    <div>
      {skills.map(s => (
        <div key={s} style={{ padding: '8px 12px', marginBottom: 8, background: '#1a1a3e', borderRadius: 8, border: '1px solid #2a2a4a' }}>
          ⚡ <strong>{s}/SKILL.md</strong>
        </div>
      ))}
    </div>
  )
}

function renderSolutions(data: unknown) {
  const sols = (data as { solutions?: string[] })?.solutions
  if (!sols || sols.length === 0) return <p style={{ color: '#6c7293' }}>暂无方案</p>
  return (
    <div>
      {sols.map(s => (
        <div key={s} style={{ padding: '8px 12px', marginBottom: 8, background: '#1a1a3e', borderRadius: 8, border: '1px solid #2a2a4a', cursor: 'pointer' }}
             onClick={() => void gateway.activateSolution(s)}>
          🎯 <strong>{s}</strong> <span style={{ fontSize: 11, color: '#6c7293', marginLeft: 8 }}>点击激活</span>
        </div>
      ))}
    </div>
  )
}

function renderSearch() {
  return (
    <div>
      <input
        style={{ width: '100%', padding: '10px 14px', background: '#0a0a23', border: '1px solid #2a2a4a', borderRadius: 8, color: '#e0e0e0', fontSize: 14, outline: 'none' }}
        placeholder="输入关键词搜索角色、世界观、章节..."
        onKeyDown={async e => {
          if (e.key === 'Enter') {
            const results = await gateway.search((e.target as HTMLInputElement).value)
            // 显示搜索结果（简化处理）
          }
        }}
      />
      <p style={{ color: '#6c7293', fontSize: 13, marginTop: 12 }}>按 Enter 搜索</p>
    </div>
  )
}

function renderToolbox() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
      {[
        { icon: '📊', name: '字数统计', desc: '全书/章节多维度统计' },
        { icon: '🔍', name: '敏感词检测', desc: '自定义词库 + 全文扫描' },
        { icon: '🎨', name: '文风分析', desc: '提取文风特征向量' },
        { icon: '📛', name: '命名生成器', desc: '人名/地名/功法名' },
        { icon: '⏱', name: '时间线工具', desc: '事件排列 + 冲突检测' },
        { icon: '✨', name: '灵感生成', desc: 'AI 生成情节灵感' },
      ].map(t => (
        <div key={t.name} style={{ padding: 16, background: '#1a1a3e', borderRadius: 8, cursor: 'pointer', border: '1px solid #2a2a4a' }}>
          <div style={{ fontSize: 20, marginBottom: 4 }}>{t.icon}</div>
          <div style={{ fontWeight: 600, fontSize: 13 }}>{t.name}</div>
          <div style={{ fontSize: 11, color: '#6c7293', marginTop: 2 }}>{t.desc}</div>
        </div>
      ))}
    </div>
  )
}
