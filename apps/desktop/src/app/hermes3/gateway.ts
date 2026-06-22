/**
 * Hermes3 Gateway — JSON-RPC 通信服务
 *
 * 通过 Electron IPC → FastAPI REST → hermes3 Python 模块
 * 实现"左侧点击 → 中间展示"的数据流。
 */

export interface NavPanelData {
  rules?: string[]
  outline?: string[]
  characters?: string[]
  worldbuilding?: string[]
  records?: { words: number; sessions: number }
  inspiration?: number
  assets?: string[]
  skills?: string[]
  knowledge?: string[]
  search?: { query: string; results: unknown[] }
  toolbox?: string[]
  solutions?: string[]
  market?: string[]
}

type Hd = {
  api: <T>(req: { path: string; method?: string; body?: unknown }) => Promise<T>
  [k: string]: unknown
}

function hd(): Hd | null {
  return (window as unknown as { hermesDesktop?: Hd }).hermesDesktop ?? null
}

export class Hermes3Gateway {
  /** 通用 JSON-RPC 调用 */
  async call<T = unknown>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    const gateway = hd()
    if (!gateway) {
      throw new Error('hermesDesktop not available')
    }
    // 通过 HTTP REST 代理到 Python 后端
    const result = await gateway.api<T>({
      path: `/api/hermes3/${method}`,
      method: 'POST',
      body: params,
    })
    return result
  }

  // ── 创作类面板 ──────────────────────────────────

  /** 获取规则列表 */
  async getRules(): Promise<string[]> {
    return this.call<string[]>('rules.list')
  }

  /** 获取大纲树 */
  async getOutline(): Promise<any> {
    return this.call('outline.get')
  }

  /** 获取角色列表 */
  async getCharacters(): Promise<string[]> {
    return this.call<string[]>('characters.list')
  }

  /** 获取世界观分类树 */
  async getWorldbuilding(): Promise<Record<string, string[]>> {
    return this.call<Record<string, string[]>>('worldbuilding.list')
  }

  /** 获取创作统计 */
  async getRecords(): Promise<{ words: number; sessions: number }> {
    return this.call('records.stats')
  }

  // ── 资产类面板 ──────────────────────────────────

  /** 获取技能列表 */
  async getSkills(): Promise<string[]> {
    return this.call<string[]>('skills.list')
  }

  /** 全局搜索 */
  async search(query: string): Promise<{ results: unknown[] }> {
    return this.call('search', { query })
  }

  // ── Solution 方案 ────────────────────────────────

  /** 获取方案列表 */
  async getSolutions(): Promise<string[]> {
    return this.call<string[]>('solutions.list')
  }

  /** 激活方案 */
  async activateSolution(name: string): Promise<boolean> {
    return this.call<boolean>('solutions.activate', { name })
  }

  // ── Agent 上下文 ────────────────────────────────

  /** 获取 Agent 的完整上下文（prompt + SKILL.md） */
  async getAgentContext(agent: string): Promise<{ agent: string; prompt: string }> {
    return this.call('agent.context', { agent })
  }
}

export const gateway = new Hermes3Gateway()
