#!/usr/bin/env python3
"""
脑洞 Agent — 突破想象，脑洞大开

为小说创作提供突破性的核心创意点。
"""

from typing import Any
from hermes3.agents.base_writing_agent import WritingAgentBase


class BrainstormAgent(WritingAgentBase):
    """脑洞 Agent — 从跨领域组合中生成新颖的故事核心。"""

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("agent_role", "brainstorm")
        super().__init__(**kwargs)
        self._agent_slogan = "突破想象，脑洞大开"
