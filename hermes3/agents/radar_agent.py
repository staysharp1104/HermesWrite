#!/usr/bin/env python3
"""
雷达 Agent — 扫描平台趋势和读者偏好，趋势研判，指引方向。
"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class RadarAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "radar")
        super().__init__(**kw)
        self._agent_slogan = "趋势研判，指引方向"
