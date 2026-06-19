---
name: phone-master
description: 安卓手机终极控制。当用户说"控制手机"、"操作手机"、"点这个"、"发消息"、"看屏幕"、"找按钮"、"输入文字"、"截图"时触发。今日血泪教训总结：uiautomator2 > OCR，别跟MIUI剪贴板死磕。
---

# 📱 手机终极控制 Skill

> **核心教训：能用 uiautomator2 就别用 OCR。MIUI 剪贴板是地狱，uiautomator2 的 set_text() 直接绕过。**

## 🔧 工具栈

| 工具 | 用途 | 优先级 |
|------|------|--------|
| **uiautomator2** | 找元素、点按钮、输入文字 | ⭐⭐⭐ 首选 |
| **ADB** | 截图、shell、回退方案 | ⭐⭐ 备用 |
| **OCR (tesserocr)** | 游戏中找文字 | ⭐ 兜底 |
| **scrcpy** | 实时投屏 | 可选 |

## ⚡ 快速开始

```python
import uiautomator2 as u2
import time

d = u2.connect('10.150.0.1:40745')

# 查看当前App
print(d.app_current())

# 找元素（瞬间，不截图不OCR）
send_btn = d(text="发送")

# 点击
if send_btn.exists:
    send_btn.click()

# 输入中文（绕过MIUI剪贴板限制！）
edit = d(className="android.widget.EditText")
edit.set_text("你好世界 👋")

# 按resource-id找
el = d(resourceId="com.tencent.mobileqq:id/input")
el.click()

# 滑动手势
d.swipe(500, 2000, 500, 500, duration=0.3)

# 等待元素出现
d(text="确认", timeout=10).click()
```

## 📋 常见操作

### 发QQ消息

```python
d = u2.connect('10.150.0.1:40745')

# 找输入框（QQ用EditText）
edit = d(className="android.widget.EditText", packageName="com.tencent.mobileqq")
edit.click()
edit.set_text("消息内容")

# 点发送
d(text="发送", packageName="com.tencent.mobileqq").click()
```

### 切换App

```python
# 方式1: adb
import subprocess
subprocess.run("adb shell monkey -p com.tencent.mobileqq 1", shell=True)
time.sleep(1)

# 方式2: uiautomator2
d.app_start("com.tencent.mobileqq")
```

### 截图 + 分析

```python
# uiautomator2截图
img = d.screenshot()
img.save('/tmp/screen.png')

# OCR分析（仅用于游戏等无UI树的场景）
from vision import ocr_text, shot
words, _ = ocr_text(shot())
```

### 安装uiautomator2

```bash
python3 -m pip install uiautomator2 --break-system-packages
```

## ⚠️ 血泪教训

### MIUI 剪贴板
- ❌ `service call clipboard` → Parcel data not fully consumed
- ❌ `cmd clipboard set` → No shell command implementation  
- ❌ `settings put secure KEY_CLIPBOARD_LIST` → 不生效
- ❌ `am broadcast clipper.set` → 返回成功但实际不工作
- ❌ `input text "中文"` → NullPointerException
- ✅ **uiautomator2 `set_text()` → 直接绕过，完美支持中文+emoji**

### 实时截屏
- ❌ 每次截图→OCR→分析→操作：2秒延迟
- ❌ 后台截屏服务：进程会被杀
- ✅ **uiautomator2 找元素：0ms，不用截图**

### 视觉分析
- OCR 适合游戏（没有UI树）
- 标准App用 uiautomator2，100%准确

### Git 在 proot 环境
```bash
git config core.symlinks false  # 必须！
git clone --no-local --bare . /path/to/bare.git  # 别用 push
```

## 🚀 最佳实践

1. **先试 uiautomator2**，找不到元素再回退 OCR
2. **中文输入用 set_text()**，不走剪贴板
3. **找按钮用 text= 或 resourceId=**，不用坐标
4. **截图用 d.screenshot()**，比 adb screencap 快

## 📂 相关文件

| 文件 | 用途 |
|------|------|
| `/workspace/phone_controller.py` | 三级策略控制器（L1 UI树/L2 OCR/L3 scrcpy） |
| `/workspace/vision.py` | 视觉分析模块 |
| `/workspace/smart_tap.py` | OCR点击（v2，图像预处理+模糊匹配） |
| `/workspace/live_screen.py` | 后台截屏服务 |

> 💡 实际开发中发现 phone_controller.py 的 UI树解析被 uiautomator2 完爆，建议直接用它替代。
