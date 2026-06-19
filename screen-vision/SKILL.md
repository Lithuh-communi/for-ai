---
name: screen-vision
description: 通过 ADB + OpenCV + OCR 实现手机屏幕视觉识别和精准点击。当用户说"看屏幕"、"找按钮"、"点这个"、"截屏"、"帮我点"、"OCR"时触发。需要 ADB over WiFi 连接。
---

# 👁️ 屏幕视觉控制 Skill

截屏 → OCR 识别文字 → 精准点击，三步完成手机屏幕自动化操作。

## 📡 前置条件

必须已建立 ADB over WiFi 连接：
```bash
adb connect <手机IP>:<端口>
```
如果未连接，先询问用户无线调试信息。

## 🔧 工具

- `adb` — Android 调试桥
- `python3-opencv` — 图像处理
- `tesserocr` (chi_sim+eng) — 文字识别
- `/workspace/smart_tap.py` — 智能点击脚本

## 📋 操作流程

### 1. 查看屏幕上有什么

```bash
cd /workspace && python3 smart_tap.py
```

输出示例：
```
📱 屏幕: 1440x3200
📝 识别到 56 个文字：
  y= 165: 记忆 | 空白 | 求助
  y=2815: 输入消息与AI聊天
📸 标注截图: /tmp/_annotated.png
```

### 2. 找文字并点击

```bash
python3 smart_tap.py "发送"
# → 🔍 找到 '发送' → (1350, 2980)
# → ✅ 点击 (1350, 2980)
```

### 3. 手动点击坐标

```bash
adb shell "input tap x y"
```

### 4. 输入文字

```bash
# 英文
adb shell "input text 'hello world'"

# 中文（需用剪贴板方式）
adb shell "service call clipboard 4 i32 1 s16 '中文' s16 'label'"
# 然后长按输入框 → 粘贴
```

### 5. 滑动屏幕

```bash
adb shell "input swipe x1 y1 x2 y2 duration_ms"
```

### 6. 截屏保存

```bash
adb exec-out screencap -p > /tmp/screen.png
```

## 🐍 Python 版完整示例

```python
import subprocess, cv2

ADB = "adb connect 10.150.0.1:40745 && adb"

def shot():
    subprocess.run(f"{ADB} exec-out screencap -p > /tmp/_s.png", shell=True)
    return cv2.imread('/tmp/_s.png')

def find_text(img, target):
    """在图片中用 OCR 找文字，返回坐标"""
    from PIL import Image
    import tesserocr
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    api = tesserocr.PyTessBaseAPI(lang='chi_sim+eng', path='/usr/share/tesseract-ocr/5/tessdata')
    api.SetImage(pil)
    api.Recognize()
    ri = api.GetIterator()
    if ri:
        while True:
            text = ri.GetUTF8Text(tesserocr.RIL.WORD)
            box = ri.BoundingBox(tesserocr.RIL.WORD)
            if text and target in text and box:
                cx, cy = (box[0]+box[2])//2, (box[1]+box[3])//2
                api.End()
                return cx, cy
            if not ri.Next(tesserocr.RIL.WORD):
                break
    api.End()
    return None

def tap(x, y):
    subprocess.run(f"{ADB} shell input tap {x} {y}", shell=True)

# 使用
img = shot()
pos = find_text(img, "发送")
if pos:
    tap(*pos)
```

## ♻️ 自动清理

截图文件在读取后自动删除，不留残留：

```python
def shot():
    adb("exec-out screencap -p > /tmp/_s.png")
    img = cv2.imread("/tmp/_s.png")
    os.remove("/tmp/_s.png")  # 读完秒删
    return img
```

`smart_tap.py` 和 `screen_control.py` 都已内置此机制。

## ⚠️ 注意事项

- 每次截图前先确保 ADB 已连接
- OCR 对游戏内自定义字体识别率较低
- 中文输入推荐用剪贴板 + 粘贴方式
- 标注截图保存在 `/tmp/_annotated.png` 可供查看
