#!/usr/bin/env python3
"""
🎬 Rikkahub 全能演示 — 一条龙展示所有新能力

跑这个脚本就能看到 v2.0 升级的全部功能：
  1. 📱 手机状态检查  → phone_monitor
  2. 👁️ 屏幕 UI 分析  → phone_controller (UI树)
  3. 🔍 找字点击      → phone_controller (OCR)
  4. 📸 截图确认      → adb_utils
  5. 🖼️ 保存模板      → 模板匹配 L4
  6. 📜 录制宏        → phone_macro
  7. ▶️ 回放宏        → phone_macro
  8. 📋 生成报告      → 汇总输出

用法:
  python3 demo.py                          # 完整演示
  python3 demo.py --quick                  # 快速演示 (跳过宏录制)
  python3 demo.py --app 微信               # 指定 App
"""

import sys, time, os
from adb_utils import adb_shell, screenshot, connect, log
from phone_controller import (
    parse_ui, show_ui_tree, smart_find, smart_find_scroll,
    wait_for_element, shot
)
from phone_monitor import get_battery, get_foreground_app, get_notifications, get_storage, get_wifi

# ─── 配置 ───
APP_NAME = sys.argv[sys.argv.index('--app') + 1] if '--app' in sys.argv else "设置"
QUICK_MODE = '--quick' in sys.argv

SEP = "═" * 50


def step(n, title):
    print(f"\n{SEP}")
    print(f" 步骤 {n}: {title}")
    print(SEP)


def main():
    print(f"""
{'╔' + '═'*48 + '╗'}
{'║':^50}
{'║':^4} 🎬 Rikkahub 全能演示 {'║':>22}
{'║':^4} 展示 v2.0 全部新能力 {'║':>22}
{'║':^50}
{'╚' + '═'*48 + '╝'}
""")
    print(f" 目标 App: {APP_NAME}")
    print(f" 模式: {'快速' if QUICK_MODE else '完整'}")
    print()

    # ────────────────────────────
    step(1, "📱 手机状态检查")
    # ────────────────────────────
    print("  正在获取手机状态...")

    bat = get_battery()
    print(f"  🔋 电池: {bat.get('level', '?')}% | 状态: {bat.get('status', '?')}")

    app = get_foreground_app()
    print(f"  📱 前台: {app}")

    storage = get_storage()
    if storage:
        print(f"  💾 存储: {storage.get('used', '?')}/{storage.get('total', '?')} ({storage.get('use%', '?')})")

    wifi = get_wifi()
    print(f"  📡 WiFi: {wifi}")

    # ────────────────────────────
    step(2, "👁️ 屏幕 UI 分析")
    # ────────────────────────────
    print(f"  正在解析屏幕 UI 树...")
    elements = parse_ui()
    print(f"  找到 {len(elements)} 个 UI 元素")

    # 显示前 5 个可交互元素
    clickable = [e for e in elements if e.get('clickable')]
    print(f"  其中 {len(clickable)} 个可点击")
    for el in clickable[:5]:
        label = el.get('text') or el.get('content_desc') or el.get('resource_id', '').split('/')[-1]
        cx, cy = el.get('center', (0, 0))
        if label:
            print(f"    🔘 {label:<25} @ ({cx},{cy})")

    # ────────────────────────────
    step(3, f"🔍 找 '{APP_NAME}' 并点击")
    # ────────────────────────────
    print(f"  正在查找 '{APP_NAME}'...")
    results = smart_find(APP_NAME)

    if results[0]:
        el = results[0][0]
        cx, cy = el['center']
        match_type = el.get('match_type', '?')
        print(f"  ✅ 找到! ({match_type}) @ ({cx}, {cy})")

        # 点击
        print(f"  👆 点击 ({cx}, {cy})...")
        adb_shell(f"input tap {cx} {cy}")
        time.sleep(2)
        print(f"  ✅ 点击完成")
    else:
        print(f"  ⚠️ 当前屏幕没找到 '{APP_NAME}'，试试滚动查找...")
        results = smart_find_scroll(APP_NAME)
        if results[0]:
            el = results[0][0]
            cx, cy = el['center']
            print(f"  ✅ 滚动后找到! @ ({cx}, {cy})")
            adb_shell(f"input tap {cx} {cy}")
            time.sleep(2)
        else:
            print(f"  ❌ 滚动后也没找到，跳过")

    # ────────────────────────────
    step(4, "📸 截图确认")
    # ────────────────────────────
    print(f"  截取当前屏幕...")
    img = shot()
    if img is not None:
        h, w = img.shape[:2]
        timestamp = int(time.time())
        path = f"/tmp/demo_screenshot_{timestamp}.png"
        import cv2
        cv2.imwrite(path, img)
        print(f"  ✅ 截图成功: {path}")
        print(f"  📐 分辨率: {w}x{h}")
    else:
        print(f"  ❌ 截图失败")

    # ────────────────────────────
    step(5, "🖼️ 模板匹配 (L4)")
    # ────────────────────────────
    if results[0]:
        # 把找到的区域保存为模板
        try:
            from phone_controller import save_template, match_template
            el = results[0][0]
            x1, y1, x2, y2 = el.get('bounds', (0, 0, 100, 100))
            name = f"demo_{APP_NAME}"

            print(f"  保存模板 '{name}'...")
            save_template(name, x1, y1, x2, y2)

            print(f"  用模板在屏幕上重新查找...")
            matches = match_template(name, threshold=0.5)
            if matches:
                print(f"  ✅ 模板匹配成功! 找到 {len(matches)} 个")
                for i, m in enumerate(matches[:3], 1):
                    cx, cy = m['center']
                    conf = m['confidence']
                    print(f"    [{i}] ({cx},{cy}) 置信度={conf:.0%}")
            else:
                print(f"  ⚠️ 模板匹配无结果 (阈值可能过高)")
        except Exception as e:
            print(f"  ⚠️ 模板匹配跳过: {e}")
    else:
        print(f"  ⚠️ 前面没找到目标，跳过模板匹配")

    # ────────────────────────────
    step(6, "🎬 宏录制 (演示)")
    # ────────────────────────────
    if not QUICK_MODE:
        print(f"  创建演示宏...")
        from phone_macro import save_macro, list_macros, play_macro

        demo_steps = [
            {"action": "wait_text", "params": {"text": APP_NAME, "timeout": 5}},
            {"action": "tap_text", "params": {"text": APP_NAME}},
            {"action": "wait", "params": {"seconds": 2}},
            {"action": "screenshot", "params": {"save": "/tmp/demo_macro_result.png"}},
        ]
        save_macro("demo_演示", demo_steps, "自动演示宏")
        print(f"  ✅ 演示宏已创建 (4 步)")

        print(f"\n  回放演示宏...")
        play_macro("demo_演示", step_timeout=10)
        print(f"  ✅ 宏回放完成")
    else:
        print(f"  快速模式: 跳过宏录制")

    # ────────────────────────────
    step(7, "🔔 通知检查")
    # ────────────────────────────
    notifs = get_notifications()
    if notifs:
        print(f"  当前有 {len(notifs)} 条通知:")
        for n in notifs[:5]:
            print(f"    🔔 {n.get('title','?')}: {n.get('text','')[:40]}")
    else:
        print(f"  📭 当前无通知")

    # ────────────────────────────
    step(8, "📋 演示完成")
    # ────────────────────────────
    print(f"""
  ✅ 全部 6 项能力演示完成!

  使用的能力:
    1. 📱 phone_monitor  — 手机状态
    2. 👁️ parse_ui()    — UI 树分析
    3. 🔍 smart_find()  — 智能查找 + 点击
    4. 📸 screenshot()  — 截图
    5. 🖼️ match_template — 模板匹配 (L4)
    6. 🎬 phone_macro    — 宏录制/回放

  效果: {len(clickable)} 个 UI 元素 / {len(results[0]) if results[0] else 0} 次匹配 /
        {'有' if img is not None else '无'} 截图
""")


if __name__ == '__main__':
    main()
