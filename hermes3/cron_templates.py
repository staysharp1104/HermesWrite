#!/usr/bin/env python3
"""
Cron Job Templates — hermes3 创作调度任务模板。

新增可复用的定时任务模板，配合 cron/jobs.py 使用。

模板列表：
  - daily_plan        每日创作计划（定时启动规划 Agent 生成当日大纲）
  - auto_publish      定时连载发布（cron 触发 -> 调用发布适配器）
  - consistency_scan  一致性定期扫描（每日凌晨启动审核 Agent）
  - weekly_report     每周创作数据报告
  - auto_backup       自动备份项目目录
  - market_monitor    市场热点监控（定时启动浏览器 Agent 采集热门榜单）
"""

from __future__ import annotations
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── 模板定义 ───────────────────────────────────────────────────────

CRON_JOB_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "daily_plan": {
        "name": "每日创作计划",
        "description": "每天指定时间自动启动规划 Agent，生成当日章节大纲并推送到手机",
        "cron_expression": "0 9 * * *",  # 每天早上 9:00
        "prompt_template": (
            "今天是 {date}。请作为规划师 Agent 分析当前创作进度，"
            "生成今日章节大纲和创作目标。当前项目: {project_name}"
        ),
        "enabled_toolsets": ["hermes3", "memory"],
        "default_max_iterations": 15,
    },
    "auto_publish": {
        "name": "定时连载发布",
        "description": "按设定时间自动将最新章节发布到指定平台",
        "cron_expression": "0 20 * * *",  # 每天晚上 8:00
        "prompt_template": (
            "请从最新章节中选取已完成的章节，调用发布适配器将其发布到 {platform}。"
            "当前项目: {project_name}"
        ),
        "enabled_toolsets": ["hermes3"],
        "default_max_iterations": 10,
    },
    "consistency_scan": {
        "name": "一致性定期扫描",
        "description": "每日凌晨自动检测新增章节中的人设/设定/时间线冲突",
        "cron_expression": "0 3 * * *",  # 每天凌晨 3:00
        "prompt_template": (
            "作为审核 Agent，请扫描最近24小时内新增的章节内容，"
            "检测人设冲突、设定矛盾、时间线问题。当前项目: {project_name}"
        ),
        "enabled_toolsets": ["hermes3", "memory"],
        "default_max_iterations": 30,
    },
    "weekly_report": {
        "name": "每周创作数据报告",
        "description": "每周统计字数、章节数、创作时长，生成周报推送",
        "cron_expression": "0 10 * * 1",  # 每周一上午 10:00
        "prompt_template": (
            "统计当前项目的创作数据：字数增长、章节完成数、创作时长趋势。"
            "生成一份简洁的周报。当前项目: {project_name}"
        ),
        "enabled_toolsets": ["hermes3"],
        "default_max_iterations": 10,
    },
    "auto_backup": {
        "name": "自动备份项目",
        "description": "每日自动备份 .feelfish/ 项目目录到指定位置",
        "cron_expression": "0 4 * * *",  # 每天凌晨 4:00
        "prompt_template": (
            "请将当前项目目录下的 .feelfish/ 备份到备份目录。"
            "当前项目: {project_name}"
        ),
        "enabled_toolsets": ["terminal"],
        "default_max_iterations": 5,
    },
    "market_monitor": {
        "name": "市场热点监控",
        "description": "定时采集各平台热门榜单，生成市场洞察报告",
        "cron_expression": "0 8 * * 1,3,5",  # 每周一、三、五早 8:00
        "prompt_template": (
            "使用浏览器工具采集当前平台热门榜单数据，"
            "分析趋势和读者偏好，生成市场洞察报告。当前项目: {project_name}"
        ),
        "enabled_toolsets": ["browser", "web"],
        "default_max_iterations": 20,
    },
}


def get_template(name: str) -> Dict[str, Any] | None:
    """按名称获取模板。"""
    return CRON_JOB_TEMPLATES.get(name)


def list_templates() -> Dict[str, str]:
    """列出所有可用模板（名称 -> 描述）。"""
    return {k: v["description"] for k, v in CRON_JOB_TEMPLATES.items()}
