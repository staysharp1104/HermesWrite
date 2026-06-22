#!/usr/bin/env python3
"""
Novel Memory — 小说级分层记忆管理。

作为 MemoryProvider 插件集成到现有的 agent/memory_manager.py 中。

分层结构：
  - 全局设定层：世界观、核心规则、不变设定（全书维度）
  - 卷级记忆层：卷级摘要、主要事件、角色出场状态（卷维度）
  - 章节级记忆层：章节摘要、关键对话、伏笔记录（章维度）

自动从章节内容中提取：角色出场、设定变更、伏笔埋设。
"""

from __future__ import annotations
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from hermes_constants import get_project_home

logger = logging.getLogger(__name__)

# ── 数据模型 ───────────────────────────────────────────────────────


@dataclass
class ChapterMemory:
    """章节级记忆。"""
    chapter_id: str                        # ch-001
    title: str = ""
    summary: str = ""                      # AI 生成的摘要
    word_count: int = 0
    characters_appeared: List[str] = field(default_factory=list)  # 出场角色
    key_events: List[str] = field(default_factory=list)           # 关键事件
    foreshadowing: List[str] = field(default_factory=list)        # 伏笔
    plot_points: List[str] = field(default_factory=list)          # 剧情节点


@dataclass
class VolumeMemory:
    """卷级记忆。"""
    volume_id: str                         # vol-01
    title: str = ""
    summary: str = ""
    chapters: Dict[str, ChapterMemory] = field(default_factory=dict)


@dataclass
class NovelMemoryState:
    """全局小说记忆状态。"""
    novel_name: str = ""
    volumes: Dict[str, VolumeMemory] = field(default_factory=dict)
    global_settings: Dict[str, str] = field(default_factory=dict)  # 全局设定
    character_notes: Dict[str, str] = field(default_factory=dict)  # 角色备注
    timeline_events: List[Tuple[str, str]] = field(default_factory=list)  # (chapter_id, event)


class NovelMemory:
    """小说级记忆管理器——自动提取、索引、检索全书记忆。"""

    def __init__(self, project_root: Optional[Path] = None):
        self._project_root = project_root or get_project_home()
        self._state = NovelMemoryState()
        self._dirty = False
        self._load()

    # ── 持久化 ──────────────────────────────────────────────────────

    def _memory_path(self) -> Path:
        return self._project_root / ".feelfish" / "records" / "novel-memory.json"

    def _load(self) -> None:
        fpath = self._memory_path()
        if fpath.exists():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                self._state = NovelMemoryState(**data)
                # Reconstruct nested dataclasses
                for vid, vdata in data.get("volumes", {}).items():
                    vol = VolumeMemory(**vdata)
                    for cid, cdata in vdata.get("chapters", {}).items():
                        vol.chapters[cid] = ChapterMemory(**cdata)
                    self._state.volumes[vid] = vol
                logger.info("已加载小说记忆 (%d 卷, %d 角色备注)",
                            len(self._state.volumes), len(self._state.character_notes))
            except Exception as exc:
                logger.warning("加载小说记忆失败: %s", exc)

    def save(self) -> None:
        fpath = self._memory_path()
        fpath.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self._state)
        fpath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._dirty = False
        logger.info("已保存小说记忆 (%d 卷)", len(self._state.volumes))

    # ── 章节级操作 ──────────────────────────────────────────────────

    def record_chapter(
        self,
        volume_id: str,
        chapter_id: str,
        title: str = "",
        content: str = "",
    ) -> ChapterMemory:
        """记录并分析一章内容，自动提取元数据。"""
        vol = self._state.volumes.setdefault(
            volume_id, VolumeMemory(volume_id=volume_id)
        )
        # 自动提取
        chars = self._extract_characters(content)
        events = self._extract_key_events(content)
        foreshadowing = self._extract_foreshadowing(content)

        mem = ChapterMemory(
            chapter_id=chapter_id,
            title=title,
            word_count=len(content),
            characters_appeared=chars,
            key_events=events,
            foreshadowing=foreshadowing,
        )
        vol.chapters[chapter_id] = mem
        self._dirty = True
        self.save()
        return mem

    def get_chapter(self, volume_id: str, chapter_id: str) -> Optional[ChapterMemory]:
        vol = self._state.volumes.get(volume_id)
        if vol is None:
            return None
        return vol.chapters.get(chapter_id)

    def list_chapters(self, volume_id: str) -> List[ChapterMemory]:
        vol = self._state.volumes.get(volume_id)
        if vol is None:
            return []
        return list(vol.chapters.values())

    # ── 自动提取（启发式占位，后续接入 AI 摘要） ──────────────────────

    _CHARACTER_PATTERN = re.compile(r'(?:说|道|问|答|喊|叫|骂|哭|笑|怒)(?:\s*[:：])?\s*[""「『]')
    _FORE_SHADOWING_KEYWORDS = [
        r'如果.*会怎样', r'突然', r'似乎', r'预感', r'不详', r'总觉得',
        r'冥冥之中', r'一个念头', r'暗流', r'暗潮',
    ]

    def _extract_characters(self, text: str) -> List[str]:
        """从对话/动作中提取疑似角色名（简化版本）。"""
        chars: List[str] = []
        # 查找 "XX说" 模式
        for match in re.finditer(r'([\u4e00-\u9fff]{2,4})[说|道|问|答|喊|叫]', text):
            name = match.group(1)
            if name not in chars and name not in ("我", "我们", "你", "你们", "他", "她"):
                chars.append(name)
        return chars

    def _extract_key_events(self, text: str) -> List[str]:
        # 简化实现：按段落取第一个句子作为事件
        events: List[str] = []
        for para in text.split("\n\n"):
            para = para.strip()
            if len(para) > 20:
                first_sent = para.split("。")[0][:80]
                events.append(first_sent)
        return events[:10]

    def _extract_foreshadowing(self, text: str) -> List[str]:
        results: List[str] = []
        for keyword in self._FORE_SHADOWING_KEYWORDS:
            for match in re.finditer(keyword, text):
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                results.append(text[start:end])
        return results[:5]

    # ── 角色备注 ─────────────────────────────────────────────────────

    def set_character_note(self, name: str, note: str) -> None:
        self._state.character_notes[name] = note
        self.save()

    def get_character_note(self, name: str) -> Optional[str]:
        return self._state.character_notes.get(name)

    # ── 全局设定 ─────────────────────────────────────────────────────

    def set_global_setting(self, key: str, value: str) -> None:
        self._state.global_settings[key] = value
        self.save()

    def get_global_setting(self, key: str) -> Optional[str]:
        return self._state.global_settings.get(key)

    # ── 检索 ─────────────────────────────────────────────────────────

    def search(self, query: str) -> List[Dict[str, Any]]:
        """模糊搜索全书记忆。"""
        results: List[Dict[str, Any]] = []
        q = query.lower()

        # 搜索章节摘要
        for vid, vol in self._state.volumes.items():
            for cid, ch in vol.chapters.items():
                score = 0
                if q in ch.summary.lower():
                    score += 10
                if q in ch.title.lower():
                    score += 5
                for event in ch.key_events:
                    if q in event.lower():
                        score += 3
                if score > 0:
                    results.append({
                        "volume": vid,
                        "chapter": cid,
                        "title": ch.title,
                        "summary": ch.summary[:200],
                        "score": score,
                    })

        # 搜索角色备注
        for name, note in self._state.character_notes.items():
            if q in name.lower() or q in note.lower():
                results.append({
                    "type": "character_note",
                    "name": name,
                    "note": note[:200],
                    "score": 8,
                })

        results.sort(key=lambda r: r.get("score", 0), reverse=True)
        return results[:20]
