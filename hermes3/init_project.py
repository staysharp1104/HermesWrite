#!/usr/bin/env python3
"""
.feelfish 项目依赖初始化脚本。

在每个小说项目的根目录执行一次 `python -m hermes3.init_project`
即可创建完整的 .feelfish/ 目录结构。
"""

from __future__ import annotations
import argparse
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# 默认项目骨架
_DEFAULT_STRUCTURE = {
    "project.yaml": "name: 未命名小说\nauthor: \ntype: 玄幻\nword_goal: 1000000\nlanguage: zh-CN\ncreated_at: ",
    "solutions/": None,        # 目录
    "agents/": None,           # 目录
    "rules/": None,            # 目录
    "skills/": None,           # 目录
    "characters/": None,       # 目录
    "worldbuilding/": None,    # 目录
    "outline/chapters/": None, # 目录
    "inspiration/": None,      # 目录
    "assets/images/": None,    # 目录
    "assets/audio/": None,     # 目录
    "knowledge/reference-docs/": None,  # 目录
    "chapters/": None,         # 目录
    "records/history/": None,  # 目录
    "records/writing-log.jsonl": "",  # 空文件
}

# .feelfish 目录名
_FEELFISH = ".feelfish"


def init_project(
    root: str | Path,
    *,
    name: str = "未命名小说",
    author: str = "",
    novel_type: str = "玄幻",
    word_goal: int = 1000000,
    force: bool = False,
) -> Path:
    """在指定路径创建 .feelfish/ 项目骨架。

    Parameters
    ----------
    root : str | Path
        项目根目录。
    name, author, novel_type, word_goal :
        项目元数据。
    force : bool
        如果 .feelfish/ 已存在，是否覆写。

    Returns
    -------
    Path
        .feelfish/ 目录路径。
    """
    root = Path(root).resolve()
    feelfish_dir = root / _FEELFISH

    if feelfish_dir.exists() and not force:
        logger.info(".feelfish/ 已存在 (%s), 跳过初始化。使用 --force 覆写。", feelfish_dir)
        return feelfish_dir

    # 创建目录和文件
    feelfish_dir.mkdir(parents=True, exist_ok=True)

    for name_or_path, content in _DEFAULT_STRUCTURE.items():
        target = feelfish_dir / name_or_path
        if content is None:
            # 目录
            target.mkdir(parents=True, exist_ok=True)
        else:
            # 文件
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or force:
                target.write_text(content, encoding="utf-8")

    # 写入 project.yaml
    project_yaml = feelfish_dir / "project.yaml"
    from datetime import datetime
    project_yaml.write_text(
        f"name: {name}\n"
        f"author: {author}\n"
        f"type: {novel_type}\n"
        f"word_goal: {word_goal}\n"
        f"language: zh-CN\n"
        f"created_at: {datetime.now().isoformat()}\n",
        encoding="utf-8",
    )

    logger.info(
        ".feelfish/ 项目已初始化: %s (小说: %s, 类型: %s)",
        feelfish_dir, name, novel_type,
    )
    return feelfish_dir


def cli() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="初始化 hermes3 小说项目")
    parser.add_argument("root", nargs="?", default=".", help="项目根目录（默认为当前目录）")
    parser.add_argument("--name", default="未命名小说", help="小说名称")
    parser.add_argument("--author", default="", help="作者")
    parser.add_argument("--type", default="玄幻", help="小说类型")
    parser.add_argument("--word-goal", type=int, default=1000000, help="目标字数")
    parser.add_argument("--force", action="store_true", help="覆写已存在的 .feelfish/")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    init_project(
        args.root,
        name=args.name,
        author=args.author,
        novel_type=args.type,
        word_goal=args.word_goal,
        force=args.force,
    )


if __name__ == "__main__":
    cli()
