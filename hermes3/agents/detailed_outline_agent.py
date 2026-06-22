#!/usr/bin/env python3
"""细纲 Agent — 条理分明，轻松创作。章节级细纲分解与驱动规则。"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class DetailedOutlineAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "detailed_outline")
        super().__init__(**kw)
        self._agent_slogan = "条理分明，轻松创作"
