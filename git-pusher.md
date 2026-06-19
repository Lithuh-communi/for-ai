---
name: git-pusher
description: Git 提交并推送到 GitHub。当用户说"推送"、"提交"、"push"、"推到GitHub"、"git push"、"commit"、"上传到仓库"时触发。自动处理 proot 沙箱兼容性问题（symlinks=false）。
---

# 🚀 Git 推送 Skill

一键提交并推送到 GitHub，自动处理认证和环境兼容。

## 📡 触发场景

| 用户说 | 动作 |
|--------|------|
| "推送" / "push" / "推到GitHub" | 直接 push |
| "提交" / "commit" | add → commit → push |
| "上传到仓库" | add → commit → push |

## ⚙️ 环境兼容（重要）

本环境运行在 proot 沙箱中，Git 必须配置：

```bash
git config core.symlinks false
```

> 不设此配置会导致对象文件变成损坏的符号链接，push 失败。

## 🔐 GitHub 认证

### 首次推送
向用户索要 **Personal Access Token**（需 `repo` 权限），然后嵌入 remote URL：

```bash
git remote set-url github https://<TOKEN>@github.com/<USER>/<REPO>.git
```

### 已有 token
直接检查 `git remote -v` 中 github 的 URL 是否包含 token，有则直接用。

### Token 安全
- Token 存储在 `.git/config` 的 remote URL 中
- `.git/config` 不会被提交到仓库
- 其他 AI 拉代码看不到 token

## 📋 操作流程

### 标准流程（add + commit + push）

```bash
cd /skills

# 1. 有 token 吗？
git remote -v | grep github

# 2. 没 token → 问用户要
# 有 token → 继续

# 3. 提交
git add -A
git commit -m "<变更描述>"

# 4. 推送
git push github master
```

### 仅推送（已有 commit）

```bash
cd /skills && git push github master
```

### 推送到本地 origin

```bash
cd /skills && git push origin master
```

## 🛠 故障处理

| 故障 | 解决方案 |
|------|----------|
| `bad object` / `unpack error` | `rm -rf .git && git init && git config core.symlinks false && git add -A && git commit -m "rebuild"` |
| `could not read Username` | 用 token 嵌入 URL 方式 |
| `remote rejected (bad pack)` | bare 仓库也需 `git config core.symlinks false` |
| `failed to create link` | 用 `git clone --no-local --bare` 代替 `git push` |

## 📂 仓库信息

| 项目 | 值 |
|------|-----|
| 本地路径 | `/skills` |
| GitHub 远程 | `https://github.com/Lithuh-communi/for-ai.git` |
| 本地 origin | `/workspace/.remotes/skills.git` |
| 分支 | `master` |

## 💡 示例

用户: "推送"
→ 检查 git remote 有 token → `git push github master` → ✅

用户: "把这个提交了"
→ `git add -A` → `git commit -m "xxx"` → `git push github master` → ✅
