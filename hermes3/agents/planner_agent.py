#!/usr/bin/env python3
"""规划师 Agent — 拆解作者意图与章节焦点，统筹全局，定准章节。"""
from hermes3.agents.base_writing_agent import WritingAgentBase


class PlannerAgent(WritingAgentBase):
    def __init__(self, **kw):
        kw.setdefault("agent_role", "planner")
        super().__init__(**kw)
        self._agent_slogan = "统筹全局，定准章节"
