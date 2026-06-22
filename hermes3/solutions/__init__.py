# hermes3.solutions — 方案管理器
from .schema import Solution, AgentConfig, AgentRole
from .manager import SolutionManager, get_project_home

__all__ = ["Solution", "AgentConfig", "AgentRole", "SolutionManager", "get_project_home"]
