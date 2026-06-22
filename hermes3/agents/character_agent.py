#!/usr/bin/env python3
"""
人设 Agent — 妙笔人设，轻松生成

创作立体丰满的小说人物档案，多维构建有深度、有弧光的人物设定。
"""

from typing import Any
from hermes3.agents.base_writing_agent import WritingAgentBase


class CharacterAgent(WritingAgentBase):
    """人设 Agent — 构建多维度人物档案，设计人物弧光与关系网络。"""

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("agent_role", "character")
        super().__init__(**kwargs)
        self._agent_slogan = "妙笔人设，轻松生成"
