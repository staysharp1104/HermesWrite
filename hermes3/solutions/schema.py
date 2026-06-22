#!/usr/bin/env python3
"""
Solution 数据模型 — 方案是 Agent 组合 + 角色分工 + 技能绑定 + 模型选择的
完整工作流定义。
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Agent 在方案中的角色分工。"""
    CHIEF = "chief"            # 主编 Agent — 终审
    PLANNER = "planner"        # 规划师 Agent — 意图拆解
    RADAR = "radar"            # 雷达 Agent — 趋势研判
    BRAINSTORM = "brainstorm"  # 脑洞 Agent
    WORLDBUILDING = "worldbuilding"  # 世界观 Agent
    CHARACTER = "character"    # 人设 Agent
    GOLDEN_FINGER = "golden_finger"  # 金手指 Agent
    ENTRY = "entry"            # 词条 Agent
    NAMING = "naming"          # 名字 Agent
    OUTLINE = "outline"        # 大纲 Agent
    DETAILED_OUTLINE = "detailed_outline"  # 细纲 Agent
    GOLDEN_OPENING = "golden_opening"  # 黄金开篇 Agent
    TITLE = "title"            # 书名 Agent
    SYNOPSIS = "synopsis"      # 简介 Agent


class AgentConfig(BaseModel):
    """单个 Agent 在方案中的配置。"""
    role: AgentRole
    enabled: bool = True
    model_override: Optional[str] = None          # 绑定指定大模型
    skill_ids: List[str] = Field(default_factory=list)  # 绑定技能 ID 列表
    extra_prompt: Optional[str] = None            # 用户额外提示


class Solution(BaseModel):
    """方案 — 一个完整的工作流定义。"""
    name: str
    description: str
    version: str = "1.0"
    agents: List[AgentConfig] = Field(
        default_factory=lambda: _default_agent_list()
    )
    default_model: str = "deepseek-chat"
    agent_model_overrides: Dict[str, str] = Field(default_factory=dict)

    def to_yaml(self) -> str:
        """导出为 YAML 格式的配置文件。"""
        import yaml
        return yaml.dump(
            self.model_dump(mode='json'),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, content: str) -> "Solution":
        """从 YAML 内容加载方案。"""
        import yaml
        data = yaml.safe_load(content)
        return cls(**data)


def _default_agent_list() -> list:
    """返回默认 Agent 配置列表（全部启用，不含 model_override）。"""
    return [AgentConfig(role=r) for r in AgentRole]
