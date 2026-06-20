# 🤖 Rikkahub AI 快速上手指南

> 你刚被部署到 Rikkahub 全权限工作区。请花 2 分钟读完本文，它会帮你省下大量试错时间。

---

## 📋 环境概览

| 项目 | 值 |
|------|-----|
| 工作目录 | `/skills` |
| GitHub 仓库 | `Lithuh-communi/for-ai` |
| GitHub 远程 | `github` (token 已嵌入) |
| 本地同步 | `/workspace/.remotes/skills.git` |
| 分支 | `master` |
| 运行环境 | proot 沙箱 (Linux, **不支持 symlink**) |

---

## 🛠 我能做什么？

| 能力 | 命令 | 说明 |
|------|------|------|
| 📱 控制手机 | `phone_controller.py` | 3 级策略 (UI树/OCR/模板匹配) |
| 👁️ 看屏幕 | `phone_controller.py --ui` | 查看 UI 元素 |
| 🔍 找文字点按 | `phone_controller.py "文字"` | 智能查找并点击 |
| 📜 翻页找 | 加 `--scroll` | 找不到自动下滑 |
| ⏳ 等待元素 | 加 `--wait 15` | 轮询等待 |
| 🎬 录制操作 | `phone_macro.py --record` | 录制操作序列 |
| ▶️ 回放操作 | `phone_macro.py --play` | 自动执行序列 |
| 🔋 手机状态 | `phone_monitor.py --info` | 电池/前台/存储/WiFi |
| 🔔 查看通知 | `phone_monitor.py --notifications` | 通知列表 |
| 👁️ 持续监控 | `phone_monitor.py --watch` | 实时状态栏 |
| 🖼️ 模板匹配 | `phone_controller.py --match-template` | 图标查找 |
| 📂 FTP 文件 | `phonefs.py` | Web 文件管理器 |
| 📁 文件共享 | `fileshare.py` | 局域网文件服务 |
| 🚀 推送代码 | 见下方 git 说明 | 同步到 GitHub |

---

## 🥇 第一步

```bash
# 1. Git 兼容性（不设会炸）
git config core.symlinks false

# 2. 连手机（向用户索要 ADB 地址）
adb connect 10.150.0.1:40745
# 或设置环境变量
export ADB_HOST=10.150.0.1:40745

# 3. 试试看
python3 phone_controller.py --ui
python3 phone_controller.py "设置"
```

---

## ⚠️ 重要注意事项

### Git（proot 兼容性）
```
❌ git push origin master          # 会炸！symlink 文件损坏
✅ git clone --no-local --bare . /workspace/.remotes/skills.git && cd /workspace/.remotes && git push github master
```

### GitHub 认证
- Token 已嵌入 `git remote github` 的 URL 中
- Token 存在 `.git/config` 里，**不会被提交**
- 如果推送到一半报 403，token 可能过期 → 问用户要新的

### ADB
- 每次 shell 会话连接会断开 → 用 `adb_utils.py`（自动重连）
- 已配 `ADB_HOST` 环境变量就不用每次指定
- 长时间不用会自动断，重新连即可

### 文件路径
| 用途 | 路径 |
|------|------|
| 工作区 | `/workspace/` |
| Skills | `/skills/` |
| 宏文件 | `/workspace/macros/` |
| 模板图片 | `/workspace/templates/` |
| 日志 | `/tmp/rikkahub.log` |
| 截图 | `/tmp/_*.png`（自动删除） |

---

## 🔍 遇到问题怎么办

| 症状 | 原因 | 解决 |
|------|------|------|
| `bad sha1 file` | symlink 损坏 | `rm -rf .git && git init && git config core.symlinks false && git add -A && git commit -m "rebuild"` |
| `unpack error` | push 用了 symlink | 改用 `clone --no-local` |
| `Operation not permitted` | proot 权限 | `rm -rf .git` 重建 |
| ADB 连不上 | 手机未开无线调试 | 让用户检查开发者选项 |
| OCR 找不到字 | 背景复杂/字体特殊 | 用 `--scroll` 翻页，或 `--match-template` |
| 点击没反应 | 元素不在当前屏幕 | 用 `--scroll` 模式 |
| GitHub 连不上 | 没开代理 | 让用户检查网络/SakuraCat |
| smart_find 报错 | ADB 断开 | 加 `--wait` 等待连接 |

---

## 📋 Skill 系统

每个 Skill 是一个目录 + `SKILL.md`：
```
/skills/<name>/SKILL.md
---
name: <skill-name>
description: <触发描述>
---
... skill 内容 ...
```

查看全部 Skill：`python3 /skills/skill-index.py`

---

## 💡 最佳实践

1. **操作手机前先 `adb connect` 确认连通**
2. **复杂操作优先用宏录制**，避免重复发命令
3. **截图自动清理**，不用手动删除
4. **推送前先看看有多少改动**：`git status`
5. **写日志**：`python3 script.py 2>&1 | tee /tmp/debug.log`

---

*祝运行顺利 ☀️  — 来自上一个在这里工作的 AI*
