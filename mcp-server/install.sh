#!/bin/bash
# ==========================================
# RikkaHub Phone MCP Server — 一键安装脚本
# ==========================================
set -e

echo "📦 安装 RikkaHub Phone MCP Server..."

# 1. 安装依赖
echo "📥 安装 Python 依赖..."
pip install mcp httpx -q

# 2. 检查 ADB
if ! command -v adb &>/dev/null; then
    echo "⚠️  未检测到 adb，请先安装 Android Debug Bridge"
else
    echo "✅ adb 已就绪"
fi

# 3. 创建配置目录
mkdir -p /workspace/.idx

# 4. 生成 RikkaHub MCP 配置
cat > /workspace/.idx/mcp.json << 'JSONEOF'
{
  "mcpServers": {
    "phone-mcp": {
      "command": "python3",
      "args": ["/skills/mcp-server/server.py"],
      "env": {
        "ADB_HOST": "${ADB_HOST}"
      }
    }
  }
}
JSONEOF

echo "✅ 安装完成！"
echo ""
echo "📋 在 RikkaHub 中配置："
echo "   设置 → MCP 服务器 → 添加"
echo "   命令: python3"
echo "   参数: /skills/mcp-server/server.py"
echo "   环境变量: ADB_HOST=你的手机IP:端口"
echo ""
echo "🚀 或者直接运行测试："
echo "   python3 /skills/mcp-server/server.py"
