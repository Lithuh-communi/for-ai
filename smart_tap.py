#!/usr/bin/env python3
"""
smart_tap.py v2.1 — 智能屏幕控制（adb_utils 版）

用法:
  python3 smart_tap.py                        # 查看屏幕
  python3 smart_tap.py "发送"                  # 找字并点击
  python3 smart_tap.py "发送" --tap 2          # 点第2个匹配
  python3 smart_tap.py "发送" --long           # 长按
  python3 smart_tap.py "发送" --conf 60        # 最低置信度60
  python3 smart_tap.py --list                  # 仅列出文字
  python3 smart_tap.py --swipe 500,2000,500,500  # 滑动
  python3 smart_tap.py "发送" --scroll         # 滚动查找
  python3 smart_tap.py --region x,y,w,h        # 区域 OCR
"""
import sys, os, cv2, numpy as np, time, json
from adb_utils import adb_shell, screenshot, log

# ─── 配置 ─────────────────────────────
ADB_HOST = os.environ.get("ADB_HOST", "10.150.0.1:40745")
TESSDATA = "/usr/share/tesseract-ocr/5/tessdata"
LANG = "chi_sim+eng"
CACHE_FILE = "/tmp/_screen_cache.json"

# ─── 截图层 ────────────────────────────

def shot():
    """截屏，返回 BGR numpy 数组"""
    return screenshot()

def preprocess(img):
    """图像预处理：增强对比度 + 自适应二值化，提高 OCR 准确率"""
    # 转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # CLAHE 对比度增强
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    # 锐化
    kernel = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
    sharp = cv2.filter2D(enhanced, -1, kernel)
    return sharp

# ─── OCR 层 ────────────────────────────

_ocr_api = None

def _get_ocr():
    """获取复用的 OCR API（单例）"""
    global _ocr_api
    if _ocr_api is None:
        import tesserocr
        _ocr_api = tesserocr.PyTessBaseAPI(lang=LANG, path=TESSDATA)
    return _ocr_api

def ocr(img, preprocess_img=True):
    """OCR 识别，返回 [(text, x1, y1, x2, y2, confidence), ...]"""
    from PIL import Image
    import tesserocr

    api = _get_ocr()
    if preprocess_img:
        img = preprocess(img)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    pil = Image.fromarray(img) if len(img.shape) == 2 else \
          Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    api.SetImage(pil)
    api.Recognize()

    results = []
    ri = api.GetIterator()
    if ri:
        while True:
            text = ri.GetUTF8Text(tesserocr.RIL.WORD)
            conf = ri.Confidence(tesserocr.RIL.WORD)
            box = ri.BoundingBox(tesserocr.RIL.WORD)
            if text and text.strip() and box:
                results.append((text.strip(), box[0], box[1], box[2], box[3], conf))
            if not ri.Next(tesserocr.RIL.WORD):
                break
    # 不清除 API，下次复用
    return results


def ocr_region(img, x, y, w, h):
    """只识别指定区域的 OCR"""
    roi = img[y:y+h, x:x+w]
    if roi.size == 0:
        return []
    return ocr(roi)


# ─── 查找层 ────────────────────────────

def find_text(words, target, min_conf=0, fuzzy=False):
    """
    在 OCR 结果中找目标文字
    fuzzy=True: 子串匹配 / 拼音首字母匹配
    返回 [(text, cx, cy, x1, y1, x2, y2, conf), ...] 按置信度降序
    """
    matches = []
    target_lower = target.lower()

    for text, x1, y1, x2, y2, conf in words:
        if conf < min_conf:
            continue
        text_lower = text.lower()

        matched = False
        if fuzzy:
            # 子串或包含关系
            if target_lower in text_lower or text_lower in target_lower:
                matched = True
            # 拼音首字母匹配（简单版）
            elif target_lower == _pinyin_initials(text):
                matched = True
        else:
            matched = (target_lower in text_lower)

        if matched:
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            matches.append((text, cx, cy, x1, y1, x2, y2, conf))

    # 按置信度降序
    matches.sort(key=lambda m: m[7], reverse=True)
    return matches

def _pinyin_initials(text):
    """简单拼音首（中文字）"""
    # 常见拼音首字母映射（简化版，覆盖高频字）
    import unicodedata
    initials = []
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            # 用拼音首字母近似（unicode 排序）
            code = ord(ch)
            if code < 0x4E00: initials.append('a')
            elif code < 0x5200: initials.append('b')
            elif code < 0x5A00: initials.append('c')
            elif code < 0x6000: initials.append('d')
            elif code < 0x6700: initials.append('e')
            elif code < 0x6F00: initials.append('f')
            elif code < 0x7700: initials.append('g')
            elif code < 0x8000: initials.append('h')
            elif code < 0x8500: initials.append('j')
            elif code < 0x8900: initials.append('k')
            elif code < 0x8E00: initials.append('l')
            elif code < 0x9500: initials.append('m')
            elif code < 0x9A00: initials.append('n')
            elif code < 0xA000: initials.append('o')
            elif code < 0xA500: initials.append('p')
            elif code < 0xAA00: initials.append('q')
            elif code < 0xB000: initials.append('r')
            elif code < 0xB800: initials.append('s')
            elif code < 0xC000: initials.append('t')
            elif code < 0xC800: initials.append('w')
            elif code < 0xD000: initials.append('x')
            elif code < 0xD800: initials.append('y')
            else: initials.append('z')
        elif ch.isalpha():
            initials.append(ch.lower())
    return ''.join(initials)

# ─── 操作层 ────────────────────────────

def tap(x, y):
    """点击"""
    adb_shell(f"input tap {x} {y}")
    print(f"  ✅ 点击 ({x}, {y})")

def long_press(x, y, duration=800):
    """长按"""
    adb_shell(f"input swipe {x} {y} {x} {y} {duration}")
    print(f"  ✅ 长按 ({x}, {y}) {duration}ms")

def double_tap(x, y, gap=100):
    """双击"""
    tap(x, y)
    time.sleep(gap / 1000.0)
    tap(x, y)

def swipe(x1, y1, x2, y2, duration=300):
    """滑动"""
    adb_shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")
    print(f"  ✅ 滑动 ({x1},{y1}) → ({x2},{y2})")

def key(keycode):
    """按键: back=4, home=3, enter=66, power=26"""
    adb_shell(f"input keyevent {keycode}")

def type_text(text, use_clipboard=False):
    """输入文字"""
    if use_clipboard:
        # 中文用剪贴板方式
        escaped = text.replace("'", "\\'")
        adb_shell(f"service call clipboard 4 i32 1 s16 '{escaped}' s16 'label'", timeout=5)
        print(f"  ✅ 已写入剪贴板: {text}（请长按粘贴）")
    else:
        adb_shell(f"input text '{text}'")
        print(f"  ✅ 输入: {text}")

# ─── 显示层 ────────────────────────────

def show_screen(img, words, min_conf=0):
    """显示屏幕内容和文字位置"""
    h, w = img.shape[:2]
    print(f"\n📱 屏幕: {w}x{h}")

    if not words:
        print("  ⚠️ 未识别到文字")
        return

    # 过滤低置信度
    filtered = words if min_conf == 0 else [w for w in words if w[5] >= min_conf]

    # 按行分组
    lines = {}
    for text, x1, y1, x2, y2, conf in filtered:
        row = y1 // 80
        if row not in lines:
            lines[row] = []
        lines[row].append((text, x1, y1, x2, y2, conf))

    print(f"\n📝 识别到 {len(filtered)} 个文字（置信度≥{min_conf}%）:")
    for row in sorted(lines.keys()):
        items = lines[row]
        avg_y = sum(it[2] for it in items) // len(items)
        parts = []
        for text, _, _, _, _, conf in items:
            if conf >= 70:  parts.append(f"\033[32m{text}\033[0m")
            elif conf >= 40: parts.append(f"\033[33m{text}\033[0m")
            else:            parts.append(f"\033[90m{text}\033[0m")
        line_str = " | ".join(parts)
        print(f"  y={avg_y:4d}: {line_str[:120]}")

    # 保存标注截图
    vis = img.copy()
    for text, x1, y1, x2, y2, conf in filtered:
        color = (0,255,0) if conf >= 70 else (0,200,200) if conf >= 40 else (100,100,100)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vis, f"{text}({conf})", (x1, y1-4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    out = '/tmp/_annotated.png'
    cv2.imwrite(out, vis)
    print(f"\n📸 标注截图: {out}")

# ─── 主入口 ────────────────────────────

def main():
    import argparse

    # 自定义参数解析（支持中文）
    args = sys.argv[1:]
    target = None
    min_conf = 0
    tap_idx = 0
    action = "tap"      # tap | long | double | list
    fuzzy = True
    swipe_coords = None
    text_input = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--conf" and i+1 < len(args):
            min_conf = int(args[i+1]); i += 2
        elif a == "--tap" and i+1 < len(args):
            tap_idx = int(args[i+1]) - 1; i += 2
        elif a == "--long":
            action = "long"; i += 1
        elif a == "--double":
            action = "double"; i += 1
        elif a == "--list":
            action = "list"; i += 1
        elif a == "--swipe" and i+1 < len(args):
            parts = args[i+1].split(",")
            if len(parts) == 4:
                swipe_coords = tuple(int(p) for p in parts)
            i += 2
        elif a == "--type" and i+1 < len(args):
            text_input = args[i+1]; action = "type"; i += 2
        elif a == "--exact":
            fuzzy = False; i += 1
        elif a.startswith("--"):
            i += 1
        elif target is None:
            target = a; i += 1
        else:
            i += 1

    scroll = '--scroll' in args

    region = None
    if '--region' in args:
        idx = args.index('--region')
        if idx + 1 < len(args):
            parts = args[idx + 1].split(',')
            if len(parts) == 4:
                region = tuple(int(p) for p in parts)

    # 截屏
    print("📸 截屏...")
    img = shot()
    if img is None:
        print("❌ 截屏失败，检查 ADB 连接")
        sys.exit(1)

    # OCR
    print("🔍 OCR 识别...")
    if region:
        rx, ry, rw, rh = region
        print(f"  区域: ({rx},{ry},{rw},{rh})")
        words = ocr_region(img, rx, ry, rw, rh)
    else:
        words = ocr(img)
    show_screen(img, words, min_conf)

    # 纯滑动
    if swipe_coords:
        print()
        swipe(*swipe_coords)
        return

    # 纯输入
    if action == "type" and text_input:
        print(f"\n⌨️  输入: {text_input}")
        type_text(text_input, use_clipboard=any('\u4e00' <= c <= '\u9fff' for c in text_input))
        return

    # 仅列出
    if action == "list" or not target:
        if not target:
            print(f"\n💡 用法: smart_tap.py <文字> [--conf N] [--tap N] [--long|--double] [--swipe x1,y1,x2,y2] [--type 文字]")
        return

    # 查找目标
    print(f"\n🔍 找 '{target}'（{'模糊' if fuzzy else '精确'}匹配, 置信度≥{min_conf}）...")
    matches = find_text(words, target, min_conf, fuzzy)

    if not matches:
        if scroll:
            print(f"  📜 OCR 没找到，尝试滚动查找...")
            from phone_controller import smart_find_scroll
            results, strategy, latency, scrolls = smart_find_scroll(target, fuzzy, min_conf)
            if results:
                print(f"  ✅ 滚动找到 {len(results)} 个匹配 ({scrolls} 次滚动)")
                # 将 phone_controller 结果转换为 smart_tap 格式
                matches = []
                for el in results:
                    text = el.get('text', '')
                    cx, cy = el['center']
                    x1, y1, x2, y2 = el['bounds']
                    conf = el.get('confidence', el.get('score', 0))
                    matches.append((text, cx, cy, x1, y1, x2, y2, conf))
                matches.sort(key=lambda m: m[7], reverse=True)
            else:
                print(f"  ❌ 滚动也没找到 '{target}'（{scrolls} 次）")
                return
        else:
            print(f"  ❌ 没找到 '{target}'")
            return

    if len(matches) > 1:
        print(f"  📍 找到 {len(matches)} 个匹配:")
        for idx, (text, cx, cy, _, _, _, _, conf) in enumerate(matches[:5], 1):
            marker = "👉" if idx == tap_idx+1 else "  "
            print(f"    {marker} [{idx}] '{text}' @ ({cx},{cy}) 置信度={conf}%")

    # 选择匹配项
    idx = max(0, min(tap_idx, len(matches)-1))
    text, cx, cy, x1, y1, x2, y2, conf = matches[idx]

    print(f"\n  🎯 选中 [{idx+1}] '{text}' ({cx},{cy}) 置信度={conf}%")
    print(f"  📍 位置: {x1},{y1} → {x2},{y2} (面积: {(x2-x1)*(y2-y1)}px²)")

    # 执行动作
    if action == "long":
        long_press(cx, cy)
    elif action == "double":
        double_tap(cx, cy)
    else:
        tap(cx, cy)


if __name__ == '__main__':
    main()
