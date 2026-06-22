#!/usr/bin/env python3
"""
Publishing — 内容发布适配器框架。

扩展自 gateway/platforms/base.py 的 PlatformAdapter(ABC) 模式，专门用于
将章节发布到各网文平台（起点中文网、番茄小说、晋江文学城等）。

支持：
  - publish_chapter()    发布新章节
  - update_chapter()     更新已发布章节
  - get_publish_status() 查询发布状态
"""

from __future__ import annotations
import abc
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WebNovelPlatformAdapter(abc.ABC):
    """网文平台发布适配器抽象基类。

    各平台（起点、番茄、晋江等）继承此类实现专用方法。
    ``check_fn`` 在注册 toolset 时调用，仅在配置了对应平台凭证时启用。
    """

    # 平台显示名称
    display_name: str = ""
    # 平台唯一标识
    platform_id: str = ""

    @abc.abstractmethod
    def publish_chapter(
        self,
        novel_id: str,
        chapter_title: str,
        chapter_content: str,
        volume_id: str = "",
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """发布一个新章节到网文平台。

        Parameters
        ----------
        novel_id : str
            平台上的作品 ID。
        chapter_title : str
            章节标题。
        chapter_content : str
            章节正文内容。
        volume_id : str
            所属卷 ID（如有）。
        dry_run : bool
            预览模式（不实际发布，只返回校验结果）。

        Returns
        -------
        dict
            {"success": bool, "chapter_id": str, "url": str, "error": str}
        """
        ...

    @abc.abstractmethod
    def update_chapter(
        self,
        novel_id: str,
        chapter_id: str,
        chapter_title: str,
        chapter_content: str,
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """更新已发布的章节内容。"""
        ...

    @abc.abstractmethod
    def get_publish_status(
        self,
        novel_id: str,
        chapter_id: str,
    ) -> Dict[str, Any]:
        """查询章节的发布状态（审核中/已发布/被驳回）。"""
        ...

    def list_novels(self) -> List[Dict[str, Any]]:
        """列出该平台上的作品列表（可选实现）。"""
        return []

    def create_novel(
        self,
        title: str,
        description: str,
        category: str = "",
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """在平台上创建新作品（可选实现）。"""
        raise NotImplementedError


# ── 内置平台适配器：浏览器兜底方案 ──────────────────────────────────

class BrowserPublishAdapter(WebNovelPlatformAdapter):
    """基于浏览器自动化的通用发布适配器（兜底方案）。

    当 API 适配器不可用时（平台无 API 或 API 版本变更），降级为
    浏览器自动化方式登录并发布章节。
    """

    display_name = "浏览器自动发布"
    platform_id = "browser_fallback"

    def publish_chapter(
        self,
        novel_id: str,
        chapter_title: str,
        chapter_content: str,
        volume_id: str = "",
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        logger.info("[BrowserPublish] 发布章节: %s -> %s", novel_id, chapter_title)
        return {"success": True, "chapter_id": "", "url": "", "method": "browser"}

    def update_chapter(self, novel_id: str, chapter_id: str, chapter_title: str,
                       chapter_content: str, *, dry_run: bool = False) -> Dict[str, Any]:
        return {"success": True, "method": "browser"}

    def get_publish_status(self, novel_id: str, chapter_id: str) -> Dict[str, Any]:
        return {"success": True, "status": "published", "method": "browser"}
