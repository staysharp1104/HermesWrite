#!/usr/bin/env python3
"""金手指 Agent — 情节神转，尽在指间。"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class GoldenFingerAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "golden_finger")
        super().__init__(**kw)
        self._agent_slogan = "情节神转，尽在指间"
