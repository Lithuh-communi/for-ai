#!/usr/bin/env python3
"""
🎥 实时屏幕流 — 持续截图 + 缓存，需要"看"时零等待

用法:
  python3 live_screen.py --serve &    # 后台持续截屏
  python3 live_screen.py --see        # 立刻看屏幕（不等截图）
  python3 live_screen.py --tap "发送"  # 找字点击
  python3 live_screen.py --stop       # 停止
"""

import subprocess, sys, os, time, json, threading

ADB_HOST = os.environ.get("ADB_HOST", "10.150.0.1:40745")
FRAME_FILE = "/tmp/live_frame.png"
STATE_FILE = "/tmp/live_state.json"
PID_FILE = "/tmp/live_screen.pid"

def capture():
    """截一帧"""
    path = f"/tmp/_lc_{os.getpid()}.png"
    subprocess.run(f"adb connect {ADB_HOST} && adb exec-out screencap -p > {path}",
                   shell=True, capture_output=True, timeout=5)
    img = None
    try:
        import cv2
        img = cv2.imread(path)
    except: pass
    try: os.remove(path)
    except: pass
    return img

# ═══════════════════ SERVE ═══════════════════

def cmd_serve():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                os.kill(int(f.read()), 0)
            print(f"⚠️ 已在运行")
            return
        except: os.remove(PID_FILE)

    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    count = 0
    print(f"🎥 截屏服务启动 (PID {os.getpid()}, 每0.3s)")
    print("   --see 查看 | --stop 停止")

    try:
        while True:
            img = capture()
            if img is not None:
                import cv2
                cv2.imwrite(FRAME_FILE, img)
                count += 1
                with open(STATE_FILE, 'w') as f:
                    json.dump({'count': count, 'time': time.time(), 'shape': list(img.shape)}, f)
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        try: os.remove(PID_FILE)
        except: pass
        print("\n👋 已停止")

# ═══════════════════ SEE ═══════════════════

def cmd_see():
    import cv2
    from PIL import Image
    import tesserocr

    if os.path.exists(FRAME_FILE):
        age = time.time() - os.path.getmtime(FRAME_FILE)
        img = cv2.imread(FRAME_FILE)
        method = "缓存"
    else:
        img = capture()
        age = 0
        method = "实时截"

    if img is None:
        print("❌ 截屏失败")
        return

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    api = tesserocr.PyTessBaseAPI(lang='chi_sim+eng', path='/usr/share/tesseract-ocr/5/tessdata')
    pil = Image.fromarray(enhanced)
    api.SetImage(pil)
    api.Recognize()

    ri = api.GetIterator()
    words = []
    if ri:
        while True:
            text = ri.GetUTF8Text(tesserocr.RIL.WORD)
            conf = ri.Confidence(tesserocr.RIL.WORD)
            box = ri.BoundingBox(tesserocr.RIL.WORD)
            if text and text.strip() and box:
                words.append({'text': text.strip(), 'x': (box[0]+box[2])//2, 'y': (box[1]+box[3])//2, 'conf': conf})
            if not ri.Next(tesserocr.RIL.WORD):
                break
    api.End()

    # App 识别
    app = 'unknown'
    all_text = ' '.join([w['text'] for w in words])
    if '技能列表' in all_text or 'Messages' in all_text:
        app = 'rikkahub'
    elif any(k in all_text for k in ['QQ', '消息', '联系人']):
        app = 'QQ'

    print(f"📱 {w}x{h} | App: {app} | 来源: {method}({int(age*1000)}ms前) | {len(words)}词")
    print()

    by_y = {}
    for w in words:
        row = w['y'] // 80
        by_y.setdefault(row, []).append(w)

    for row in sorted(by_y.keys()):
        items = by_y[row]
        avg_y = sum(w['y'] for w in items) // len(items)
        texts = [f"\033[32m{w['text']}\033[0m" if w['conf']>70 else f"\033[33m{w['text']}\033[0m" if w['conf']>40 else f"\033[90m{w['text']}\033[0m" for w in items]
        print(f"  y={avg_y:4d}: {' | '.join(texts[:12])}")

# ═══════════════════ TAP ═══════════════════

def cmd_tap(target):
    import cv2
    from PIL import Image
    import tesserocr

    # 坐标格式 "x,y"
    if ',' in target:
        parts = target.split(',')
        if len(parts) == 2:
            x, y = int(parts[0]), int(parts[1])
            subprocess.run(f"adb connect {ADB_HOST} && adb shell input tap {x} {y}", shell=True, timeout=5)
            print(f"✅ 点击 ({x}, {y})")
            return

    # 取帧
    if os.path.exists(FRAME_FILE):
        img = cv2.imread(FRAME_FILE)
    else:
        img = capture()

    if img is None:
        print("❌ 无画面")
        return

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    api = tesserocr.PyTessBaseAPI(lang='chi_sim+eng', path='/usr/share/tesseract-ocr/5/tessdata')
    pil = Image.fromarray(enhanced)
    api.SetImage(pil)
    api.Recognize()

    ri = api.GetIterator()
    best = None
    if ri:
        while True:
            text = ri.GetUTF8Text(tesserocr.RIL.WORD)
            conf = ri.Confidence(tesserocr.RIL.WORD)
            box = ri.BoundingBox(tesserocr.RIL.WORD)
            if text and target.lower() in text.lower() and box:
                cx, cy = (box[0]+box[2])//2, (box[1]+box[3])//2
                if best is None or conf > best[0]:
                    best = (conf, text.strip(), cx, cy)
            if not ri.Next(tesserocr.RIL.WORD):
                break
    api.End()

    if best is None:
        print(f"❌ 没找到 '{target}'")
        return

    conf, text, x, y = best
    subprocess.run(f"adb connect {ADB_HOST} && adb shell input tap {x} {y}", shell=True, timeout=5)
    print(f"✅ 点击 '{text}' ({x},{y}) conf={conf}%")

# ═══════════════════ STOP ═══════════════════

def cmd_stop():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read())
        try:
            os.kill(pid, 15)
            print(f"✅ 已停止 (PID {pid})")
        except:
            print("⚠️ 进程不存在")
        os.remove(PID_FILE)
    else:
        print("⚠️ 未运行")

# ═══════════════════ MAIN ═══════════════════

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("--serve | --see | --tap X | --stop")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == '--serve': cmd_serve()
    elif cmd == '--see': cmd_see()
    elif cmd == '--tap' and len(sys.argv) > 2: cmd_tap(sys.argv[2])
    elif cmd == '--stop': cmd_stop()
    else: print(f"未知: {cmd}")
