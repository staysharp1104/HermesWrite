// 14 个 Agent 的状态定义
const AGENTS = [
  { id: 'radar', name: '雷达Agent', layer: '顶层调度', status: 'idle' as const },
  { id: 'planner', name: '规划师Agent', layer: '顶层调度', status: 'idle' as const },
  { id: 'chief', name: '主编Agent', layer: '顶层调度', status: 'active' as const },
  { id: 'brainstorm', name: '脑洞Agent', layer: '底层设定', status: 'idle' as const },
  { id: 'worldbuilding', name: '世界观Agent', layer: '底层设定', status: 'idle' as const },
  { id: 'character', name: '人设Agent', layer: '底层设定', status: 'idle' as const },
  { id: 'golden_finger', name: '金手指Agent', layer: '底层设定', status: 'idle' as const },
  { id: 'entry', name: '词条Agent', layer: '底层设定', status: 'idle' as const },
  { id: 'naming', name: '名字Agent', layer: '底层设定', status: 'idle' as const },
  { id: 'outline', name: '大纲Agent', layer: '剧情框架', status: 'idle' as const },
  { id: 'detailed_outline', name: '细纲Agent', layer: '剧情框架', status: 'idle' as const },
  { id: 'golden_opening', name: '黄金开篇Agent', layer: '剧情框架', status: 'idle' as const },
  { id: 'title', name: '书名Agent', layer: '流量包装', status: 'idle' as const },
  { id: 'synopsis', name: '简介Agent', layer: '流量包装', status: 'idle' as const },
]

const STATUS_DOT: Record<string, string> = {
  idle: 'idle',
  active: 'active',
  busy: 'busy',
  error: 'error',
}

export function AgentStatus() {
  return (
    <div className="hermes3-agent-status">
      <div className="hermes3-agent-status-title">智能体状态</div>
      {AGENTS.map(agent => (
        <div key={agent.id} className="hermes3-agent-row">
          <span className={`hermes3-agent-dot ${STATUS_DOT[agent.status]}`} />
          <span className="hermes3-agent-name">{agent.name}</span>
          <span className="hermes3-agent-status-text">{agent.status}</span>
        </div>
      ))}
    </div>
  )
}
