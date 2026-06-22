#!/usr/bin/env python3
"""
Character Graph — 角色关系图谱。

内存中维护角色关系图（轻量 dict-based 图），支持：
- 关系查询
- 关系变化时间线
- 角色共现分析
- 导出为力导向图可用的数据格式
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from hermes_constants import get_project_home

logger = logging.getLogger(__name__)


@dataclass
class RelationEdge:
    """角色之间的单条关系。"""
    target: str          # 目标角色名
    relation: str        # 关系类型 (friend, enemy, family, lover, mentor, rivalry, etc.)
    chapter_id: str = ""  # 首次出现在哪章
    description: str = ""


@dataclass
class CharacterNode:
    """角色节点。"""
    name: str
    aliases: List[str] = field(default_factory=list)
    relations: List[RelationEdge] = field(default_factory=list)
    first_appearance: str = ""  # chapter_id
    tags: List[str] = field(default_factory=list)  # 角色标签 (主角, 反派, 配角...)


class CharacterGraph:
    """角色关系图谱 — 轻量内存图。"""

    def __init__(self, project_root: Optional[Path] = None):
        self._project_root = project_root or get_project_home()
        self._nodes: Dict[str, CharacterNode] = {}
        self._load()

    def _graph_path(self) -> Path:
        return self._project_root / ".feelfish" / "records" / "character-graph.json"

    def _load(self) -> None:
        fpath = self._graph_path()
        if fpath.exists():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                for name, ndata in data.items():
                    node = CharacterNode(name=name, aliases=ndata.get("aliases", []),
                                         tags=ndata.get("tags", []),
                                         first_appearance=ndata.get("first_appearance", ""))
                    for rdata in ndata.get("relations", []):
                        node.relations.append(RelationEdge(**rdata))
                    self._nodes[name] = node
                logger.info("已加载角色关系图 (%d 个角色, %d 条关系)",
                            len(self._nodes),
                            sum(len(n.relations) for n in self._nodes.values()))
            except Exception as exc:
                logger.warning("加载角色关系图失败: %s", exc)

    def save(self) -> None:
        fpath = self._graph_path()
        fpath.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {}
        for name, node in self._nodes.items():
            data[name] = asdict(node)
        fpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 节点操作 ────────────────────────────────────────────────────

    def add_character(self, name: str, *, aliases: Optional[List[str]] = None,
                      tags: Optional[List[str]] = None,
                      first_appearance: str = "") -> CharacterNode:
        if name not in self._nodes:
            self._nodes[name] = CharacterNode(
                name=name,
                aliases=aliases or [],
                tags=tags or [],
                first_appearance=first_appearance,
            )
        return self._nodes[name]

    def add_relation(self, source: str, target: str, relation: str,
                     chapter_id: str = "", description: str = "") -> None:
        """在 source 和 target 之间添加关系（双向存储）。"""
        src = self.add_character(source)
        self.add_character(target)

        src.relations.append(RelationEdge(
            target=target, relation=relation,
            chapter_id=chapter_id, description=description,
        ))
        self.save()

    def get_relations(self, name: str) -> List[RelationEdge]:
        node = self._nodes.get(name)
        return node.relations if node else []

    def get_character(self, name: str) -> Optional[CharacterNode]:
        return self._nodes.get(name)

    def list_characters(self) -> List[str]:
        return sorted(self._nodes.keys())

    # ── 关系检索 ────────────────────────────────────────────────────

    def find_connections(self, name: str, max_depth: int = 3) -> Dict[str, List[str]]:
        """BFS 查询角色关系链。"""
        connections: Dict[str, List[str]] = {}
        if name not in self._nodes:
            return connections
        visited = {name: []}
        queue = [(name, [])]
        while queue and len(visited) <= 50:
            current, path = queue.pop(0)
            if len(path) >= max_depth:
                continue
            node = self._nodes.get(current)
            if not node:
                continue
            for rel in node.relations:
                if rel.target not in visited:
                    new_path = path + [current]
                    visited[rel.target] = new_path
                    queue.append((rel.target, new_path))
        for other, path in visited.items():
            if other != name:
                connections[other] = path + [other]
        return connections

    def co_occurrence(self, name_a: str, name_b: str) -> int:
        """计算两个角色在同一章节的出现次数（共现度）。"""
        node_a = self._nodes.get(name_a)
        node_b = self._nodes.get(name_b)
        if not node_a or not node_b:
            return 0
        a_chapters = {r.chapter_id for r in node_a.relations if r.chapter_id}
        b_chapters = {r.chapter_id for r in node_b.relations if r.chapter_id}
        return len(a_chapters & b_chapters)

    # ── 导出 ─────────────────────────────────────────────────────────

    def export_for_viz(self) -> Dict[str, Any]:
        """导出为力导向图可视化可用的数据。"""
        nodes = []
        for name in self._nodes:
            nodes.append({"id": name, "group": 1})
        links = []
        seen: set = set()
        for name, node in self._nodes.items():
            for rel in node.relations:
                edge = tuple(sorted([name, rel.target]))
                if edge not in seen:
                    links.append({"source": name, "target": rel.target, "relation": rel.relation})
                    seen.add(edge)
        return {"nodes": nodes, "links": links}
