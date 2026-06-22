#!/usr/bin/env python3
"""主编 Agent — 通用内容审核与质量把控，校准内容，严控品质。"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class ChiefAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "chief")
        super().__init__(**kw)
        self._agent_slogan = "校准内容，严控品质"
