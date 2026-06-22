import { useState, useRef, useEffect, useCallback } from 'react'
import { hermes3Client, type Message as BackendMessage } from '../hermes3-client'
import { NAV_AGENT_PROMPTS } from '../App'
import { gateway } from '../gateway'

interface ChatMessage {
  role: 'user' | 'agent'
  content: string
  agentName?: string
}

interface ChatPanelProps {
  activeNav: string
  navTrigger: number
}

export function ChatPanel({ activeNav, navTrigger }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'agent',
      content: '你好！我是 hermes3.0 创作助手。请点击左侧导航栏选择要管理的创作模块，我来帮你分析和完善！',
      agentName: '主编Agent',
    },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [sessionReady, setSessionReady] = useState(false)
  const lastNavRef = useRef('')
  const agentContextRef = useRef('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 首次挂载时创建会话
  useEffect(() => {
    hermes3Client
      .createSession()
      .then(() => setSessionReady(true))
      .catch(() => setSessionReady(true))
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 左侧导航点击 → 获取 Agent 上下文 → 自动触发 AI 对话
  useEffect(() => {
    if (!sessionReady || busy || !navTrigger) return
    const prompt = NAV_AGENT_PROMPTS[activeNav]
    if (!prompt || lastNavRef.current === activeNav) return
    lastNavRef.current = activeNav

    const doNavAction = async () => {
      // 获取 Agent 专属上下文（prompt + SKILL.md）
      const agentName = getAgentForNav(activeNav)
      try {
        const ctx = await gateway.getAgentContext(agentName)
        agentContextRef.current = ctx.prompt || ''
      } catch {
        agentContextRef.current = ''
      }

      // 自动发送 AI 消息
      sendMessage(prompt, true)
    }
    const timer = setTimeout(doNavAction, 300)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navTrigger, sessionReady])

  const sendMessage = async (text: string, isAuto: boolean = false) => {
    if (busy) return
    setBusy(true)

    if (!isAuto) {
      setMessages(prev => [...prev, { role: 'user', content: text }])
    } else {
      // 自动触发时添加一个过渡提示
      setMessages(prev => [
        ...prev,
        {
          role: 'agent',
          content: `🔄 正在分析「${activeNav}」面板，请稍候...`,
          agentName: '系统',
        },
      ])
    }

    const history: BackendMessage[] = messages
      .filter(m => m.role !== 'agent' || (m.agentName !== '系统'))
      .map(m => ({ role: m.role === 'agent' ? 'assistant' : 'user', content: m.content }))

    try {
      const reply = await hermes3Client.sendMessage(text, agentContextRef.current, history)
      // 替换过渡提示为真实回复
      setMessages(prev => {
        const idx = prev.length - 1
        if (isAuto && prev[idx]?.agentName === '系统') {
          const updated = [...prev]
          updated[idx] = { role: 'agent', content: reply, agentName: getAgentForNav(activeNav) }
          return updated
        }
        return [...prev, { role: 'agent', content: reply, agentName: '主编Agent' }]
      })
    } catch {
      setMessages(prev => {
        const idx = prev.length - 1
        if (isAuto && prev[idx]?.agentName === '系统') {
          const updated = [...prev]
          updated[idx] = {
            role: 'agent',
            content: `抱歉，AI 暂时无法响应。请检查 DeepSeek API 是否配置正确。`,
            agentName: '系统',
          }
          return updated
        }
        return prev
      })
    } finally {
      setBusy(false)
    }
  }

  const handleSend = useCallback(() => {
    if (!input.trim()) return
    const text = input.trim()
    setInput('')
    void sendMessage(text, false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, busy, messages, agentContextRef.current])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="hermes3-chat-panel">
      <div className="hermes3-chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`hermes3-chat-message ${msg.role}`}>
            <div className="hermes3-chat-message-label">
              {msg.role === 'agent' ? msg.agentName || 'Agent' : '我'}
            </div>
            <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="hermes3-chat-input">
        <textarea
          className="hermes3-chat-input-field"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={sessionReady ? '输入消息（Enter 发送）...' : '正在连接 LLM...'}
          rows={2}
          disabled={!sessionReady}
        />
        <button
          className="hermes3-chat-input-send"
          onClick={handleSend}
          disabled={busy || !sessionReady}
        >
          {busy ? '⏳' : '➤'}
        </button>
      </div>
    </div>
  )
}

function getAgentForNav(nav: string): string {
  const map: Record<string, string> = {
    rules: '主编Agent',
    outline: '大纲Agent',
    characters: '人设Agent',
    worldbuilding: '世界观Agent',
    records: '主编Agent',
    skills: '主编Agent',
    solutions: '规划师Agent',
    inspiration: '脑洞Agent',
    assets: '主编Agent',
    knowledge: '主编Agent',
  }
  return map[nav] || '主编Agent'
}
