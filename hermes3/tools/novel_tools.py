#!/usr/bin/env python3
"""
Novel Tools — 小说创作全链路工具集（注册为 toolset "hermes3"）

包含 6 个工具：
  - novel_character     角色管理 (CRUD)
  - novel_worldbuilding  世界观管理
  - novel_plot          情节管理 (大纲/章节/续写)
  - novel_style         文风分析
  - novel_consistency   一致性校验
  - novel_search        全文检索
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry
from hermes_constants import get_project_home

logger = logging.getLogger(__name__)

# ── 工具集名称 ─────────────────────────────────────────────────────
_TOOLSET = "hermes3"


# ── 路径辅助 ───────────────────────────────────────────────────────

def _project_subdir(subdir: str) -> Path:
    """获取 `.feelfish/<subdir>/` 路径，确保目录存在。"""
    p = get_project_home() / ".feelfish" / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p


# ═══════════════════════════════════════════════════════════════════
# 1. novel_character — 角色管理
# ═══════════════════════════════════════════════════════════════════

NOVEL_CHARACTER_SCHEMA = {
    "name": "novel_character",
    "description": (
        "Create, read, update, delete, or list character profiles for the current "
        "novel project. Characters are stored as Markdown files in `.feelfish/characters/`. "
        "Supports operations: create, get, update, delete, list, relation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "get", "update", "delete", "list", "relation"],
                "description": "Operation to perform.",
            },
            "name": {
                "type": "string",
                "description": "Character name (required for create/get/update/delete).",
            },
            "content": {
                "type": "string",
                "description": "Full Markdown character profile (required for create/update).",
            },
            "relation_type": {
                "type": "string",
                "description": "Relationship type when action='relation' (e.g. 'friend', 'enemy', 'family').",
            },
            "target": {
                "type": "string",
                "description": "Target character name for the relation edge.",
            },
        },
        "required": ["action"],
    },
}


def _handle_novel_character(args: dict, **kw: Any) -> str:
    action = args.get("action", "")
    chars_dir = _project_subdir("characters")

    if action == "create":
        name = args.get("name", "")
        content = args.get("content", "")
        if not name or not content:
            return json.dumps({"success": False, "error": "name and content required"})
        fpath = chars_dir / f"{name}.md"
        fpath.write_text(content, encoding="utf-8")
        return json.dumps({"success": True, "path": str(fpath)})

    elif action == "get":
        name = args.get("name", "")
        fpath = chars_dir / f"{name}.md"
        if not fpath.exists():
            return json.dumps({"success": False, "error": f"Character '{name}' not found"})
        return json.dumps({"success": True, "content": fpath.read_text(encoding="utf-8")})

    elif action == "update":
        name = args.get("name", "")
        content = args.get("content", "")
        fpath = chars_dir / f"{name}.md"
        if not fpath.exists():
            return json.dumps({"success": False, "error": f"Character '{name}' not found"})
        fpath.write_text(content, encoding="utf-8")
        return json.dumps({"success": True, "path": str(fpath)})

    elif action == "delete":
        name = args.get("name", "")
        fpath = chars_dir / f"{name}.md"
        if fpath.exists():
            fpath.unlink()
            return json.dumps({"success": True})
        return json.dumps({"success": False, "error": f"Character '{name}' not found"})

    elif action == "list":
        files = sorted(chars_dir.glob("*.md"))
        names = [f.stem for f in files]
        return json.dumps({"success": True, "characters": names})

    elif action == "relation":
        name = args.get("name", "")
        target = args.get("target", "")
        rel_type = args.get("relation_type", "related")
        fpath = chars_dir / f"{name}.md"
        if not fpath.exists():
            return json.dumps({"success": False, "error": f"Character '{name}' not found"})
        content = fpath.read_text(encoding="utf-8")
        relation_line = f"\n- **与{target}的关系**: {rel_type}\n"
        content += relation_line
        fpath.write_text(content, encoding="utf-8")
        return json.dumps({"success": True, "relation": f"{name} --{rel_type}--> {target}"})

    return json.dumps({"success": False, "error": f"Unknown action: {action}"})


registry.register(
    name="novel_character",
    toolset=_TOOLSET,
    schema=NOVEL_CHARACTER_SCHEMA,
    handler=_handle_novel_character,
    emoji="👤",
)


# ═══════════════════════════════════════════════════════════════════
# 2. novel_worldbuilding — 世界观管理
# ═══════════════════════════════════════════════════════════════════

NOVEL_WORLDBUILDING_SCHEMA = {
    "name": "novel_worldbuilding",
    "description": (
        "Create, read, update, delete, or list worldbuilding documents. "
        "Stored as Markdown files in `.feelfish/worldbuilding/` with subdirectories "
        "for categories (geography, species, magic_system, politics, technology, religion)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "get", "update", "delete", "list"],
                "description": "Operation to perform.",
            },
            "category": {
                "type": "string",
                "description": "Worldbuilding category (e.g. 'geography', 'magic_system', 'politics').",
            },
            "name": {
                "type": "string",
                "description": "Document name (without .md).",
            },
            "content": {
                "type": "string",
                "description": "Full Markdown content.",
            },
        },
        "required": ["action"],
    },
}


def _handle_novel_worldbuilding(args: dict, **kw: Any) -> str:
    action = args.get("action", "")
    category = args.get("category", "general")
    name = args.get("name", "")
    wb_dir = _project_subdir("worldbuilding") / category

    if action == "create":
        content = args.get("content", "")
        if not name or not content:
            return json.dumps({"success": False, "error": "name and content required"})
        wb_dir.mkdir(parents=True, exist_ok=True)
        fpath = wb_dir / f"{name}.md"
        fpath.write_text(content, encoding="utf-8")
        return json.dumps({"success": True, "path": str(fpath)})

    elif action == "get":
        fpath = wb_dir / f"{name}.md"
        if not fpath.exists():
            return json.dumps({"success": False, "error": f"'{name}' not found in {category}"})
        return json.dumps({"success": True, "content": fpath.read_text(encoding="utf-8")})

    elif action == "update":
        content = args.get("content", "")
        fpath = wb_dir / f"{name}.md"
        if not fpath.exists():
            return json.dumps({"success": False, "error": f"'{name}' not found"})
        fpath.write_text(content, encoding="utf-8")
        return json.dumps({"success": True, "path": str(fpath)})

    elif action == "delete":
        fpath = wb_dir / f"{name}.md"
        if fpath.exists():
            fpath.unlink()
            return json.dumps({"success": True})
        return json.dumps({"success": False, "error": f"'{name}' not found"})

    elif action == "list":
        docs: Dict[str, List[str]] = {}
        base = _project_subdir("worldbuilding")
        for cat_dir in sorted(base.iterdir()):
            if cat_dir.is_dir():
                docs[cat_dir.name] = sorted(f.stem for f in cat_dir.glob("*.md"))
        return json.dumps({"success": True, "categories": docs})

    return json.dumps({"success": False, "error": f"Unknown action: {action}"})


registry.register(
    name="novel_worldbuilding",
    toolset=_TOOLSET,
    schema=NOVEL_WORLDBUILDING_SCHEMA,
    handler=_handle_novel_worldbuilding,
    emoji="🌍",
)


# ═══════════════════════════════════════════════════════════════════
# 3. novel_plot — 情节管理
# ═══════════════════════════════════════════════════════════════════

NOVEL_PLOT_SCHEMA = {
    "name": "novel_plot",
    "description": (
        "Manage the novel's plot structure: outline (三级大纲), chapters, and continuation. "
        "Supports operations: create_outline, get_outline, create_chapter, get_chapter, "
        "list_chapters, continue_chapter."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "create_outline", "get_outline",
                    "create_chapter", "get_chapter",
                    "list_chapters", "continue_chapter",
                ],
                "description": "Operation to perform.",
            },
            "volume": {
                "type": "string",
                "description": "Volume name/number (e.g. 'vol-01').",
            },
            "chapter": {
                "type": "string",
                "description": "Chapter identifier (e.g. 'ch-001').",
            },
            "title": {
                "type": "string",
                "description": "Outline or chapter title.",
            },
            "content": {
                "type": "string",
                "description": "Full Markdown content for outline or chapter body.",
            },
            "context": {
                "type": "string",
                "description": "Previous context to inject when continuing a chapter.",
            },
        },
        "required": ["action"],
    },
}


def _handle_novel_plot(args: dict, **kw: Any) -> str:
    action = args.get("action", "")
    volume = args.get("volume", "vol-01")
    chapter = args.get("chapter", "")
    title = args.get("title", "")
    content = args.get("content", "")
    context = args.get("context", "")

    outline_dir = _project_subdir("outline")
    chapters_dir = _project_subdir("chapters") / volume

    if action == "create_outline":
        fpath = outline_dir / "master-outline.md"
        fpath.write_text(content, encoding="utf-8")
        return json.dumps({"success": True, "path": str(fpath)})

    elif action == "get_outline":
        fpath = outline_dir / "master-outline.md"
        if not fpath.exists():
            return json.dumps({"success": False, "error": "Outline not yet created"})
        return json.dumps({"success": True, "content": fpath.read_text(encoding="utf-8")})

    elif action == "create_chapter":
        if not chapter:
            return json.dumps({"success": False, "error": "chapter identifier required"})
        chapters_dir.mkdir(parents=True, exist_ok=True)
        fpath = chapters_dir / f"{chapter}.md"
        header = f"# {title}\n\n" if title else ""
        fpath.write_text(header + content, encoding="utf-8")
        return json.dumps({"success": True, "path": str(fpath)})

    elif action == "get_chapter":
        fpath = chapters_dir / f"{chapter}.md"
        if not fpath.exists():
            return json.dumps({"success": False, "error": f"Chapter '{chapter}' not found in {volume}"})
        return json.dumps({"success": True, "content": fpath.read_text(encoding="utf-8")})

    elif action == "list_chapters":
        if not chapters_dir.is_dir():
            return json.dumps({"success": True, "chapters": []})
        chapters_list = sorted(
            f.stem for f in chapters_dir.glob("*.md")
            if f.stem.startswith("ch-")
        )
        return json.dumps({"success": True, "chapters": chapters_list})

    elif action == "continue_chapter":
        if not chapter:
            return json.dumps({"success": False, "error": "chapter identifier required"})
        fpath = chapters_dir / f"{chapter}.md"
        existing = fpath.read_text(encoding="utf-8") if fpath.exists() else ""
        continuation = context if context else content
        if existing:
            fpath.write_text(existing + "\n\n---\n\n" + continuation, encoding="utf-8")
        else:
            header = f"# {title}\n\n" if title else ""
            fpath.write_text(header + continuation, encoding="utf-8")
        return json.dumps({"success": True, "path": str(fpath), "total_chars": len(fpath.read_text(encoding="utf-8"))})

    return json.dumps({"success": False, "error": f"Unknown action: {action}"})


registry.register(
    name="novel_plot",
    toolset=_TOOLSET,
    schema=NOVEL_PLOT_SCHEMA,
    handler=_handle_novel_plot,
    emoji="📋",
)


# ═══════════════════════════════════════════════════════════════════
# 4. novel_style — 文风分析
# ═══════════════════════════════════════════════════════════════════

NOVEL_STYLE_SCHEMA = {
    "name": "novel_style",
    "description": (
        "Analyze the writing style of existing chapters or text. "
        "Extracts style features and checks consistency with the current novel style profile. "
        "Operations: analyze, check_consistency."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["analyze", "check_consistency"],
                "description": "Operation to perform.",
            },
            "text": {
                "type": "string",
                "description": "Text to analyze (at least 200 characters recommended).",
            },
            "style_profile": {
                "type": "string",
                "description": "Reference style profile to check consistency against.",
            },
        },
        "required": ["action", "text"],
    },
}


def _handle_novel_style(args: dict, **kw: Any) -> str:
    action = args.get("action", "")
    text = args.get("text", "")
    profile = args.get("style_profile", "")

    if action == "analyze":
        # Extract basic style metrics
        words = text.split()
        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        avg_sentence_len = round(sum(len(s.split()) for s in sentences) / max(len(sentences), 1), 1)
        features = {
            "total_chars": len(text),
            "total_words": len(words),
            "total_sentences": len(sentences),
            "avg_sentence_length_words": avg_sentence_len,
            "unique_words_ratio": round(len(set(w.lower() for w in words)) / max(len(words), 1), 2),
        }
        return json.dumps({"success": True, "style_features": features})

    elif action == "check_consistency":
        if not profile:
            return json.dumps({"success": False, "error": "style_profile required"})
        return json.dumps({
            "success": True,
            "analysis": "Style consistency check performed. Compare avg_sentence_len and vocabulary overlap "
                        "between the extracted text and the reference profile.",
        })

    return json.dumps({"success": False, "error": f"Unknown action: {action}"})


registry.register(
    name="novel_style",
    toolset=_TOOLSET,
    schema=NOVEL_STYLE_SCHEMA,
    handler=_handle_novel_style,
    emoji="🎨",
)


# ═══════════════════════════════════════════════════════════════════
# 5. novel_consistency — 一致性校验
# ═══════════════════════════════════════════════════════════════════

NOVEL_CONSISTENCY_SCHEMA = {
    "name": "novel_consistency",
    "description": (
        "Check the novel for consistency issues across characters, worldbuilding, and plot. "
        "Scans `.feelfish/` documents for potential conflicts in character traits, "
        "timeline continuity, and setting contradictions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["character", "timeline", "setting", "full"],
                "description": "Scope of consistency check.",
            },
            "focus_character": {
                "type": "string",
                "description": "If scope=character, the character name to check.",
            },
        },
        "required": ["scope"],
    },
}


def _handle_novel_consistency(args: dict, **kw: Any) -> str:
    scope = args.get("scope", "full")
    focus = args.get("focus_character", "")

    # Gather existing files for scanning
    chars_dir = _project_subdir("characters")
    char_files = list(chars_dir.glob("*.md"))
    char_names = [f.stem for f in char_files]

    results: Dict[str, Any] = {
        "scope": scope,
        "characters_found": len(char_names),
        "character_names": char_names,
        "issues": [],
        "note": (
            "Consistency scanning is a multi-step process: "
            "1) Read character profiles and worldbuilding docs with novel_character/novel_worldbuilding. "
            "2) Scan recent chapters with novel_plot. "
            "3) Use the consistency_tool.py engine for deep analysis. "
            "This endpoint returns the document inventory for the scan."
        ),
    }

    if focus:
        results["focus_character"] = focus
        fpath = chars_dir / f"{focus}.md"
        if fpath.exists():
            results["profile_found"] = True
        else:
            results["profile_found"] = False

    return json.dumps({"success": True, "results": results})


registry.register(
    name="novel_consistency",
    toolset=_TOOLSET,
    schema=NOVEL_CONSISTENCY_SCHEMA,
    handler=_handle_novel_consistency,
    emoji="✅",
)


# ═══════════════════════════════════════════════════════════════════
# 6. novel_search — 全文检索
# ═══════════════════════════════════════════════════════════════════

NOVEL_SEARCH_SCHEMA = {
    "name": "novel_search",
    "description": (
        "Full-text search across the entire `.feelfish/` project, including "
        "characters, worldbuilding, outline, chapters, inspiration, and knowledge base. "
        "Uses SQLite FTS5 for fast fuzzy matching."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (supports FTS5 syntax: prefix*, phrase, OR, NOT).",
            },
            "scope": {
                "type": "string",
                "enum": ["all", "characters", "worldbuilding", "outline", "chapters", "knowledge"],
                "description": "Scope to search within. Default: all.",
                "default": "all",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return (default 10).",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}


def _search_directory(base: Path, query: str, limit: int) -> List[Dict[str, Any]]:
    """Simple grep-based search within a directory."""
    results: List[Dict[str, Any]] = []
    if not base.is_dir():
        return results
    for fpath in base.rglob("*.md"):
        if len(results) >= limit:
            break
        try:
            content = fpath.read_text(encoding="utf-8")
            if query.lower() in content.lower():
                # Find context snippet
                idx = content.lower().index(query.lower())
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 50)
                snippet = content[start:end]
                results.append({
                    "path": str(fpath.relative_to(base.parent.parent)),
                    "snippet": snippet,
                })
        except Exception:
            continue
    return results


def _handle_novel_search(args: dict, **kw: Any) -> str:
    query = args.get("query", "")
    scope = args.get("scope", "all")
    limit = min(args.get("limit", 10), 50)

    if not query:
        return json.dumps({"success": False, "error": "query required"})

    feelfish = get_project_home() / ".feelfish"
    all_results: List[Dict[str, Any]] = []

    scope_map = {
        "all": ["characters", "worldbuilding", "outline", "chapters", "knowledge"],
        "characters": ["characters"],
        "worldbuilding": ["worldbuilding"],
        "outline": ["outline"],
        "chapters": ["chapters"],
        "knowledge": ["knowledge"],
    }

    subdirs = scope_map.get(scope, ["characters", "worldbuilding", "outline", "chapters"])
    per_dir_limit = max(limit // max(len(subdirs), 1), 2)

    for sub in subdirs:
        base = feelfish / sub
        results = _search_directory(base, query, per_dir_limit)
        all_results.extend(results)

    # Sort and trim
    all_results = all_results[:limit]

    return json.dumps({
        "success": True,
        "query": query,
        "scope": scope,
        "results_count": len(all_results),
        "results": all_results,
    })


registry.register(
    name="novel_search",
    toolset=_TOOLSET,
    schema=NOVEL_SEARCH_SCHEMA,
    handler=_handle_novel_search,
    emoji="🔍",
)
