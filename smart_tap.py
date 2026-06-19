#!/usr/bin/env python3
"""智能点击器 - 看屏幕、找文字、精准点（自动清理截图）"""
import subprocess, sys, os, cv2, numpy as np

ADB = "10.150.0.1:40745"

def adb(cmd):
    subprocess.run(f"adb connect {ADB} && adb {cmd}", shell=True, capture_output=True, timeout=15)

def shot():
    """截屏 → 读取 → 删文件，一条龙"""
    adb("exec-out screencap -p > /tmp/_s.png")
    img = cv2.imread('/tmp/_s.png')
    os.remove('/tmp/_s.png')  # 读完秒删
    return img

def ocr(img):
    from PIL import Image
    import tesserocr
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    api = tesserocr.PyTessBaseAPI(lang='chi_sim+eng', path='/usr/share/tesseract-ocr/5/tessdata')
    api.SetImage(pil)
    api.Recognize()
    ri = api.GetIterator()
    results = []
    if ri:
        while True:
            text = ri.GetUTF8Text(tesserocr.RIL.WORD)
            conf = ri.Confidence(tesserocr.RIL.WORD)
            box = ri.BoundingBox(tesserocr.RIL.WORD)
            if text and text.strip() and box:
                results.append((text.strip(), *box, conf))
            if not ri.Next(tesserocr.RIL.WORD):
                break
    api.End()
    return results

def tap(x, y):
    adb(f"shell input tap {x} {y}")
    print(f"  ✅ 点击 ({x}, {y})")

def find_and_tap(target, img=None):
    if img is None:
        img = shot()
    words = ocr(img)
    for text, x1, y1, x2, y2, conf in words:
        if target in text:
            cx, cy = (x1+x2)//2, (y1+y2)//2
            print(f"  🔍 找到 '{text}' → ({cx},{cy})")
            tap(cx, cy)
            return True
    print(f"  ❌ 没找到 '{target}'")
    return False

def show_screen(img, words=None):
    """显示屏幕内容和文字位置"""
    h, w = img.shape[:2]
    print(f"\n📱 屏幕: {w}x{h}")
    if words:
        # 按行分组
        lines = {}
        for text, x1, y1, x2, y2, conf in words:
            row = y1 // 100
            if row not in lines: lines[row] = []
            lines[row].append((text, x1, y1, x2, y2, conf))
        print(f"\n📝 识别到 {len(words)} 个文字：")
        for row in sorted(lines.keys()):
            items = lines[row]
            line_text = " | ".join([f"{t}" for t, *_ in items])
            avg_y = sum(y1 for _, _, y1, _, _, _ in items) // len(items)
            print(f"  y={avg_y:4d}: {line_text[:100]}")
        
        # 标注截图保存
        vis = img.copy()
        for text, x1, y1, x2, y2, conf in words:
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0,255,0), 2)
            cv2.putText(vis, text, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
        annotated = '/tmp/_annotated.png'
        cv2.imwrite(annotated, vis)
        print(f"\n  📸 标注截图: {annotated}（下次覆盖）")

if __name__ == '__main__':
    img = shot()
    if img is None:
        print("❌ 截屏失败")
        sys.exit(1)
    
    words = ocr(img)
    show_screen(img, words)
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
        print(f"\n🔍 找 '{target}'...")
        find_and_tap(target, img)
    else:
        print("\n💡 用法: python3 smart_tap.py <要点的文字>")
        print("   示例: python3 smart_tap.py 对战")
