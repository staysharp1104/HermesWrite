#!/usr/bin/env python3
"""
Chapter Index — 章节索引与摘要系统。

每章完成后自动生成摘要，存储到 SQLite FTS5 虚拟表。
支持按章节、角色、事件维度的多维索引。

复用 hermes_state.py 的 FTS5 架构。
"""

from __future__ import annotations
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_constants import get_project_home

logger = logging.getLogger(__name__)

# FTS5 表名
_FTS_TABLE = "novel_chapter_index"
_FTS_CONTENT_TABLE = "novel_chapter_content"


class ChapterIndex:
    """章节索引系统 — 每章的摘要和维度标签存储。"""

    def __init__(self, project_root: Optional[Path] = None):
        self._project_root = project_root or get_project_home()
        self._db_path = self._project_root / ".feelfish" / "records" / "chapter-index.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        # 主表
        self._conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {_FTS_CONTENT_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volume_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                title TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                characters TEXT DEFAULT '[]',
                key_events TEXT DEFAULT '[]',
                foreshadowing TEXT DEFAULT '[]',
                word_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(volume_id, chapter_id)
            );"""
        )
        # FTS5 虚拟表
        self._conn.execute(
            f"""CREATE VIRTUAL TABLE IF NOT EXISTS {_FTS_TABLE}
                USING fts5(
                    title, summary, characters, key_events,
                    content='{_FTS_CONTENT_TABLE}',
                    content_rowid='id',
                    tokenize='unicode61'
                );"""
        )
        self._conn.commit()

    # ── 索引操作 ────────────────────────────────────────────────────

    def index_chapter(
        self,
        volume_id: str,
        chapter_id: str,
        title: str = "",
        summary: str = "",
        characters: Optional[List[str]] = None,
        key_events: Optional[List[str]] = None,
        foreshadowing: Optional[List[str]] = None,
        word_count: int = 0,
    ) -> None:
        """将章节摘要和元数据加入索引。"""
        assert self._conn is not None

        chars_json = json.dumps(characters or [], ensure_ascii=False)
        events_json = json.dumps(key_events or [], ensure_ascii=False)
        fshad_json = json.dumps(foreshadowing or [], ensure_ascii=False)

        self._conn.execute(
            f"""INSERT OR REPLACE INTO {_FTS_CONTENT_TABLE}
                (volume_id, chapter_id, title, summary, characters, key_events, foreshadowing, word_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            (volume_id, chapter_id, title, summary, chars_json, events_json, fshad_json, word_count),
        )

        # 同步 FTS5 索引
        row_id = self._conn.execute(
            f"SELECT id FROM {_FTS_CONTENT_TABLE} WHERE volume_id=? AND chapter_id=?",
            (volume_id, chapter_id),
        ).fetchone()
        if row_id:
            self._conn.execute(
                f"INSERT INTO {_FTS_TABLE}(rowid, title, summary, characters, key_events) "
                f"VALUES (?, ?, ?, ?, ?);",
                (row_id[0], title, summary, chars_json, events_json),
            )

        self._conn.commit()
        logger.info("已索引章节: %s/%s (%d 字)", volume_id, chapter_id, word_count)

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """在章节索引中全文搜索。"""
        assert self._conn is not None

        # 避免 FTS5 语法错误
        safe_query = query.replace("'", "''")
        try:
            rows = self._conn.execute(
                f"""SELECT c.volume_id, c.chapter_id, c.title, c.summary, c.characters,
                           c.key_events, c.word_count, rank
                    FROM {_FTS_TABLE} f
                    JOIN {_FTS_CONTENT_TABLE} c ON f.rowid = c.id
                    WHERE {_FTS_TABLE} MATCH ?
                    ORDER BY rank
                    LIMIT ?;""",
                (safe_query, limit),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning("FTS5 搜索失败 '%s': %s", query, exc)
            return []

        results = []
        for row in rows:
            results.append({
                "volume_id": row[0],
                "chapter_id": row[1],
                "title": row[2],
                "summary": row[3][:300],
                "characters": json.loads(row[4] or "[]"),
                "key_events": json.loads(row[5] or "[]"),
                "word_count": row[6],
            })
        return results

    def get_chapter_index(self, volume_id: str, chapter_id: str) -> Optional[Dict[str, Any]]:
        """获取单章的索引信息。"""
        assert self._conn is not None
        row = self._conn.execute(
            f"SELECT * FROM {_FTS_CONTENT_TABLE} WHERE volume_id=? AND chapter_id=?",
            (volume_id, chapter_id),
        ).fetchone()
        if row is None:
            return None
        columns = [d[0] for d in self._conn.execute(f"PRAGMA table_info({_FTS_CONTENT_TABLE});")]
        return dict(zip(columns, row))

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
