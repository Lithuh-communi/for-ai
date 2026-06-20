#!/usr/bin/env python3
"""
RikkaHub Phone MCP Server — 手机全能控制服务
将 phone_controller.py / phone_macro.py / phone_monitor.py / phonefs.py
暴露为 MCP Tool，供 RikkaHub 客户端通过局域网调用。
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)

# ── 路径常量 ──
SKILLS_DIR = Path("/skills")
WORKSPACE_DIR = Path("/workspace")
ADB_UTILS = SKILLS_DIR / "adb_utils.py"
PHONE_CTRL = SKILLS_DIR / "phone_controller.py"
PHONE_MACRO = SKILLS_DIR / "phone_macro.py"
PHONE_MONITOR = SKILLS_DIR / "phone_monitor.py"
PHONEFS = SKILLS_DIR / "phonefs.py"
SMART_TAP = SKILLS_DIR / "smart_tap.py"

# ── 日志 ──
LOG_FILE = Path("/tmp/mcp-server.log")


def log(msg: str):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")


# ── 辅助函数 ──

def run_py(script: str, args: list[str] | None = None, timeout: int = 60) -> str:
    """运行 /skills 下的 Python 脚本，返回 stdout"""
    cmd = [sys.executable, script]
    if args:
        cmd.extend(args)
    log(f"RUN: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            log(f"ERR (rc={r.returncode}): {r.stderr[:200]}")
            return f"错误: {r.stderr[:500]}"
        return r.stdout.strip() or "(空输出)"
    except subprocess.TimeoutExpired:
        return f"错误: 执行超时 ({timeout}s)"
    except FileNotFoundError as e:
        return f"错误: 脚本不存在 - {e}"
    except Exception as e:
        return f"错误: {e}"


def check_adb() -> str | None:
    """检查 ADB 是否已连接，未连则尝试环境变量"""
    host = os.environ.get("ADB_HOST")
    if host:
        r = subprocess.run(
            ["adb", "connect", host],
            capture_output=True, text=True, timeout=10,
        )
        if "connected" in r.stdout or "already" in r.stdout:
            return None
        return f"ADB 连接失败: {r.stderr or r.stdout}"
    return "ADB_HOST 未设置，请先设置环境变量"


# ── 实例化服务器 ──
app = Server("rikkahub-phone-mcp")


# ── 工具定义 ──

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="phone_get_ui",
            description="获取手机当前屏幕的 UI 元素树 (XML)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="phone_tap_text",
            description="查找屏幕上的文字并点击",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要点击的文字内容",
                    },
                    "scroll": {
                        "type": "boolean",
                        "description": "找不到时是否自动向下滚动",
                        "default": False,
                    },
                    "wait": {
                        "type": "integer",
                        "description": "等待元素出现的秒数",
                        "default": 0,
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="phone_tap_xy",
            description="点击屏幕指定坐标",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X 坐标"},
                    "y": {"type": "integer", "description": "Y 坐标"},
                },
                "required": ["x", "y"],
            },
        ),
        Tool(
            name="phone_swipe",
            description="屏幕滑动",
            inputSchema={
                "type": "object",
                "properties": {
                    "x1": {"type": "integer", "description": "起点 X"},
                    "y1": {"type": "integer", "description": "起点 Y"},
                    "x2": {"type": "integer", "description": "终点 X"},
                    "y2": {"type": "integer", "description": "终点 Y"},
                    "duration": {
                        "type": "integer",
                        "description": "滑动时长(毫秒)",
                        "default": 300,
                    },
                },
                "required": ["x1", "y1", "x2", "y2"],
            },
        ),
        Tool(
            name="phone_type",
            description="在输入框中输入文字",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要输入的文字"},
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="phone_screenshot",
            description="截取手机屏幕并返回 base64 图片",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="phone_back",
            description="按下返回键",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="phone_home",
            description="按下 Home 键回到桌面",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="phone_monitor",
            description="获取手机状态信息 (电池/前台应用/存储/WiFi)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="phone_notifications",
            description="查看手机通知列表",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="phone_macro_record",
            description="开始录制手机操作宏",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "宏名称",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="phone_macro_play",
            description="回放已录制的操作宏",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "宏名称",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="phone_find_file",
            description="在手机上搜索文件",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "文件名(支持模糊搜索)",
                    },
                },
                "required": ["filename"],
            },
        ),
        Tool(
            name="workspace_read",
            description="读取工作区文件内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径 (相对 /workspace)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="workspace_write",
            description="写入工作区文件",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径 (相对 /workspace)",
                    },
                    "content": {
                        "type": "string",
                        "description": "文件内容",
                    },
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="workspace_shell",
            description="在工作区执行 Shell 命令",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的命令",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时秒数",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="list_skills",
            description="列出所有已安装的 Skill",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


# ── 工具调用实现 ──

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent | EmbeddedResource]:
    log(f"CALL: {name}({json.dumps(arguments, ensure_ascii=False)})")

    if name == "phone_get_ui":
        r = subprocess.run(
            ["adb", "shell", "uiautomator", "dump", "/dev/tmp/uidump.xml",
             "&&", "cat", "/dev/tmp/uidump.xml"],
            capture_output=True, text=True, timeout=30,
        )
        return [TextContent(type="text", text=r.stdout or r.stderr)]

    elif name == "phone_tap_text":
        args = []
        text = arguments.get("text", "")
        if arguments.get("scroll"):
            args.append("--scroll")
        if arguments.get("wait"):
            args.extend(["--wait", str(arguments["wait"])])
        args.append(text)
        out = run_py(str(PHONE_CTRL), args)
        return [TextContent(type="text", text=out)]

    elif name == "phone_tap_xy":
        out = run_py(str(SMART_TAP), [
            "--tap",
            str(arguments["x"]), str(arguments["y"]),
        ])
        return [TextContent(type="text", text=out)]

    elif name == "phone_swipe":
        r = subprocess.run(
            ["adb", "shell", "input", "swipe",
             str(arguments["x1"]), str(arguments["y1"]),
             str(arguments["x2"]), str(arguments["y2"]),
             str(arguments.get("duration", 300))],
            capture_output=True, text=True, timeout=10,
        )
        return [TextContent(type="text", text=r.stdout or "滑动完成")]

    elif name == "phone_type":
        text = arguments["text"]
        escaped = text.replace(" ", "%s").replace("'", "")
        r = subprocess.run(
            ["adb", "shell", "input", "text", escaped],
            capture_output=True, text=True, timeout=10,
        )
        return [TextContent(type="text", text=r.stdout or f"已输入: {text}")]

    elif name == "phone_screenshot":
        tmp = "/dev/tmp/screen.png"
        subprocess.run(["adb", "shell", "screencap", "-p", tmp.replace("/dev/tmp", "/dev/tmp")],
                       capture_output=True, timeout=15)
        subprocess.run(["adb", "pull", tmp, tmp], capture_output=True, timeout=15)
        import base64
        try:
            with open(tmp, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return [ImageContent(type="image", data=b64, mimeType="image/png")]
        except FileNotFoundError:
            return [TextContent(type="text", text="截图失败: 文件未生成")]

    elif name == "phone_back":
        subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_BACK"],
                       capture_output=True, timeout=10)
        return [TextContent(type="text", text="已返回")]

    elif name == "phone_home":
        subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_HOME"],
                       capture_output=True, timeout=10)
        return [TextContent(type="text", text="已回到桌面")]

    elif name == "phone_monitor":
        out = run_py(str(PHONE_MONITOR), ["--info"])
        return [TextContent(type="text", text=out)]

    elif name == "phone_notifications":
        out = run_py(str(PHONE_MONITOR), ["--notifications"])
        return [TextContent(type="text", text=out)]

    elif name == "phone_macro_record":
        out = run_py(str(PHONE_MACRO), ["--record", arguments["name"]])
        return [TextContent(type="text", text=out)]

    elif name == "phone_macro_play":
        out = run_py(str(PHONE_MACRO), ["--play", arguments["name"]])
        return [TextContent(type="text", text=out)]

    elif name == "phone_find_file":
        out = run_py(str(PHONEFS), ["--find", arguments["filename"]])
        return [TextContent(type="text", text=out)]

    elif name == "workspace_read":
        p = WORKSPACE_DIR / arguments["path"]
        if not p.exists():
            return [TextContent(type="text", text=f"文件不存在: {arguments['path']}")]
        content = p.read_text(encoding="utf-8", errors="replace")
        return [TextContent(type="text", text=content)]

    elif name == "workspace_write":
        p = WORKSPACE_DIR / arguments["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(arguments["content"], encoding="utf-8")
        return [TextContent(type="text", text=f"已写入: {arguments['path']} ({len(arguments['content'])} bytes)")]

    elif name == "workspace_shell":
        try:
            r = subprocess.run(
                arguments["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=arguments.get("timeout", 30),
            )
            out = r.stdout or ""
            if r.stderr:
                out += f"\n--- stderr ---\n{r.stderr[:1000]}"
            if r.returncode != 0:
                out = f"退出码 {r.returncode}\n{out}"
            return [TextContent(type="text", text=out.strip() or "(空输出)")]
        except subprocess.TimeoutExpired:
            return [TextContent(type="text", text=f"命令超时 ({arguments.get('timeout', 30)}s)")]

    elif name == "list_skills":
        out = run_py(str(SKILLS_DIR / "skill-index.py"))
        return [TextContent(type="text", text=out)]

    else:
        raise ValueError(f"未知工具: {name}")


# ── 启动 ──

async def main():
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="rikkahub-phone-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
