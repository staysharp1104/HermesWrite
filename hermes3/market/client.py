#!/usr/bin/env python3
"""
Market — 资源市场客户端。

方案/智能体/技能三类资源的发布、搜索、下载、导入。
本地缓存 + 版本检查。
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_constants import get_project_home

logger = logging.getLogger(__name__)

_MARKET_CACHE_DIR = ".feelfish/market_cache"


class ResourceType:
    SOLUTION = "solution"
    AGENT = "agent"
    SKILL = "skill"


class MarketClient:
    """资源市场客户端 — 支持方案、智能体、技能三类资源的管理。"""

    def __init__(self, project_root: Optional[Path] = None):
        self._project_root = project_root or get_project_home()
        self._cache_dir = self._project_root / _MARKET_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ── 本地资源管理 ─────────────────────────────────────────────────

    def list_local_resources(self, resource_type: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """枚举本地项目中的资源。"""
        result: Dict[str, List[Dict[str, Any]]] = {
            "solutions": [],
            "agents": [],
            "skills": [],
        }

        feelfish = self._project_root / ".feelfish"

        # 方案
        sol_dir = feelfish / "solutions"
        if sol_dir.is_dir():
            for f in sol_dir.glob("*.yaml"):
                result["solutions"].append({
                    "name": f.stem, "type": "solution",
                    "path": str(f), "size": f.stat().st_size,
                })

        # 自定义智能体
        agents_dir = feelfish / "agents"
        if agents_dir.is_dir():
            for f in agents_dir.glob("*.md"):
                result["agents"].append({
                    "name": f.stem, "type": "agent",
                    "path": str(f), "size": f.stat().st_size,
                })

        # 技能
        skills_dir = feelfish / "skills"
        if skills_dir.is_dir():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists():
                        result["skills"].append({
                            "name": skill_dir.name, "type": "skill",
                            "path": str(skill_md), "size": skill_md.stat().st_size,
                        })

        if resource_type:
            return {resource_type: result.get(resource_type, [])}
        return result

    def export_resource(self, name: str, resource_type: str,
                        target_path: Path) -> Dict[str, Any]:
        """导出自有资源为可分享的文件。"""
        feelfish = self._project_root / ".feelfish"
        source_map = {
            ResourceType.SKILL: feelfish / "skills" / name / "SKILL.md",
            ResourceType.SOLUTION: feelfish / "solutions" / f"{name}.yaml",
            ResourceType.AGENT: feelfish / "agents" / f"{name}.md",
        }
        src = source_map.get(resource_type)
        if src is None or not src.exists():
            return {"success": False, "error": f"{resource_type} '{name}' not found"}

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(src, "r", encoding="utf-8") as f_in:
            with open(target_path, "w", encoding="utf-8") as f_out:
                f_out.write(f"# Type: {resource_type}\n")
                f_out.write(f"# Name: {name}\n")
                f_out.write(f_in.read())
        return {"success": True, "path": str(target_path)}

    def import_resource(self, source_path: Path) -> Dict[str, Any]:
        """从文件导入资源到本地项目。"""
        if not source_path.exists():
            return {"success": False, "error": f"File not found: {source_path}"}

        content = source_path.read_text(encoding="utf-8")
        # 解析头部元数据
        resource_type = ""
        name = source_path.stem
        for line in content.splitlines():
            if line.startswith("# Type:"):
                resource_type = line.replace("# Type:", "").strip()
            elif line.startswith("# Name:"):
                name = line.replace("# Name:", "").strip()

        if not resource_type:
            return {"success": False, "error": "Missing # Type: header in resource file"}

        feelfish = self._project_root / ".feelfish"
        target_map = {
            ResourceType.SKILL: feelfish / "skills" / name / "SKILL.md",
            ResourceType.SOLUTION: feelfish / "solutions" / f"{name}.yaml",
            ResourceType.AGENT: feelfish / "agents" / f"{name}.md",
        }
        target = target_map.get(resource_type)
        if target is None:
            return {"success": False, "error": f"Unknown resource type: {resource_type}"}

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("已导入 %s: %s -> %s", resource_type, name, target)
        return {"success": True, "type": resource_type, "name": name, "path": str(target)}
