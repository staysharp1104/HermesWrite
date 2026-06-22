#!/usr/bin/env python3
"""词条 Agent — 道具/技能/功法/法宝数据规范。"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class EntryAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "entry")
        super().__init__(**kw)
        self._agent_slogan = "道具功法，技能法宝"
