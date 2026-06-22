#!/usr/bin/env python3
"""简介 Agent — 期待拉满，万量可期。简介结构模板与期待感设计方法。"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class SynopsisAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "synopsis")
        super().__init__(**kw)
        self._agent_slogan = "期待拉满，万量可期"
