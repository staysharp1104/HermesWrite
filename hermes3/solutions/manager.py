#!/usr/bin/env python3
"""
Solution Manager — 方案 CRUD、内置方案加载、项目级方案存储、激活切换。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from hermes3.solutions.schema import Solution, AgentConfig
from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

# 内置方案目录（随 hermes3 发布）
_BUILTIN_DIR = Path(__file__).parent / "builtin"

# 项目级方案目录
_PROJECT_SOLUTIONS_DIR = ".feelfish/solutions"


def get_project_home() -> Path:
    """获取当前项目的 hermes3 项目根目录（从 `.feelfish/` 定位）。"""
    # 从当前工作目录向上查找 `.feelfish/`
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".feelfish").is_dir():
            return parent
    # 兜底：在 CWD 下创建
    return cwd


class SolutionManager:
    """方案管理器 — 加载、创建、枚举、激活方案。"""

    def __init__(self, project_root: Optional[Path] = None):
        self._project_root = project_root or get_project_home()
        self._active_solution: Optional[Solution] = None
        self._cache: Dict[str, Solution] = {}

    # ── 内置方案 ────────────────────────────────────────────────────

    def load_builtins(self) -> Dict[str, Solution]:
        """加载所有内置方案（从 hermes3/solutions/builtin/ 加载 .yaml 文件）。"""
        solutions: Dict[str, Solution] = {}
        if not _BUILTIN_DIR.is_dir():
            logger.warning("内置方案目录不存在: %s", _BUILTIN_DIR)
            return solutions
        for fpath in sorted(_BUILTIN_DIR.glob("*.yaml")):
            try:
                sol = Solution.from_yaml(fpath.read_text(encoding="utf-8"))
                solutions[sol.name] = sol
            except Exception as exc:
                logger.error("加载内置方案失败 %s: %s", fpath.name, exc)
        return solutions

    # ── 项目级方案 ───────────────────────────────────────────────────

    def _project_solutions_dir(self) -> Path:
        return self._project_root / _PROJECT_SOLUTIONS_DIR

    def list_project_solutions(self) -> Dict[str, Solution]:
        """枚举项目级方案。"""
        sol_dir = self._project_solutions_dir()
        if not sol_dir.is_dir():
            return {}
        solutions: Dict[str, Solution] = {}
        for fpath in sorted(sol_dir.glob("*.yaml")):
            try:
                sol = Solution.from_yaml(fpath.read_text(encoding="utf-8"))
                solutions[sol.name] = sol
            except Exception as exc:
                logger.error("加载项目方案失败 %s: %s", fpath.name, exc)
        return solutions

    def get_solution(self, name: str) -> Optional[Solution]:
        """按名称获取方案（内置优先，项目级覆盖）。"""
        # 优先查缓存
        if name in self._cache:
            return self._cache[name]

        # 查内置
        builtins = self.load_builtins()
        if name in builtins:
            self._cache[name] = builtins[name]
            return builtins[name]

        # 查项目级
        project_sols = self.list_project_solutions()
        if name in project_sols:
            self._cache[name] = project_sols[name]
            return project_sols[name]

        return None

    def create_solution(self, solution: Solution) -> Path:
        """在项目级创建新方案（保存到 .feelfish/solutions/）。"""
        sol_dir = self._project_solutions_dir()
        sol_dir.mkdir(parents=True, exist_ok=True)
        fpath = sol_dir / f"{solution.name}.yaml"
        fpath.write_text(solution.to_yaml(), encoding="utf-8")
        self._cache[solution.name] = solution
        logger.info("方案已创建: %s (%s)", solution.name, fpath)
        return fpath

    def delete_solution(self, name: str) -> bool:
        """删除项目级方案。"""
        sol_dir = self._project_solutions_dir()
        fpath = sol_dir / f"{name}.yaml"
        if fpath.exists():
            fpath.unlink()
            self._cache.pop(name, None)
            return True
        return False

    # ── 激活/切换 ────────────────────────────────────────────────────

    def activate(self, name: str) -> Optional[Solution]:
        """激活指定方案。返回当前激活的方案实例。"""
        sol = self.get_solution(name)
        if sol is None:
            logger.error("方案不存在: %s", name)
            return None
        self._active_solution = sol
        logger.info("已激活方案: %s", name)
        return sol

    @property
    def active(self) -> Optional[Solution]:
        """当前激活的方案。"""
        return self._active_solution

    def deactivate(self):
        """取消激活当前方案。"""
        self._active_solution = None

    # ── 全部方案（内置+项目级） ───────────────────────────────────────

    def list_all(self) -> Dict[str, Solution]:
        """获取所有可用方案（内置 + 项目级合并）。"""
        all_sols = {}
        all_sols.update(self.load_builtins())
        all_sols.update(self.list_project_solutions())
        return all_sols
