import { useState } from 'react'

export interface NavItem {
  id: string
  label: string
  icon: string
  group: string
}

export const NAV_ITEMS: NavItem[] = [
  // 创作类
  { id: 'rules', label: '规则', icon: '📏', group: '创作' },
  { id: 'outline', label: '大纲', icon: '📋', group: '创作' },
  { id: 'characters', label: '角色管理', icon: '👤', group: '创作' },
  { id: 'worldbuilding', label: '世界观设定', icon: '🌍', group: '创作' },
  { id: 'records', label: '记录', icon: '📝', group: '创作' },
  { id: 'inspiration', label: '灵感', icon: '💡', group: '创作' },
  // 资产类
  { id: 'assets', label: '资产', icon: '📦', group: '资产' },
  { id: 'skills', label: '技能', icon: '⚡', group: '资产' },
  { id: 'knowledge', label: '知识库', icon: '📚', group: '资产' },
  // 工具类
  { id: 'search', label: '搜索', icon: '🔍', group: '工具' },
  { id: 'toolbox', label: '百宝箱', icon: '🧰', group: '工具' },
  { id: 'solutions', label: '方案', icon: '🎯', group: '工具' },
  { id: 'market', label: '市场', icon: '🏪', group: '工具' },
  // 其他
  { id: 'misc', label: '其他', icon: '⚙️', group: '其他' },
]

interface SidebarProps {
  activeNav: string
  onNavChange: (id: string) => void
  onBackToNormal: () => void
}

export function Hermes3Sidebar({ activeNav, onNavChange, onBackToNormal }: SidebarProps) {
  const groups = [...new Set(NAV_ITEMS.map(n => n.group))]

  return (
    <div className="hermes3-sidebar">
      <div className="hermes3-sidebar-header">
        <span>✍️</span>
        <span>hermes3.0</span>
      </div>

      {groups.map(group => (
        <div key={group} className="hermes3-sidebar-group">
          <div className="hermes3-sidebar-group-title">{group}</div>
          {NAV_ITEMS.filter(n => n.group === group).map(item => (
            <div
              key={item.id}
              className={`hermes3-nav-item ${activeNav === item.id ? 'active' : ''}`}
              onClick={() => onNavChange(item.id)}
            >
              <span className="hermes3-nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </div>
          ))}
        </div>
      ))}

      <div style={{ flex: 1 }} />
      <div
        className="hermes3-nav-item"
        onClick={onBackToNormal}
        style={{ borderTop: '1px solid var(--border-color, #2a2a4a)', marginTop: 0 }}
      >
        <span className="hermes3-nav-icon">↩</span>
        <span>返回通用界面</span>
      </div>
    </div>
  )
}
