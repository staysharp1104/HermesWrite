#!/usr/bin/env python3
"""书名 Agent — 爆款书名，超级吸量。爆款书名模型与市场匹配规则。"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class TitleAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "title")
        super().__init__(**kw)
        self._agent_slogan = "爆款书名，超级吸量"
