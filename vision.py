#!/usr/bin/env python3
"""
👁️ 屏幕视觉分析引擎 — 不仅 OCR，真正"看懂"屏幕

输出结构化分析：
  - 当前 App
  - 区域划分（状态栏/导航栏/内容区/输入区）
  - 检测到的 UI 元素（按钮、输入框、列表...）
  - 文字内容 + 位置
  - 屏幕变化（与上一次对比）
"""

import cv2, numpy as np, json, os, time, sys

# ─── 工具层 ────────────────────────

def shot(adb_host="10.150.0.1:40745"):
    """截屏，返回 BGR numpy 数组"""
    import subprocess
    pid = os.getpid()
    path = f"/tmp/_vision_{pid}.png"
    subprocess.run(
        f"adb connect {adb_host} && adb exec-out screencap -p > {path}",
        shell=True, capture_output=True, timeout=15
    )
    img = cv2.imread(path)
    os.remove(path)
    return img

# ─── App 识别 ──────────────────────

def identify_app(img):
    """通过顶部标题栏识别当前 App"""
    h, w = img.shape[:2]
    # 状态栏区域
    status_bar = img[0:100, 0:w]
    # 标题栏区域（状态栏下方 100-250px）
    title_bar = img[100:300, 0:w]

    # 分析颜色分布来识别 App
    # QQ: 蓝色主题
    # 微信: 绿色
    # Rikkahub: 深色主题

    # 简单方法：看标题栏主色调
    avg_color = np.mean(title_bar, axis=(0, 1))
    b, g, r = avg_color

    # OCR 标题文字
    try:
        from PIL import Image
        import tesserocr
        api = tesserocr.PyTessBaseAPI(
            lang='chi_sim+eng',
            path='/usr/share/tesseract-ocr/5/tessdata'
        )
        pil = Image.fromarray(cv2.cvtColor(title_bar, cv2.COLOR_BGR2RGB))
        api.SetImage(pil)
        text = api.GetUTF8Text().strip()
        api.End()

        # 从标题文字推断 App
        app_clues = {
            'QQ': 'com.tencent.mobileqq',
            '微信': 'com.tencent.mm',
            '技能列表': 'rikkahub',
            'Messages': 'rikkahub',
            '设置': 'com.android.settings',
        }
        for clue, app_id in app_clues.items():
            if clue.lower() in text.lower():
                return app_id, text
        return 'unknown', text
    except:
        return 'unknown', ''

# ─── 区域分割 ──────────────────────

def segment_regions(img):
    """将屏幕分割为功能区域"""
    h, w = img.shape[:2]

    # 检测状态栏（顶部深色条 + 下方浅色渐变）
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 状态栏通常在顶部 80-120px
    status_h = 120
    # 导航栏在底部（如果有的话）
    nav_h = 150
    # 底部输入区（QQ/微信输入框区域）
    input_zone_top = h - 600

    regions = {
        'status_bar': (0, 0, w, status_h),
        'title_bar': (0, status_h, w, 280),
        'content': (0, 280, w, input_zone_top),
        'input_area': (0, input_zone_top, w, h),
    }

    # 检测内容区域的实际边界
    # 通过寻找大面积空白/颜色变化
    row_std = np.std(gray[100:, :], axis=1)
    smooth_std = np.convolve(row_std, np.ones(20)/20, mode='same')

    # 找内容区域的下边界（输入区开始处）
    for y in range(int(h*0.6), int(h*0.85)):
        if smooth_std[y] > np.mean(smooth_std) * 1.3:
            regions['content'] = (0, 280, w, y)
            regions['input_area'] = (0, y, w, h)
            break

    return regions

# ─── UI 元素检测 ──────────────────

def detect_ui_elements(img):
    """检测 UI 元素：按钮、输入框、列表项、图标等"""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elements = {
        'buttons': [],      # 可点击元素
        'input_fields': [], # 输入框
        'list_items': [],   # 列表项
        'images': [],       # 图片/图标
    }

    # 1. 检测输入框（底部白色/浅色矩形区域）
    # 输入框通常有边框
    edges = cv2.Canny(gray, 50, 150)
    # 在底部区域找矩形轮廓
    bottom = edges[int(h*0.7):h, :]
    contours, _ = cv2.findContours(bottom, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        real_y = y + int(h*0.7)
        if bw > 200 and bh > 40 and bw < w * 0.9:
            elements['input_fields'].append({
                'bounds': (x, real_y, x+bw, real_y+bh),
                'center': (x + bw//2, real_y + bh//2),
                'area': bw * bh
            })

    # 2. 检测按钮（文字周围有颜色/边框的矩形）
    # 找轮廓
    all_contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in all_contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        if 30 < bw < 300 and 30 < bh < 120:
            # 检查是否包含文字
            roi = img[y:y+bh, x:x+bw]
            roi_gray = gray[y:y+bh, x:x+bw]
            if np.std(roi_gray) > 30:  # 有内容
                elements['buttons'].append({
                    'bounds': (x, y, x+bw, y+bh),
                    'center': (x + bw//2, y + bh//2),
                    'area': bw * bh
                })

    # 3. 去重（合并重叠的检测结果）
    elements['buttons'] = _deduplicate(elements['buttons'])
    elements['input_fields'] = _deduplicate(elements['input_fields'])

    return elements

def _deduplicate(items, iou_threshold=0.5):
    """合并重叠的检测框"""
    if len(items) <= 1:
        return items

    kept = []
    used = set()
    for i, a in enumerate(items):
        if i in used:
            continue
        merged = a
        for j, b in enumerate(items):
            if j <= i or j in used:
                continue
            iou = _iou(merged['bounds'], b['bounds'])
            if iou > iou_threshold:
                merged = _merge_boxes(merged, b)
                used.add(j)
        kept.append(merged)
    return kept

def _iou(box_a, box_b):
    """两个框的 IoU"""
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = (box_a[2]-box_a[0]) * (box_a[3]-box_a[1])
    area_b = (box_b[2]-box_b[0]) * (box_b[3]-box_b[1])
    return inter / (area_a + area_b - inter + 1)

def _merge_boxes(a, b):
    return {
        'bounds': (
            min(a['bounds'][0], b['bounds'][0]),
            min(a['bounds'][1], b['bounds'][1]),
            max(a['bounds'][2], b['bounds'][2]),
            max(a['bounds'][3], b['bounds'][3]),
        ),
        'center': (
            (a['center'][0] + b['center'][0]) // 2,
            (a['center'][1] + b['center'][1]) // 2,
        ),
        'area': max(a.get('area', 0), b.get('area', 0)),
    }

# ─── OCR 文字 ──────────────────────

_ocr_api = None

def ocr_text(img, regions=None):
    """OCR 识别屏幕上所有文字，按区域分组"""
    global _ocr_api
    import tesserocr
    from PIL import Image

    if _ocr_api is None:
        _ocr_api = tesserocr.PyTessBaseAPI(
            lang='chi_sim+eng',
            path='/usr/share/tesseract-ocr/5/tessdata'
        )

    # 预处理
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    pil = Image.fromarray(enhanced)
    _ocr_api.SetImage(pil)
    _ocr_api.Recognize()

    ri = _ocr_api.GetIterator()
    words = []
    if ri:
        while True:
            text = ri.GetUTF8Text(tesserocr.RIL.WORD)
            conf = ri.Confidence(tesserocr.RIL.WORD)
            box = ri.BoundingBox(tesserocr.RIL.WORD)
            if text and text.strip() and box:
                words.append({
                    'text': text.strip(),
                    'bounds': (box[0], box[1], box[2], box[3]),
                    'center': ((box[0]+box[2])//2, (box[1]+box[3])//2),
                    'confidence': conf,
                })
            if not ri.Next(tesserocr.RIL.WORD):
                break

    # 按区域分组
    if regions:
        grouped = {
            'status_bar': [],
            'title_bar': [],
            'content': [],
            'input_area': [],
        }
        for w in words:
            cy = w['center'][1]
            if cy < regions['title_bar'][1]:
                grouped['status_bar'].append(w)
            elif cy < regions['content'][1]:
                grouped['title_bar'].append(w)
            elif cy < regions['input_area'][1]:
                grouped['content'].append(w)
            else:
                grouped['input_area'].append(w)
        return words, grouped

    return words, {}

# ─── 变化检测 ──────────────────────

_last_screen = None

def detect_changes(img):
    """与上一次截屏对比，返回变化区域"""
    global _last_screen
    current = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if _last_screen is None:
        _last_screen = current
        return {'changed': True, 'change_count': 0, 'total_change_area': 0, 'regions': [], 'note': '首次截屏'}

    if current.shape != _last_screen.shape:
        _last_screen = current
        return {'changed': True, 'change_count': 0, 'total_change_area': 0, 'regions': [], 'note': '分辨率变化'}

    # 差分
    diff = cv2.absdiff(current, _last_screen)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

    # 找变化区域
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    changes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:  # 忽略微小变化
            x, y, w, h = cv2.boundingRect(cnt)
            changes.append({'bounds': (x, y, x+w, y+h), 'area': area})

    change_count = len(changes)
    _last_screen = current
    return {
        'changed': change_count > 0,
        'change_count': change_count,
        'total_change_area': sum(c['area'] for c in changes) if changes else 0,
        'regions': sorted(changes, key=lambda c: c['area'], reverse=True)[:5] if changes else [],
    }

# ─── 综合分析 ──────────────────────

def analyze(img=None):
    """综合分析屏幕：App + 区域 + 元素 + 文字 + 变化"""
    if img is None:
        img = shot()

    h, w = img.shape[:2]

    # 并行分析（顺序执行，保持兼容）
    app_id, app_title = identify_app(img)
    regions = segment_regions(img)
    ui_elements = detect_ui_elements(img)
    words, grouped_words = ocr_text(img, regions)
    changes = detect_changes(img)

    return {
        'screen': {'width': w, 'height': h},
        'app': {'id': app_id, 'title': app_title},
        'regions': regions,
        'ui_elements': {
            'input_fields': len(ui_elements['input_fields']),
            'buttons': len(ui_elements['buttons']),
            'details': ui_elements,
        },
        'text': {
            'total_words': len(words),
            'by_region': {
                k: [w['text'] for w in v]
                for k, v in grouped_words.items()
            },
            'high_conf': [
                w for w in words if w['confidence'] >= 70
            ],
        },
        'changes': changes,
    }

def describe(img=None):
    """人类可读的屏幕描述"""
    result = analyze(img)
    r = result

    lines = []
    lines.append(f"📱 屏幕: {r['screen']['width']}x{r['screen']['height']}")
    lines.append(f"📦 App: {r['app']['id']} ({r['app']['title']})")
    lines.append(f"")

    # 内容区文字
    content_texts = r['text']['by_region'].get('content', [])[:20]
    if content_texts:
        lines.append(f"📝 内容区文字 ({len(content_texts)} 词):")
        lines.append(f"   {' '.join(content_texts)}")
        lines.append("")

    # 输入区
    input_texts = r['text']['by_region'].get('input_area', [])
    if input_texts:
        lines.append(f"⌨️ 输入区: {' '.join(input_texts)}")
    else:
        lines.append(f"⌨️ 输入区: (空)")

    # 检测到的按钮
    buttons = r['ui_elements']['details']['buttons']
    if buttons:
        lines.append(f"\n🔘 检测到 {len(buttons)} 个按钮:")
        for btn in buttons[:8]:
            cx, cy = btn['center']
            lines.append(f"   ({cx}, {cy}) {btn['bounds']}")

    # 输入框
    inputs = r['ui_elements']['details']['input_fields']
    if inputs:
        lines.append(f"\n📝 检测到 {len(inputs)} 个输入框:")
        for inp in inputs[:3]:
            cx, cy = inp['center']
            lines.append(f"   ({cx}, {cy}) {inp['bounds']}")

    # 变化
    if r['changes']['changed']:
        lines.append(f"\n🔄 屏幕有变化 ({r['changes']['change_count']} 个区域)")
    else:
        lines.append(f"\n🔄 屏幕无变化")

    return '\n'.join(lines)


# ─── 独立运行 ──────────────────────

if __name__ == '__main__':
    print("📸 截屏 + 分析中...")
    img = shot()
    print(describe(img))

    # 保存标注截图
    vis = img.copy()
    for btn in analyze(img)['ui_elements']['details']['buttons']:
        x1, y1, x2, y2 = btn['bounds']
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
    for inp in analyze(img)['ui_elements']['details']['input_fields']:
        x1, y1, x2, y2 = inp['bounds']
        cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 0, 0), 3)

    out = '/tmp/_vision_annotated.png'
    cv2.imwrite(out, vis)
    print(f"\n📸 标注截图: {out}")
