#!/usr/bin/env python3
"""
Base Writing Agent — 所有小说创作 Agent 的基类。

提供：
- 自动加载对应 SKILL.md（`.feelfish/skills/<agent-name>/SKILL.md`）
- 专属 system prompt 加载（`hermes3/agents/prompts/<agent-name>.md`）
- 统一的 Agent 元信息接口（名称、slogan、描述）
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from run_agent import AIAgent
from hermes3.solutions.schema import AgentRole

logger = logging.getLogger(__name__)

# 内置 SKILL.md 目录
_BUILTIN_SKILLS_DIR = Path(__file__).parent.parent / "skills"


class WritingAgentBase(AIAgent):
    """小说创作 Agent 基类。

    usage::
        agent = WritingAgentBase(agent_role="brainstorm", ...)
        agent.run_conversation("生成一个穿越题材的脑洞")
    """

    def __init__(
        self,
        agent_role: str = "",
        **kwargs: Any,
    ):
        self._agent_role = agent_role
        self._agent_slogan = ""

        # 加载专属 system prompt（如存在）
        prompt_text = self._load_prompt()
        if prompt_text:
            kwargs.setdefault("ephemeral_system_prompt", prompt_text)

        # 加载对应 SKILL.md（如存在）
        self._skill_content: Optional[str] = None
        self._skill_path: Optional[Path] = None

        super().__init__(**kwargs)

        # 附加技能内容到 system prompt（如果父类未设置 prompt，则设置）
        if self._skill_content and not prompt_text:
            kwargs.setdefault("ephemeral_system_prompt", self._skill_content)
            super().__init__(**kwargs)

    # ── 元信息接口 ───────────────────────────────────────────────────

    @property
    def agent_role(self) -> str:
        return self._agent_role

    @property
    def slogan(self) -> str:
        return self._agent_slogan

    @property
    def skill_content(self) -> Optional[str]:
        return self._skill_content

    @property
    def skill_path(self) -> Optional[Path]:
        return self._skill_path

    # ── Prompt 加载 ──────────────────────────────────────────────────

    def _load_prompt(self) -> Optional[str]:
        """从 `hermes3/agents/prompts/<agent-role>.md` 加载专属 prompt。"""
        if not self._agent_role:
            return None
        prompt_dir = Path(__file__).parent / "prompts"
        fpath = prompt_dir / f"{self._agent_role}.md"
        if fpath.is_file():
            content = fpath.read_text(encoding="utf-8")
            logger.debug("已加载 prompt: %s", fpath)
            return content
        logger.debug("Agent prompt 不存在: %s", fpath)
        return None

    # ── SKILL.md 自动加载 ────────────────────────────────────────────

    def _resolve_skill_path(self) -> Optional[Path]:
        """按查找链加载 SKILL.md：
        项目 .feelfish/skills/<agent-role>/SKILL.md
          -> 全局 ~/.hermes/skills/<agent-role>/SKILL.md
          -> 内置 hermes3/skills/<agent-role>/SKILL.md
        """
        if not self._agent_role:
            return None

        agent_name = self._agent_role

        # 1) 项目级
        project_path = Path.cwd() / ".feelfish" / "skills" / agent_name / "SKILL.md"
        if project_path.is_file():
            return project_path

        # 2) 全局级
        global_path = Path.home() / ".hermes" / "skills" / agent_name / "SKILL.md"
        if global_path.is_file():
            return global_path

        # 3) 内置级
        builtin_path = _BUILTIN_SKILLS_DIR / agent_name / "SKILL.md"
        if builtin_path.is_file():
            return builtin_path

        return None

    def load_skill(self) -> None:
        """显式加载 SKILL.md（init 中已自动调用）。"""
        fpath = self._resolve_skill_path()
        if fpath is None:
            logger.debug("未找到 Agent '%s' 对应的 SKILL.md", self._agent_role)
            return
        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("读取 SKILL.md 失败 %s: %s", fpath, exc)
            return

        self._skill_path = fpath
        self._skill_content = content
        logger.info("已加载 SKILL.md: %s (%d chars)", fpath, len(content))

        # 追加到 system prompt（通过 mutation 方式注入）
        existing = getattr(self, "_cached_system_prompt", "") or ""
        combined = existing + "\n\n## 技能定义\n\n" + content
        self._cached_system_prompt = combined
