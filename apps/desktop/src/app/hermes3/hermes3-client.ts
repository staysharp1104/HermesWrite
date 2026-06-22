/** hermes3 后端通信服务 — 通过 Electron IPC 直连 LLM API */

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

declare global {
  interface HermesDesktop {
    hermes3Chat: (messages: Message[]) => Promise<{ choices?: Array<{ message: { content: string } }>; error?: string }>
  }
}

function getHd(): HermesDesktop | null {
  return (window as unknown as { hermesDesktop?: HermesDesktop }).hermesDesktop ?? null
}

export class Hermes3Client {
  private _sessionId: string | null = null

  get sessionId(): string | null {
    return this._sessionId
  }

  setSessionId(id: string): void {
    this._sessionId = id
  }

  async createSession(): Promise<{ id: string }> {
    const id = `hermes3-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    this._sessionId = id
    return { id }
  }

  /**
   * 发送消息给 AI，使用动态 agentContext 作为 system prompt
   * @param text 用户消息
   * @param agentContext Agent 的完整上下文（prompt + SKILL.md），作为 system message
   * @param history 对话历史
   */
  async sendMessage(
    text: string,
    agentContext: string = '',
    history: Message[] = [],
  ): Promise<string> {
    // 构建 system message：agentContext + 通用指令
    const systemContent = agentContext
      ? `${agentContext}\n\n请根据以上角色定义和技能规范来回答用户的问题。回答要专业、具体、有创意。`
      : `你是一个专业的小说创作AI助手，名为 hermes3.0。请根据用户的需求，扮演最合适的角色进行回应。回答要专业、具体、有创意。`

    const messages: Message[] = [
      { role: 'system', content: systemContent },
      ...history,
      { role: 'user' as const, content: text },
    ]

    const hd = getHd()
    if (hd?.hermes3Chat) {
      const result = await hd.hermes3Chat(messages)
      if (result.error) throw new Error(result.error)
      return result.choices?.[0]?.message?.content || ''
    }

    // Fallback: 直接 fetch
    const res = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer sk-e73e7922534b448e9de4c9e301fbc7e6',
      },
      body: JSON.stringify({ model: 'deepseek-chat', messages, max_tokens: 4096, temperature: 0.8 }),
    })
    if (!res.ok) {
      const errText = await res.text().catch(() => res.statusText)
      throw new Error(`DeepSeek API error: ${res.status} ${errText}`)
    }
    const data = await res.json()
    return data.choices?.[0]?.message?.content || ''
  }
}

export const hermes3Client = new Hermes3Client()
