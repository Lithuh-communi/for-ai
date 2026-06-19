---
name: proot-survivor
description: Proot 沙箱环境生存指南。当 AI 遇到 Git 异常（bad object、symlink、pack failed、unpack error）、文件权限问题（Operation not permitted）、或需要了解本环境特殊限制时触发。也是给新来 AI 的交接文档。
---

# 🏕️ Proot 沙箱生存指南

在 Rikkahub 全权限工作区活下来的经验，写给后来的 AI。

## ⚠️ 核心问题：Git 不兼容

本环境是 proot 沙箱，**不支持 symlink**。Git 默认用 symlink 创建临时对象，导致连锁故障。

### 症状速查

| 你看到的 | 真实原因 | 怎么办 |
|----------|----------|--------|
| `bad sha1 file: .l2s.tmp_obj_xxx` | git 对象变成了损坏 symlink | 清理 temp 文件，设 `core.symlinks=false` |
| `unpack should have generated xxx, but I can't find it` | push 的 pack/unpack 在 bare 仓库创建 symlink 失败 | 别 push，用 clone |
| `Operation not permitted` on git objects | proot 无权访问某些文件 | 重建 `.git` |
| `failed to create link` | clone --local 尝试硬链接 | 加 `--no-local` |
| `fatal: unable to access github.com` | 没开 VPN | 让人类开 VPN |

### 标准修复流程

```bash
# 1. 清掉所有 temp 文件
find /skills/.git -name ".l2s.tmp_obj_*" -delete 2>/dev/null

# 2. 彻底重建（如果坏得厉害）
cd /skills
rm -rf .git
git init
git config core.symlinks false
git config user.name "Rikkahub Workspace AI"
git config user.email "ai@rikkahub.workspace"
git add -A
git commit -m "rebuild"
```

### 正确的同步方式

```bash
# ❌ 不要用 git push
git push origin master  # 会炸

# ✅ 用 clone --no-local
rm -rf /workspace/.remotes/skills.git
cd /skills
git clone --no-local --bare . /workspace/.remotes/skills.git
```

## 🔐 GitHub 认证

```bash
# Token 嵌入 URL（.git/config 不会被提交，安全）
git remote set-url github https://<TOKEN>@github.com/Lithuh-communi/for-ai.git
```

- Token 需要 `repo` 权限
- 别把 token 写进任何 .md 文件（会被提交）
- GitHub 连不上 → 让人类开 VPN

## 📂 仓库信息

| 项 | 值 |
|----|-----|
| 工作目录 | `/skills` |
| GitHub | `https://github.com/Lithuh-communi/for-ai.git` |
| 本地 origin | `/workspace/.remotes/skills.git` |
| 分支 | `master` |
| Skills 目录 | `/skills/<name>/SKILL.md` |

## 📋 已知 Skill 列表

| Skill | 目录 | 状态 |
|-------|------|------|
| phone-adb-access | `phone-ftp-access/` | ⚠️ 名称与目录不一致 |
| skill-installer | `skill-installer/` | ✅ |
| skill-creator | `skill-creator/` | ⚠️ SKILL.md 被截断 |
| note-tidy | `note-tidy/` | ✅ |
| update-summarizer | `update-summarizer/` | ✅ |
| screen-vision | `screen-vision/` | ✅ |
| auto-pilot | `auto-pilot/` | ✅ |
| git-pusher | `git-pusher/` | ✅ |
| proot-survivor | `proot-survivor/` | ✅ 本文档 |

## 🧠 给新 AI 的速查

1. 进去先 `git config core.symlinks false`
2. 推送 = `clone --no-local --bare`，别 push
3. 连不上 GitHub = 让人类开 VPN
4. `phone-adb-access` 在 `phone-ftp-access/` 目录
5. `skill-creator/SKILL.md` 没写完，需要补
