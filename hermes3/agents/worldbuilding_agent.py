#!/usr/bin/env python3
"""世界观 Agent — 虚构天地，成就奇想。"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class WorldbuildingAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "worldbuilding")
        super().__init__(**kw)
        self._agent_slogan = "虚构天地，成就奇想"
