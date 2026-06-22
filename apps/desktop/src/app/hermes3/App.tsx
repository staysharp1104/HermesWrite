import { useState, useCallback, useRef } from 'react'
import './hermes3.css'
import { Hermes3Sidebar } from './sidebar'
import { EditorPanel } from './editor'
import { ChatPanel } from './chat-panel'
import { AgentStatus } from './agent-status'

interface Hermes3AppProps {
  onBackToNormal: () => void
}

/** 导航项 → AI Agent 触发消息映射 */
export const NAV_AGENT_PROMPTS: Record<string, string> = {
  rules: '请作为**主编Agent**，查看当前项目的写作规则。列出 .feelfish/rules/ 目录下已有的规则文件，检查是否有缺失，并给出完善建议。',
  outline: '请作为**大纲Agent**，分析当前项目的大纲结构。阅读 .feelfish/outline/ 中的大纲文档，评估完整性，并给出优化建议。如果大纲尚未创建，请协助生成一份初步大纲。',
  characters: '请作为**人设Agent**，查看当前项目的角色档案。阅读 .feelfish/characters/ 下的角色文件，分析角色设定的完整性（外貌、性格、背景、动机、人物弧光），指出缺失项并给出补充建议。',
  worldbuilding: '请作为**世界观Agent**，查看当前项目的世界观设定。阅读 .feelfish/worldbuilding/ 下的设定文档，评估设定的完整性和一致性，给出完善建议。',
  records: '请统计当前项目的创作数据：字数、章节数、角色数量，生成一份简洁的创作进度报告。',
  skills: '请检查 .feelfish/skills/ 目录下的技能文件，列出每个 Agent 对应的 SKILL.md，评估是否需要补充或优化。',
  solutions: '请列出当前可用的创作方案（Solution），说明每个方案的适用场景，并推荐最适合当前项目的方案。',
  search: '',
  toolbox: '',
  inspiration: '请作为**脑洞Agent**，为当前小说项目提供一些创新的情节灵感、人物设定或世界观元素。',
  assets: '请检查 .feelfish/assets/ 目录下的项目资产，列出可用的图片、音频等资源。',
  knowledge: '请查看 .feelfish/knowledge/ 目录下的参考资料，评估知识库的完整性。',
  market: '',
  misc: '',
}

export function Hermes3App({ onBackToNormal }: Hermes3AppProps) {
  const [activeNav, setActiveNav] = useState('writing')
  const navTriggerRef = useRef(0)

  const handleNavChange = useCallback((id: string) => {
    setActiveNav(id)
    // 递增触发器，ChatPanel 通过这个变化感知导航切换
    navTriggerRef.current += 1
  }, [])

  return (
    <div className="hermes3-layout">
      {/* 左侧导航栏 */}
      <Hermes3Sidebar
        activeNav={activeNav}
        onNavChange={handleNavChange}
        onBackToNormal={onBackToNormal}
      />

      {/* 中间文稿编辑器 / 管理面板 */}
      <EditorPanel activeNav={activeNav} />

      {/* 右侧栏：对话面板 + 智能体状态 */}
      <div className="hermes3-right-panel">
        <ChatPanel activeNav={activeNav} navTrigger={navTriggerRef.current} />
        <AgentStatus />
      </div>
    </div>
  )
}
