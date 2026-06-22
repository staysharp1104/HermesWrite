#!/usr/bin/env python3
"""
Retrieval — 语义检索与上下文注入引擎。

创作时自动从小说记忆中检索：当前章节相关的角色设定、世界观、前文摘要，
以 volatile 层注入 system prompt，不破坏 prompt cache。

百万字策略：滑动窗口 + 语义检索 + 章节摘要链。
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_constants import get_project_home
from hermes3.context_engine.novel_memory import NovelMemory
from hermes3.context_engine.chapter_index import ChapterIndex
from hermes3.context_engine.character_graph import CharacterGraph

logger = logging.getLogger(__name__)


class ContextRetriever:
    """上下文检索器 — 为创作 Agent 提供相关背景信息。"""

    def __init__(self, project_root: Optional[Path] = None):
        self._project_root = project_root or get_project_home()
        self._memory = NovelMemory(self._project_root)
        self._index = ChapterIndex(self._project_root)
        self._graph = CharacterGraph(self._project_root)

    # ── 检索策略 ────────────────────────────────────────────────────

    def retrieve_for_chapter(
        self,
        volume_id: str,
        chapter_id: str,
        query: str = "",
        max_tokens: int = 4000,
    ) -> str:
        """为创作指定章节检索上下文（组装为文本块返回）。"""
        parts: List[str] = []

        # 1) 前文摘要（最近的 3 章）
        prev_summaries = self._get_previous_summaries(volume_id, chapter_id, count=3)
        if prev_summaries:
            parts.append("## 前文摘要\n" + "\n".join(prev_summaries))

        # 2) 与本内容最相关的人物设定
        if query:
            char_names = self._find_relevant_characters(query, limit=5)
            for name in char_names:
                note = self._memory.get_character_note(name)
                if note:
                    parts.append(f"## 角色参考：{name}\n{note[:500]}")

        # 3) 全局设定（所有 key-value）
        settings = self._memory._state.global_settings
        if settings:
            settings_text = "\n".join(f"- **{k}**: {v}" for k, v in settings.items())
            parts.append("## 全局设定\n" + settings_text)

        # 4) 角色关系摘要（查询中的角色）
        if query:
            for name in char_names[:3]:
                relations = self._graph.get_relations(name)
                if relations:
                    rel_text = "\n".join(
                        f"- {r.relation} → {r.target} ({r.description[:60]})"
                        for r in relations[:5]
                    )
                    parts.append(f"## {name} 的关系网络\n{rel_text}")

        combined = "\n\n".join(parts)

        # 如果超出 token 预算，截断最长的部分
        if len(combined) > max_tokens * 4:  # 粗略估算：1 token ≈ 4 chars
            combined = combined[: max_tokens * 4]
            combined += "\n\n[注意：上下文已截断以控制 token 预算]"

        return combined

    def _get_previous_summaries(self, volume_id: str, chapter_id: str, count: int = 3) -> List[str]:
        """获取当前章节之前最近 count 章的摘要。"""
        try:
            ch_num = int(chapter_id.replace("ch-", ""))
            summaries = []
            for i in range(max(1, ch_num - count), ch_num):
                prev = f"ch-{i:03d}"
                entry = self._index.get_chapter_index(volume_id, prev)
                if entry and entry.get("summary"):
                    summaries.append(f"**第{i}章 {entry.get('title', '')}**: {entry['summary'][:300]}")
            return summaries
        except (ValueError, IndexError):
            return []

    def _find_relevant_characters(self, query: str, limit: int = 5) -> List[str]:
        """从查询文本中提取相关角色（简单关键词匹配）。"""
        all_chars = self._graph.list_characters()
        if not all_chars:
            return []
        q = query.lower()
        scored = []
        for name in all_chars:
            score = 0
            if name.lower() in q:
                score += 10
            # 检查角色备注是否命中查询
            note = self._memory.get_character_note(name)
            if note and q in note.lower():
                score += 5
            if score > 0:
                scored.append((score, name))
        scored.sort(reverse=True)
        return [name for _, name in scored[:limit]]

    # ── 日志和统计 ──────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """返回检索引擎的统计信息。"""
        return {
            "characters": len(self._graph.list_characters()),
            "global_settings": len(self._memory._state.global_settings),
            "volumes": len(self._memory._state.volumes),
        }
