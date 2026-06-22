#!/usr/bin/env python3
"""名字 Agent — 人名/物品/地名/势力名，命名体系规则与文化背景规范。"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class NamingAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "naming")
        super().__init__(**kw)
        self._agent_slogan = "命名巧思，万象生辉"
