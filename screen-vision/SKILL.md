---
name: screen-vision
description: 通过 ADB + OpenCV + OCR 实现手机屏幕视觉识别和精准点击。当用户说"看屏幕"、"找按钮"、"点这个"、"截屏"、"帮我点"、"OCR"时触发。需要 ADB over WiFi 连接。
---

# 👁️ 屏幕视觉控制 Skill v2

截屏 → OCR 识别 → 精准操作，一站式手机屏幕自动化。

## 📡 前置条件

ADB over WiFi 已连接：
```bash
adb connect <手机IP>:<端口>
```
或设置环境变量：`export ADB_HOST=10.150.0.1:40745`

## 🔧 工具

| 工具 | 说明 |
|------|------|
| `adb` | Android 调试桥 |
| `python3-opencv` | 图像处理 |
| `tesserocr` (chi_sim+eng) | 文字识别 |
| `/workspace/smart_tap.py` | **v2 统一脚本** |

## 📋 命令速查

```bash
# 查看屏幕（自动 OCR 标注）
python3 /workspace/smart_tap.py

# 找字并点击（模糊匹配）
python3 /workspace/smart_tap.py "发送"

# 精确匹配
python3 /workspace/smart_tap.py "发送" --exact

# 点第N个匹配
python3 /workspace/smart_tap.py "确定" --tap 2

# 长按
python3 /workspace/smart_tap.py "消息" --long

# 双击
python3 /workspace/smart_tap.py "消息" --double

# 最低置信度过滤
python3 /workspace/smart_tap.py "设置" --conf 60

# 滑动
python3 /workspace/smart_tap.py --swipe 500,2000,500,500

# 输入文字（自动识别中英文）
python3 /workspace/smart_tap.py --type "你好世界"

# 仅列出文字（不点击）
python3 /workspace/smart_tap.py --list
```

## 🚀 v2 新特性

| 特性 | 说明 |
|------|------|
| 🔍 **模糊匹配** | 默认子串匹配 + 拼音首字母，不区分大小写 |
| 🎨 **图像预处理** | CLAHE 对比度增强 + 锐化，OCR 准确率提升 |
| ⚡ **API 复用** | OCR 引擎单例复用，多次调用不重复初始化 |
| 🎯 **多匹配选择** | `--tap N` 点第 N 个匹配，显示全部候选 |
| 🌈 **置信度着色** | 绿色≥70% / 黄色≥40% / 灰色<40% |
| 📏 **面积信息** | 显示匹配区域的位置和像素面积 |
| 👆 **完整手势** | tap / long_press / double_tap / swipe |
| ⌨️ **智能输入** | 中文自动走剪贴板，英文直接 input text |
| 🧹 **自动清理** | 截图读完秒删，0 残留 |

## 🐍 底层 API 速查

```python
import subprocess, os, sys
sys.path.insert(0, '/workspace')
from smart_tap import shot, ocr, find_text, tap, swipe, type_text

# 截屏 + OCR
img = shot()
words = ocr(img)

# 找文字
matches = find_text(words, "发送", min_conf=50, fuzzy=True)

# 操作
if matches:
    text, cx, cy, *_ = matches[0]
    tap(cx, cy)
    # long_press(cx, cy, duration=800)
    # swipe(100, 500, 100, 1000, duration=300)

# 按键
from smart_tap import key
key(4)   # 返回
key(3)   # Home
```

## ♻️ 截图自动清理

所有临时截图在读取后立即 `os.remove()`，不占用空间。

## ⚠️ 注意事项

- 每次截图前确认 ADB 已连接
- OCR 对游戏自定义字体识别率较低（建议提高对比度或使用游戏内置字体）
- 中文输入用 `--type` 自动走剪贴板
- 标注截图：`/tmp/_annotated.png`（每次覆盖）
- 可通过 `ADB_HOST` 环境变量配置 IP
