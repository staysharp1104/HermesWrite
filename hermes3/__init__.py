#!/usr/bin/env python3
"""
hermes3 — 小说垂直 AI 创作客户端扩展包

三层核心架构：
  - Solution 方案层  : hermes3/solutions/
  - Agent 智能体层   : hermes3/agents/
  - Skill 技能层     : .feelfish/skills/ <-> hermes3/agents/
"""

from .solutions.schema import Solution, AgentConfig
from .solutions.manager import SolutionManager

__all__ = ["Solution", "AgentConfig", "SolutionManager"]
