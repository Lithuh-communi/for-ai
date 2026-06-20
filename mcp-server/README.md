# 📱 RikkaHub Phone MCP Server

将手机控制能力暴露为 MCP 工具，RikkaHub 客户端可直接调用。

## ✨ 工具列表

| 工具 | 说明 |
|------|------|
| `phone_get_ui` | 获取屏幕 UI 元素树 |
| `phone_tap_text` | 查找文字并点击 |
| `phone_tap_xy` | 坐标点击 |
| `phone_swipe` | 滑动屏幕 |
| `phone_type` | 输入文字 |
| `phone_screenshot` | 截图 (返回图片) |
| `phone_back` | 返回键 |
| `phone_home` | Home 键 |
| `phone_monitor` | 手机状态监控 |
| `phone_notifications` | 通知列表 |
| `phone_macro_record` | 录制操作宏 |
| `phone_macro_play` | 回放操作宏 |
| `phone_find_file` | 搜索文件 |
| `workspace_read` | 读取工作区文件 |
| `workspace_write` | 写入工作区文件 |
| `workspace_shell` | 执行 Shell 命令 |
| `list_skills` | 列出所有 Skill |

## 🚀 快速启动

```bash
# 1. 安装依赖
pip install mcp httpx

# 2. 设置 ADB 连接
export ADB_HOST=192.168.x.x:xxxxx

# 3. 启动 MCP 服务器 (STDIO 模式)
python3 /skills/mcp-server/server.py
```

## 🔌 RikkaHub 配置

### STDIO 模式 (推荐)
设置 → MCP 服务器 → 添加
- 名称: `手机控制`
- 命令: `python3`
- 参数: `/skills/mcp-server/server.py`
- 环境变量: `ADB_HOST=你的手机IP:端口`

### Streamable HTTP 模式
```bash
# 启动 HTTP 服务
python3 -m mcp.server.stdio --transport sse --port 58000 \
  python3 /skills/mcp-server/server.py
```
- 名称: `手机控制`
- URL: `http://127.0.0.1:58000/mcp`

## 📁 文件结构
```
/skills/mcp-server/
├── server.py         # MCP 服务器主程序
├── requirements.txt  # Python 依赖
├── install.sh        # 一键安装脚本
└── README.md         # 本文件
```
