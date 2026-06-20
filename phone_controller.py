#!/usr/bin/env python3
"""phone_controller.py v2.0 — 手机终极控制台

策略层级（自动选择）:
  L1 ⚡ uiautomator XML 解析    → 0ms延迟, 100%准确 (标准App)
  L2 👁️ OCR 视觉识别            → ~500ms延迟, 85-95%准确 (游戏/自定义UI)
  L3 🖥️ scrcpy 视频流控制      → ~35ms延迟, 人工辅助

用法:
  python3 phone_controller.py                        # 查看屏幕 + UI树
  python3 phone_controller.py "发送"                  # 智能查找并点击
  python3 phone_controller.py "发送" --id             # 优先用 resource-id
  python3 phone_controller.py "发送" --ocr            # 强制用OCR
  python3 phone_controller.py --mirror                # scrcpy 实时投屏
  python3 phone_controller.py --dump                  # 导出 UI 树
  python3 phone_controller.py "发送" --scroll         # 滚动查找
  python3 phone_controller.py "发送" --wait 15        # 等待元素出现
  python3 phone_controller.py --save-template <name>  # 保存屏幕区域为模板
  python3 phone_controller.py --match-template <name> # 模板匹配查找
  python3 phone_controller.py --match-template <name> --threshold 0.8  # 模板匹配（自定义阈值）
"""

import subprocess, sys, os, time, json, xml.etree.ElementTree as ET
import cv2, numpy as np
from adb_utils import adb_shell, screenshot, connect, log

# ─── 配置 ─────────────────────────────
ADB_HOST = os.environ.get("ADB_HOST", "10.150.0.1:40745")
TESSDATA = "/usr/share/tesseract-ocr/5/tessdata"
LANG = "chi_sim+eng"

# ═══════════════════════════════════════
# L1: UIAUTOMATOR — 0ms / 100%准确
# ═══════════════════════════════════════

def dump_ui():
    """导出 UI 层级树 XML"""
    adb_shell("uiautomator dump /sdcard/ui.xml 2>/dev/null")
    xml_str = adb_shell("cat /sdcard/ui.xml")
    # 截取 XML 部分 (uiautomator dump 可能输出额外信息)
    start = xml_str.find('<?xml')
    if start == -1:
        return None
    return xml_str[start:]

def parse_ui(xml_str=None):
    """解析 UI 树，返回 [(text, resource_id, class_name, bounds, clickable, enabled, ...), ...]"""
    if xml_str is None:
        xml_str = dump_ui()
    if xml_str is None:
        return []

    root = ET.fromstring(xml_str)
    elements = []

    def walk(node):
        attrs = node.attrib
        text = attrs.get('text', '')
        rid = attrs.get('resource-id', '')
        cls = attrs.get('class', '')
        bounds = attrs.get('bounds', '')
        clickable = attrs.get('clickable', 'false') == 'true'
        enabled = attrs.get('enabled', 'true') == 'true'
        content_desc = attrs.get('content-desc', '')
        pkg = attrs.get('package', '')

        if text or content_desc or rid:
            # 解析 bounds
            b = bounds.replace('][', ',').replace('[', '').replace(']', '').split(',')
            if len(b) == 4:
                x1, y1, x2, y2 = map(int, b)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                elements.append({
                    'text': text,
                    'content_desc': content_desc,
                    'resource_id': rid,
                    'class': cls,
                    'package': pkg,
                    'bounds': (x1, y1, x2, y2),
                    'center': (cx, cy),
                    'clickable': clickable,
                    'enabled': enabled,
                })

        for child in node:
            walk(child)

    walk(root)
    return elements

def find_ui_elements(target, elements=None):
    """
    在 UI 树中查找目标。匹配优先级:
    1. resource-id 精确包含
    2. text 精确/模糊匹配
    3. content-desc 匹配
    """
    if elements is None:
        elements = parse_ui()
    
    target_lower = target.lower()
    results = []

    for el in elements:
        score = 0
        match_type = ""

        # resource-id 匹配 (最高优先级)
        rid = el['resource_id'].lower()
        if target_lower in rid:
            # 更精确的 ID 匹配给更高分
            rid_parts = rid.split('/')[-1].replace('_', ' ').replace('-', ' ')
            if target_lower in rid_parts:
                score = 100
                match_type = "resource-id(精确)"
            else:
                score = 90
                match_type = "resource-id"

        # text 匹配
        text = el['text'].lower()
        if target_lower == text:
            score = max(score, 95)
            match_type = "text(精确)"
        elif target_lower in text:
            score = max(score, 80)
            match_type = "text(包含)"
        elif text in target_lower:
            score = max(score, 70)
            match_type = "text(被包含)"

        # content-desc 匹配
        desc = el['content_desc'].lower()
        if target_lower == desc:
            score = max(score, 85)
            match_type = "content-desc(精确)"
        elif target_lower in desc:
            score = max(score, 75)
            match_type = "content-desc"

        if score > 0:
            el['score'] = score
            el['match_type'] = match_type
            results.append(el)

    # 按分数降序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

# ═══════════════════════════════════════
# L2: OCR 视觉识别（复用 smart_tap v2）
# ═══════════════════════════════════════

_ocr_api = None

def _get_ocr():
    global _ocr_api
    if _ocr_api is None:
        import tesserocr
        _ocr_api = tesserocr.PyTessBaseAPI(lang=LANG, path=TESSDATA)
    return _ocr_api

def shot():
    return screenshot()

def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    kernel = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
    sharp = cv2.filter2D(enhanced, -1, kernel)
    return sharp

def ocr(img, preprocess_img=True):
    import tesserocr
    from PIL import Image

    api = _get_ocr()
    if preprocess_img:
        img = preprocess(img)

    if len(img.shape) == 2:
        pil = Image.fromarray(img)
    else:
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

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
                cx = (box[0] + box[2]) // 2
                cy = (box[1] + box[3]) // 2
                results.append({
                    'text': text.strip(),
                    'bounds': (box[0], box[1], box[2], box[3]),
                    'center': (cx, cy),
                    'confidence': conf,
                    'match_type': 'OCR',
                    'clickable': True,
                })
            if not ri.Next(tesserocr.RIL.WORD):
                break
    return results

def find_ocr_elements(target, words=None, min_conf=0):
    if words is None:
        img = shot()
        words = ocr(img)

    target_lower = target.lower()
    results = []

    for w in words:
        if w['confidence'] < min_conf:
            continue
        text_lower = w['text'].lower()
        if target_lower in text_lower:
            w['score'] = w['confidence']
            results.append(w)

    results.sort(key=lambda x: x['score'], reverse=True)
    return results

# ═══════════════════════════════════════
# L3: scrcpy — 实时视频流
# ═══════════════════════════════════════

def start_mirror(max_size=1024, bitrate='8M', fps=60):
    """启动 scrcpy 实时投屏（最低延迟配置）"""
    print("🖥️  启动 scrcpy 实时投屏...")
    print(f"   分辨率: max {max_size}px | 码率: {bitrate} | 帧率: {fps}fps")
    cmd = (
        f"scrcpy --max-size {max_size} --bit-rate {bitrate} "
        f"--max-fps {fps} --no-audio --window-title '📱 手机实时画面' "
        f"--serial {ADB_HOST} 2>&1"
    )
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    # 非阻塞，后台运行
    print("   ✅ scrcpy 已启动 (Ctrl+C 停止)")
    return proc

# ═══════════════════════════════════════
# 操作层
# ═══════════════════════════════════════

def tap(x, y):
    adb_shell(f"input tap {x} {y}")
    print(f"  ✅ 点击 ({x}, {y})")

def long_press(x, y, duration=800):
    adb_shell(f"input swipe {x} {y} {x} {y} {duration}")

def swipe(x1, y1, x2, y2, duration=300):
    adb_shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")

def key(keycode):
    adb_shell(f"input keyevent {keycode}")

def type_text(text):
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        escaped = text.replace("'", "\\'")
        adb_shell(f"service call clipboard 4 i32 1 s16 '{escaped}' s16 'label'")
        print(f"  ✅ 已写入剪贴板 (中文): {text}")
    else:
        adb_shell(f"input text '{text}'")
        print(f"  ✅ 输入: {text}")

# ═══════════════════════════════════════
# 智能查找 — 自动选择 L1/L2
# ═══════════════════════════════════════

def smart_find(target, force_ocr=False, min_conf=0, prefer_id=True):
    """
    智能查找目标元素。先用 UI 树，失败回退 OCR。
    返回 (元素列表, 策略名称, 耗时ms)
    """
    t0 = time.time()

    if not force_ocr:
        print(f"⚡ L1: UI树查找 '{target}'...")
        try:
            elements = parse_ui()
            results = find_ui_elements(target, elements)
            elapsed = int((time.time() - t0) * 1000)

            if results:
                print(f"   ✅ 找到 {len(results)} 个元素 ({elapsed}ms)")
                return results, "UI", elapsed
            else:
                print(f"   ⚠️ UI树未找到 ({elapsed}ms)，回退OCR...")
        except Exception as e:
            print(f"   ❌ UI树解析失败: {e}，回退OCR...")

    # 回退到 OCR
    print(f"👁️ L2: OCR查找 '{target}'...")
    t1 = time.time()
    img = shot()
    words = ocr(img)
    results = find_ocr_elements(target, words, min_conf)
    elapsed = int((time.time() - t1) * 1000)

    if results:
        print(f"   ✅ 找到 {len(results)} 个匹配 ({elapsed}ms)")
    else:
        print(f"   ❌ OCR也未找到 ({elapsed}ms)")

    return results, "OCR", elapsed

# ═══════════════════════════════════════
# 滚动查找 & 等待
# ═══════════════════════════════════════

def smart_find_scroll(target, force_ocr=False, min_conf=0, max_scrolls=5):
    for i in range(max_scrolls):
        results, strategy, latency = smart_find(target, force_ocr, min_conf)
        if results:
            return results, strategy, latency, i + 1
        if i < max_scrolls - 1:
            print(f"  📜 第 {i+1} 次滚动，还没找到 '{target}'...")
            adb_shell("input swipe 720 2400 720 800 200")
            time.sleep(1.5)
    return [], "scroll", 0, max_scrolls

def wait_for_element(target, timeout=15, interval=1.5):
    print(f"  ⏳ 等待 '{target}' 出现（超时 {timeout}s）...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        results, strategy, latency = smart_find(target)
        if results:
            elapsed = int((time.time() - t0) * 1000)
            print(f"  ✅ 找到 '{target}'（{elapsed}ms, {strategy}）")
            return results
        time.sleep(interval)
    print(f"  ❌ 超时 {timeout}s，'{target}' 未出现")
    return []

# ═══════════════════════════════════════
# 显示层
# ═══════════════════════════════════════

def show_ui_tree(elements, max_items=30):
    """显示 UI 树摘要"""
    print(f"\n📋 UI 树 ({len(elements)} 个元素):")
    print(f"{'文本':<20} {'ID':<40} {'坐标':<15} {'可点击'}")
    print("-" * 90)

    shown = 0
    for el in elements:
        if el['text'] or el['content_desc'] or el['resource_id']:
            label = el['text'] or el['content_desc'] or el['resource_id'].split('/')[-1]
            rid = el['resource_id'][:38] if el['resource_id'] else '-'
            cx, cy = el['center']
            click = '✓' if el['clickable'] else '-'
            print(f"{label:<20} {rid:<40} ({cx},{cy}){'':<8} {click}")
            shown += 1
            if shown >= max_items:
                print(f"  ... 还有 {len(elements) - shown} 个元素未显示")
                break


# ═══════════════════════════════════════
# L4: 模板匹配
# ═══════════════════════════════════════

TEMPLATES_DIR = "/workspace/templates"

def ensure_templates_dir():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

def save_template(name, x1, y1, x2, y2):
    """保存屏幕上指定区域为模板"""
    ensure_templates_dir()
    img = screenshot()
    if img is None:
        return False
    roi = img[y1:y2, x1:x2]
    path = os.path.join(TEMPLATES_DIR, name + '.png')
    cv2.imwrite(path, roi)
    # 保存位置信息
    info = {"name": name, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "w": x2-x1, "h": y2-y1}
    with open(os.path.join(TEMPLATES_DIR, name + '.json'), 'w') as f:
        json.dump(info, f)
    print(f"✅ 模板 '{name}' 已保存 ({x2-x1}x{y2-y1}px)")
    return True

def match_template(name, threshold=0.7):
    """在屏幕上查找模板，返回匹配位置列表"""
    template_path = os.path.join(TEMPLATES_DIR, name + '.png')
    if not os.path.exists(template_path):
        print(f"❌ 模板 '{name}' 不存在")
        return []

    template = cv2.imread(template_path)
    if template is None:
        return []
    th, tw = template.shape[:2]

    img = screenshot()
    if img is None:
        return []

    result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)

    matches = []
    for pt in zip(*locations[::-1]):
        cx = pt[0] + tw // 2
        cy = pt[1] + th // 2
        conf = float(result[pt[1], pt[0]])
        matches.append({
            'text': name,
            'center': (cx, cy),
            'bounds': (pt[0], pt[1], pt[0] + tw, pt[1] + th),
            'confidence': conf,
            'match_type': 'template',
            'clickable': True,
        })

    # 去重（合并重叠匹配）
    return dedup_matches(matches)

def dedup_matches(matches, iou_threshold=0.3):
    """NMS 去重"""
    if not matches:
        return []
    matches = sorted(matches, key=lambda m: m['confidence'], reverse=True)
    kept = []
    for m in matches:
        x1, y1, x2, y2 = m['bounds']
        overlap = False
        for k in kept:
            kx1, ky1, kx2, ky2 = k['bounds']
            ix1 = max(x1, kx1); iy1 = max(y1, ky1)
            ix2 = min(x2, kx2); iy2 = min(y2, ky2)
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                union = (x2-x1)*(y2-y1) + (kx2-kx1)*(ky2-ky1) - inter
                if inter / union > iou_threshold:
                    overlap = True
                    break
        if not overlap:
            kept.append(m)
    return kept

def smart_find_all(target, force_ocr=False, min_conf=0, threshold=0.7):
    """L1 + L2 + L4 全策略查找"""
    t0 = time.time()
    all_results = []

    # L1: UI 树
    try:
        elements = parse_ui()
        ui_results = find_ui_elements(target, elements)
        all_results.extend(ui_results)
    except Exception as e:
        log("WARN", "phone_controller", f"L1 failed: {e}")

    # L2: OCR
    if not all_results or force_ocr:
        try:
            img = shot()
            words = ocr(img)
            ocr_results = find_ocr_elements(target, words, min_conf)
            all_results.extend(ocr_results)
        except Exception as e:
            log("WARN", "phone_controller", f"L2 failed: {e}")

    # L4: 模板匹配
    if not all_results:
        try:
            tm_results = match_template(target, threshold)
            all_results.extend(tm_results)
        except Exception as e:
            log("WARN", "phone_controller", f"L4 failed: {e}")

    all_results.sort(key=lambda x: x.get('score', x.get('confidence', 0)), reverse=True)
    elapsed = int((time.time() - t0) * 1000)
    return all_results, "ALL", elapsed

# ═══════════════════════════════════════
# 主入口
# ═══════════════════════════════════════

def main():
    args = sys.argv[1:]

    # 特殊命令
    if '--mirror' in args:
        start_mirror()
        return

    if '--dump' in args:
        xml = dump_ui()
        print(xml[:5000])
        return

    if '--ui' in args:
        elements = parse_ui()
        show_ui_tree(elements)
        return

    if '--save-template' in args:
        idx = args.index('--save-template')
        name = args[idx + 1]
        # 用当前截图选择区域... 简单实现：先截图显示，用户输入坐标
        print("📸 截图中，请稍后...")
        img = shot()
        h, w = img.shape[:2]
        print(f"屏幕: {w}x{h}")
        print("输入区域坐标: x1 y1 x2 y2")
        # 简单交互
        coords = input("> ").strip().split()
        if len(coords) == 4:
            save_template(name, int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3]))
        return

    if '--match-template' in args:
        idx = args.index('--match-template')
        name = args[idx + 1]
        threshold = 0.7
        if '--threshold' in args:
            ti = args.index('--threshold')
            threshold = float(args[ti + 1])
        results = match_template(name, threshold)
        if results:
            print(f"✅ 找到 {len(results)} 个匹配:")
            for i, r in enumerate(results[:5], 1):
                cx, cy = r['center']
                conf = r['confidence']
                print(f"  [{i}] ({cx},{cy}) 置信度={conf:.0%}")
            # 点击第一个
            cx, cy = results[0]['center']
            adb_shell(f"input tap {cx} {cy}")
        else:
            print(f"❌ 未找到模板 '{name}'")
        return

    # 解析参数
    target = None
    force_ocr = '--ocr' in args
    prefer_id = '--id' in args
    min_conf = 50
    action = "tap"
    tap_idx = 0

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--conf" and i+1 < len(args):
            min_conf = int(args[i+1]); i += 2
        elif a == "--tap" and i+1 < len(args):
            tap_idx = int(args[i+1]) - 1; i += 2
        elif a == "--long":
            action = "long"; i += 1
        elif a == "--ocr":
            force_ocr = True; i += 1
        elif a == "--id":
            prefer_id = True; i += 1
        elif a in ("--swipe", "--type"):
            i += 2
        elif a.startswith("--"):
            i += 1
        elif target is None:
            target = a; i += 1
        else:
            i += 1

    scroll = '--scroll' in args
    wait_timeout = None
    if '--wait' in args:
        idx = args.index('--wait')
        if idx + 1 < len(args):
            try:
                wait_timeout = int(args[idx + 1])
            except ValueError:
                wait_timeout = 15
                print(f"  ⚠️ --wait 值无效，使用默认 15s")

    if not target:
        # 无目标：显示状态
        print("📱 手机控制器 v1.0")
        print(f"   连接: {ADB_HOST}")
        print(f"\n⚡ L1: UI树   | 👁️ L2: OCR   | 🖥️ L3: scrcpy")
        print(f"   0ms/100%     | ~500ms/90%   | ~35ms/人工")
        print(f"\n用法: phone_controller.py <文字> [--ocr] [--conf N] [--tap N]")
        print(f"      phone_controller.py --ui      # 查看UI树")
        print(f"      phone_controller.py --dump    # 导出UI树XML")
        print(f"      phone_controller.py --mirror  # scrcpy投屏")
        print(f"      phone_controller.py --save-template <name>  # 保存模板")
        print(f"      phone_controller.py --match-template <name> [--threshold 0.8]  # 匹配模板")
        return

    # 智能查找（支持 --scroll 和 --wait）
    if wait_timeout and target:
        results = wait_for_element(target, wait_timeout)
    elif scroll and target:
        results, strategy, latency, scrolls = smart_find_scroll(target, force_ocr, min_conf)
        print(f"  📜 滚动次数: {scrolls}")
    else:
        results, strategy, latency = smart_find(target, force_ocr, min_conf)

    if not results:
        print(f"\n  ❌ 所有策略均未找到 '{target}'")
        return

    # 显示结果
    print(f"\n📍 找到 {len(results)} 个匹配 ({strategy}):")
    for idx, el in enumerate(results[:5], 1):
        cx, cy = el['center']
        score = el.get('score', el.get('confidence', 0))
        match_type = el.get('match_type', '?')
        text = el.get('text', '') or el.get('content_desc', '') or el.get('resource_id', '')[:30]
        clickable = '🔘' if el.get('clickable') else '  '
        marker = '👉' if idx == tap_idx + 1 else '  '
        print(f"    {marker} [{idx}] {clickable} '{text}' @ ({cx},{cy}) {match_type} {score}%")

    # 选择
    idx = max(0, min(tap_idx, len(results) - 1))
    el = results[idx]
    cx, cy = el['center']
    text = el.get('text', '') or el.get('content_desc', '') or '元素'

    print(f"\n🎯 选中 [{idx+1}] '{text}' ({cx},{cy})")

    # 执行
    if action == "long":
        long_press(cx, cy)
    else:
        tap(cx, cy)


if __name__ == '__main__':
    main()
