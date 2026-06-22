#!/usr/bin/env python3
"""
大纲 Agent — 创作蓝图，尽在掌握

构建小说的完整三级结构框架：全书大纲 -> 卷大纲 -> 章节大纲。
"""

from typing import Any
from hermes3.agents.base_writing_agent import WritingAgentBase


class OutlineAgent(WritingAgentBase):
    """大纲 Agent — 将零散的脑洞转化为层级清晰的小说大纲。"""

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("agent_role", "outline")
        super().__init__(**kwargs)
        self._agent_slogan = "创作蓝图，尽在掌握"
