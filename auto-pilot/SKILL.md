---
name: auto-pilot
description: AI 全自动助手 - 手机控制、GitHub 同步、MCP 服务器管理、系统维护
---

# 🤖 Auto-Pilot — AI 全自动助手

> 本 Skill 定义了 AI 在 Rikkahub 工作区中的全部能力和操作规范。
> 每次加载时自动读取，确保 AI 知道所有可用工具和工作流程。

---

## 📋 环境概览

| 项目 | 值 |
|------|-----|
| 工作目录 | `/skills` |
| GitHub 仓库 | `Lithuh-communi/for-ai` |
| GitHub 远程 | `github` (token 已嵌入) |
| 本地同步 | `/workspace/.remotes/skills.git` |
| Git 分支 | `master` |
| 运行环境 | proot 沙箱 (Linux) |

---

## 🔧 核心能力

### 📱 手机控制 (ADB)

| 命令 | 说明 |
|------|------|
| `python3 /skills/phone_controller.py --ui` | 查看屏幕 UI 元素 |
| `python3 /skills/phone_controller.py "文字"` | 智能查找文字并点击 |
| `python3 /skills/phone_controller.py "文字" --scroll` | 翻页查找并点击 |
| `python3 /skills/phone_controller.py "文字" --wait 15` | 等待元素出现后点击 |
| `python3 /skills/phone_controller.py --match-template 模板名` | 图标模板匹配点击 |
| `python3 /skills/phone_controller.py --save-template 模板名` | 保存当前区域为模板 |
| `python3 /skills/phone_macro.py --record` | 录制操作宏 |
| `python3 /skills/phone_macro.py --play 宏名` | 回放操作宏 |
| `python3 /skills/phone_monitor.py --info` | 查看手机状态 |
| `python3 /skills/phone_monitor.py --notifications` | 查看通知 |
| `python3 /skills/phone_monitor.py --watch` | 实时监控模式 |

### 📂 FTP 文件管理

| 命令 | 说明 |
|------|------|
| `python3 /skills/phonefs.py` | 启动 Web 文件管理器 |
| `python3 /skills/phonefs.py --find 文件名` | 搜索文件 |
| `python3 /skills/fileshare.py` | 局域网文件共享服务 |

### 🚀 GitHub 操作

```bash
# ✅ 正确推送方式（proot 兼容）
cd /skills
git clone --no-local --bare . /workspace/.remotes/skills.git
cd /workspace/.remotes
git push github master

# 推送到远程
git push github master
```

### 🧹 Skill 管理

```bash
# 查看所有已安装 skill
python3 /skills/skill-index.py

# 创建新 skill
mkdir -p /skills/<skill-name>
# 然后创建 SKILL.md (必须包含 frontmatter)
```

---

## 📬 自动更新检查

**启动后优先执行**：
1. `cd /skills && git fetch github`
2. 对比本地和远程的最新 commit
3. 如果有更新 → `git pull --rebase github main` (处理冲突)
4. 读取新的 `更新总结_*.md` 告知用户

---

## 🌐 MCP 服务器配置

用户可以创建 MCP 服务器让手机 Rikkahub 调用电脑的能力：

| MCP 服务器类型 | 启动命令 |
|----------------|---------|
| 文件系统 | `npx -y @modelcontextprotocol/server-filesystem <路径>` |
| GitHub | `npx -y @modelcontextprotocol/server-github` |
| 联网搜索 | `npx -y @tavily/mcp-server` |

手机 Rikkahub 通过局域网 `http://电脑IP:端口/mcp` 连接。

---

## ⚠️ 重要注意事项

### Git (proot 兼容)
- ❌ 不要直接 `git push origin master` (symlink 会损坏)
- ✅ 用 `clone --no-local --bare` 方式推送
- 如果 `.git` 损坏 → `rm -rf .git && git init && git config core.symlinks false && git add -A && git commit -m "rebuild"`

### ADB
- 每次会话需先 `adb connect` 或使用 `adb_utils.py`(自动重连)
- 环境变量 `ADB_HOST` 已配置就不用每次都连

### 文件路径
| 用途 | 路径 |
|------|------|
| 工作区 | `/workspace/` |
| Skills | `/skills/` |
| 宏文件 | `/workspace/macros/` |
| 模板图片 | `/workspace/templates/` |
| 截图 | `/tmp/_*.png` (自动清理) |

---

## 💡 最佳实践

1. **启动先检查 GitHub 更新** — 看有没有新能力
2. **操作手机前先连 ADB** — `adb connect` 确认通畅
3. **复杂操作用宏录制** — 减少重复发命令
4. **推送前先 `git status`** — 确认改了什么
5. **写日志** — `python3 script.py 2>&1 \| tee /tmp/debug.log`
6. **有新能力就更新这个 SKILL.md** — 让后续 AI 都知道

---

*最后更新: 2026-06-21*
*由 AI 自动创建并维护*
