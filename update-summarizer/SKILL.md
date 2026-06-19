---
name: update-summarizer
description: 当有重要功能更新或新增能力时，自动生成更新总结文档并创建对应的 Rikkahub Skill。触发词包括"更新了"、"新功能"、"新增"、"升级"、"重要更新"、"写个总结"、"做个skill"。
---

# 📢 更新总结 + Skill 自动生成器

当有新功能、新能力、或重要变更时，自动完成两件事：
1. **📝 写总结** — 记录变更内容、能力说明、使用方法
2. **📦 做 Skill** — 将该能力封装为立即可用的 Rikkahub Skill

---

## 🔔 触发场景

用户说类似这些话时触发：

| 用户说 | 触发 |
|--------|------|
| "我更新了xxx" | ✅ |
| "新增了xxx功能" | ✅ |
| "xxx升级了" | ✅ |
| "有个重要的更新" | ✅ |
| "把这个能力写个skill" | ✅ |
| 在对话中新增了某种能力（如装了新工具、配了新服务） | ✅ 主动询问是否需要封装 |

---

## 📝 第一步：写总结

在 `/workspace/` 下创建 `更新总结_<日期>.md`，格式如下：

```markdown
# 📢 更新总结 — <日期>

## 🆕 新增内容
- <具体变更>

## 🔧 能力说明
- <能做什么>

## 🚀 使用方法
- <怎么用>

## 📎 相关文件
- <文件路径>

## 💡 注意事项
- <注意点>
```

## 📦 第二步：做 Skill

按照以下流程将新能力封装为 Skill：

### 1. 确定 Skill 信息

| 字段 | 说明 |
|------|------|
| **name** | 英文短横线式，如 `screen-vision` |
| **description** | 触发描述 + 功能说明 |
| **instructions** | 具体的操作步骤、代码示例 |

### 2. 生成 SKILL.md

```markdown
---
name: <skill-name>
description: <描述，含触发词>
---

# <显示名称>

## 概述
<能力说明>

## 前提条件
<需要什么环境/工具>

## 操作步骤
<具体步骤>

## 示例
<使用示例>

## 注意事项
<注意点>
```

### 3. 安装到 Rikkahub

```bash
mkdir -p /skills/<skill-name>/
cp <临时文件> /skills/<skill-name>/SKILL.md
```

### 4. 验证

```bash
cat /skills/<skill-name>/SKILL.md | head -5
ls -la /skills/<skill-name>/
```

---

## 📂 输出文件

```
/workspace/更新总结_<日期>.md     ← 总结文档
/skills/<skill-name>/SKILL.md     ← 新 Skill
```

## 💡 示例

当用户说"我装好了 OpenCV 和 OCR，现在能看屏幕了"时，自动：

```
📝 生成: /workspace/更新总结_2026-06-20.md
    - 新增: OpenCV 4.6.0 计算机视觉
    - 新增: TesserOCR 中文+英文文字识别
    - 新增: smart_tap.py 智能点击脚本

📦 生成: /skills/screen-vision/SKILL.md
    - 屏幕截图 + OCR识别 + 精准点击
    - 立即可以在 Rikkahub 扩展管理中看到
```

## ⚠️ 注意事项

- 总结文档放在 `/workspace/` 方便查看
- Skill 放在 `/skills/<name>/SKILL.md` 才被 Rikkahub 识别
- description 字段要写清楚触发场景
- 包含实际可用的代码示例
