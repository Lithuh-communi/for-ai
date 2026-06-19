---
name: skill-installer
description: 快速创建并安装 Rikkahub Skill。当用户说"写个skill"、"做个skill"、"创建技能"、"安装skill"、"弄个技能"时触发。自动生成符合 Rikkahub 规范的 SKILL.md 并写入 /skills/<name>/ 目录，立即可用。
---

# Skill Installer — 快速创建 Rikkahub Skill

一键创建符合 Rikkahub 规范的 Skill，自动安装到扩展管理中，无需手动配置。

## 📋 工作流程

### 第一步：收集信息

与用户对话，确认以下内容：

```yaml
skill_name:       # 技能名称（英文短横线式，如 file-organizer）
display_name:     # 显示名称（中文，如 "文件整理"）
description:      # 触发描述（什么场景触发、做什么）
instructions:     # 核心指令（具体实现步骤）
```

需要问用户的问题：

1. **Skill 名字是什么？**（英文，如 `pdf-merge`）
2. **什么时候触发？**（用户说什么话时激活？）
3. **具体做什么？**（描述功能）
4. **实现步骤？**（可选，AI 可以自己设计）

### 第二步：生成 SKILL.md

在 `/workspace/` 下创建临时文件，格式如下：

```markdown
---
name: <skill_name>
description: <description>
---

# <display_name>

<详细指令，让 AI 知道怎么执行这个 skill>
```

### 第三步：写入目标目录

```bash
# 创建 skill 目录
mkdir -p /skills/<skill_name>/

# 写入 SKILL.md
cp /workspace/<skill_name>.md /skills/<skill_name>/SKILL.md

# 验证
cat /skills/<skill_name>/SKILL.md | head -5
```

### 第四步：确认生效

告诉用户 Skill 已安装成功，并说明：
- 在什么场景下会触发
- 可以在 Rikkahub 的扩展管理中看到它

## ✍️ SKILL.md 模板

```markdown
---
name: <英文名>
description: <中文描述，包含触发词和功能说明>
---

# <显示名称>

<核心指令内容>

## 使用示例

<可选：给 AI 的示例对话>
```

## ⚙️ 目录结构规范

```
/skills/
  ├── <skill-name>/      # 新建的 skill 目录
  │   └── SKILL.md       # 主文件（必须）
  ├── skill-installer/   # 本 skill
  ├── phone-ftp-access/  
  └── ...
```

> 💡 只需创建目录 + SKILL.md，Rikkahub 会自动识别。

## ✅ 验证方法

创建好后，用以下命令确认：

```bash
ls -la /skills/<skill_name>/
cat /skills/<skill_name>/SKILL.md | head -3  # 检查 frontmatter
```

## 📌 注意事项

- `name` 字段用英文小写，单词间短横线连接
- `description` 字段写清楚触发场景，方便 Rikkahub 精准匹配
- SKILL.md 首部必须有 `---` 包裹的 YAML frontmatter
- 如果用户没说清楚，主动询问细节
