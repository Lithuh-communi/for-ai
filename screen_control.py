#!/usr/bin/env python3
"""屏幕视觉控制 - 截图 → OCR找字 → 精准点击"""
import cv2
import numpy as np
import subprocess
import os
import re
import sys

ADB_HOST = "10.150.0.1:40745"

def adb(cmd):
    """执行 adb 命令"""
    full = f"adb connect {ADB_HOST} && adb {cmd}"
    try:
        r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=15)
        return r.stdout
    except:
        return ""

def screenshot():
    """截图并返回 OpenCV 图像（读完自动删）"""
    subprocess.run(
        f"adb connect {ADB_HOST} && adb exec-out screencap -p > /tmp/_screen.png",
        shell=True, timeout=15
    )
    img = cv2.imread('/tmp/_screen.png')
    os.remove('/tmp/_screen.png')
    return img

def find_text(img, target_text):
    """在图片中找指定文字，返回中心坐标"""
    import tesserocr
    from PIL import Image
    
    api = tesserocr.PyTessBaseAPI(lang='chi_sim+eng', path='/usr/share/tesseract-ocr/5/tessdata')
    try:
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        api.SetImage(pil)
        api.Recognize()
        
        ri = api.GetIterator()
        found = []
        level = tesserocr.RIL.WORD
        
        if ri:
            while True:
                text = ri.GetUTF8Text(level)
                confidence = ri.Confidence(level)
                if text and target_text in text:
                    box = ri.BoundingBox(level)
                    if box:
                        x1, y1, x2, y2 = box
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        found.append((text.strip(), cx, cy, x1, y1, x2, y2, confidence))
                if not ri.Next(level):
                    break
        return found
    finally:
        api.End()

def find_all_text(img):
    """识别屏幕上所有文字及其位置"""
    from PIL import Image
    import tesserocr
    
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    api = tesserocr.PyTessBaseAPI(lang='chi_sim+eng', path='/usr/share/tesseract-ocr/5/tessdata')
    try:
        api.SetImage(pil)
        api.Recognize()
        ri = api.GetIterator()
        level = tesserocr.RIL.WORD
        results = []
        if ri:
            while True:
                text = ri.GetUTF8Text(level)
                conf = ri.Confidence(level)
                if text and text.strip():
                    box = ri.BoundingBox(level)
                    if box:
                        x1, y1, x2, y2 = box
                        results.append((text.strip(), x1, y1, x2, y2, conf))
                if not ri.Next(level):
                    break
        return results
    finally:
        api.End()

def tap(x, y):
    """点击屏幕坐标"""
    print(f"  👆 点击 ({x}, {y})")
    adb(f"shell input tap {x} {y}")

def swipe(x1, y1, x2, y2, duration=300):
    """滑动"""
    adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")

def type_text(text):
    """输入文字"""
    adb(f"shell input text '{text}'")

def key_back():
    adb("shell input keyevent 4")

def key_home():
    adb("shell input keyevent 3")

if __name__ == '__main__':
    # 先连上
    print("📡 连接手机...")
    adb("devices")  # 触发连接
    
    print("📸 截屏...")
    img = screenshot()
    if img is None:
        print("❌ 截屏失败")
        sys.exit(1)
    
    h, w = img.shape[:2]
    print(f"   分辨率: {w}x{h}")
    
    # 保存截图
    cv2.imwrite('/tmp/screen_debug.png', img)
    
    print("\n🔍 识别所有文字...")
    texts = find_all_text(img)
    
    if not texts:
        print("   ❌ 未识别到文字（游戏可能是图形渲染）")
    else:
        # 按行分组（y坐标相近的在一行）
        lines = {}
        for text, x1, y1, x2, y2, conf in texts:
            row = y1 // 80  # 80px 内算同一行
            if row not in lines:
                lines[row] = []
            lines[row].append((text, x1, y1, x2, y2, conf))
        
        print(f"   共识别到 {len(texts)} 个文字块")
        print()
        
        # 按行从上到下显示
        for row in sorted(lines.keys()):
            items = lines[row]
            line_text = " | ".join([t for t, *_ in items])
            avg_y = sum(y1 for _, _, y1, _, _, _ in items) // len(items)
            print(f"  📍 y≈{avg_y}:  {line_text}")
    
    print("\n✅ 就绪！输入要找的文字，我会点击它")
