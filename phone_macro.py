#!/usr/bin/env python3
"""phone_macro.py v1.0 — 操作序列录制与回放"""

import json, os, sys, time
import cv2
from adb_utils import adb_shell, log, screenshot
from phone_controller import smart_find, wait_for_element

MACROS_DIR = "/workspace/macros"

def ensure_dir():
    os.makedirs(MACROS_DIR, exist_ok=True)

def list_macros():
    ensure_dir()
    files = [f for f in os.listdir(MACROS_DIR) if f.endswith('.json')]
    if not files:
        print("没有保存的宏")
        return
    for f in files:
        path = os.path.join(MACROS_DIR, f)
        with open(path) as fp:
            macro = json.load(fp)
        steps = len(macro.get('steps', []))
        print(f"  📋 {macro['name']:<20} ({steps} 步)  {f}")

def load_macro(name):
    path = os.path.join(MACROS_DIR, name + '.json')
    if not os.path.exists(path):
        print(f"❌ 宏 '{name}' 不存在")
        return None
    with open(path) as f:
        return json.load(f)

def save_macro(name, steps, description=""):
    ensure_dir()
    macro = {
        "name": name,
        "description": description,
        "version": 1,
        "steps": steps
    }
    path = os.path.join(MACROS_DIR, name + '.json')
    with open(path, 'w') as f:
        json.dump(macro, f, ensure_ascii=False, indent=2)
    print(f"✅ 宏 '{name}' 已保存 ({len(steps)} 步)")

def play_macro(name, step_timeout=15):
    macro = load_macro(name)
    if not macro:
        return

    print(f"▶️  回放宏: {macro['name']}")
    total = len(macro['steps'])
    success = 0

    for idx, step in enumerate(macro['steps'], 1):
        action = step.get('action', '')
        params = step.get('params', {})
        print(f"  [{idx}/{total}] {action} {params}")

        try:
            if action == 'tap_text':
                text = params['text']
                results = smart_find(text, force_ocr=params.get('ocr', False))
                if results[0]:
                    el = results[0][0]
                    cx, cy = el['center']
                    adb_shell(f"input tap {cx} {cy}")
                    success += 1
                else:
                    print(f"    ⚠️ 未找到 '{text}'")
                    if params.get('required', False):
                        print("    ❌ 必需步骤失败，停止回放")
                        break

            elif action == 'wait_text':
                text = params['text']
                timeout = params.get('timeout', step_timeout)
                r = wait_for_element(text, timeout)
                if r:
                    success += 1
                else:
                    print(f"    ⚠️ 等待 '{text}' 超时")

            elif action == 'tap':
                x, y = params['x'], params['y']
                adb_shell(f"input tap {x} {y}")
                success += 1

            elif action == 'swipe':
                x1, y1 = params['x1'], params['y1']
                x2, y2 = params['x2'], params['y2']
                d = params.get('duration', 300)
                adb_shell(f"input swipe {x1} {y1} {x2} {y2} {d}")
                success += 1

            elif action == 'screenshot':
                save_path = params.get('save', f"/tmp/macro_{name}_{idx}.png")
                img = screenshot()
                if img is not None:
                    cv2.imwrite(save_path, img)
                    print(f"    📸 截图: {save_path}")
                    success += 1

            elif action == 'open_app':
                package = params['package']
                adb_shell(f"monkey -p {package} 1")
                success += 1
                time.sleep(2)

            elif action == 'wait':
                time.sleep(params.get('seconds', 1))
                success += 1

            elif action == 'key':
                keycode = params.get('keycode', 4)
                adb_shell(f"input keyevent {keycode}")
                success += 1

            elif action == 'text':
                text = params['text']
                if any('一' <= c <= '鿿' for c in text):
                    escaped = text.replace("'", "\\'")
                    adb_shell(f"service call clipboard 4 i32 1 s16 '{escaped}' s16 'label'")
                else:
                    adb_shell(f"input text '{text}'")
                success += 1

            # 每步间隔
            time.sleep(params.get('interval', 1))

        except Exception as e:
            log("ERROR", "phone_macro", f"Step {idx} failed: {e}")
            print(f"    ❌ 错误: {e}")
            if params.get('required', False):
                break

    print(f"\n🏁 回放完成: {success}/{total} 步成功")

def record_macro(name):
    print(f"🎬 录制宏: {name}")
    print("操作指引：输入指令逐条添加，输入 'done' 完成，'list' 查看")
    print("可用指令：")
    print("  tap <文字>          — 点击文字")
    print("  wait <文字> <秒>    — 等待文字出现")
    print("  coord <x> <y>       — 点击坐标")
    print("  swipe <x1> <y1> <x2> <y2> — 滑动")
    print("  open <包名>         — 打开 App")
    print("  text <内容>         — 输入文字")
    print("  key <键码>          — 按键")
    print("  sleep <秒>          — 等待")
    print("  screenshot          — 截图")
    print("  done                — 完成")
    print("  cancel              — 取消")

    steps = []
    while True:
        cmd = input(f"[{len(steps)+1}] > ").strip()
        if cmd == 'done':
            break
        if cmd == 'cancel':
            print("已取消")
            return
        if cmd == 'list':
            for i, s in enumerate(steps, 1):
                print(f"  {i}. {s['action']} {s['params']}")
            continue

        parts = cmd.split()
        if not parts:
            continue

        action = parts[0]
        params = {}

        if action == 'tap':
            params = {'text': ' '.join(parts[1:])}
            steps.append({'action': 'tap_text', 'params': params})
            print(f"  ✅ 添加: 点击 '{params['text']}'")

        elif action == 'wait':
            params = {'text': parts[1], 'timeout': int(parts[2]) if len(parts) > 2 else 10}
            steps.append({'action': 'wait_text', 'params': params})
            print(f"  ✅ 添加: 等待 '{params['text']}' (超时 {params['timeout']}s)")

        elif action == 'coord':
            params = {'x': int(parts[1]), 'y': int(parts[2])}
            steps.append({'action': 'tap', 'params': params})

        elif action == 'swipe':
            params = {'x1': int(parts[1]), 'y1': int(parts[2]), 'x2': int(parts[3]), 'y2': int(parts[4])}
            steps.append({'action': 'swipe', 'params': params})

        elif action == 'open':
            params = {'package': parts[1]}
            steps.append({'action': 'open_app', 'params': params})

        elif action == 'text':
            params = {'text': ' '.join(parts[1:])}
            steps.append({'action': 'text', 'params': params})

        elif action == 'key':
            params = {'keycode': int(parts[1])}
            steps.append({'action': 'key', 'params': params})

        elif action == 'sleep':
            params = {'seconds': int(parts[1]) if len(parts) > 1 else 1}
            steps.append({'action': 'wait', 'params': params})

        elif action == 'screenshot':
            params = {'save': f'/tmp/macro_{name}_{len(steps)+1}.png'}
            steps.append({'action': 'screenshot', 'params': params})

    if steps:
        save_macro(name, steps)

def main():
    args = sys.argv[1:]
    if not args:
        print("用法:")
        print("  python3 phone_macro.py --record <名称>")
        print("  python3 phone_macro.py --play <名称>")
        print("  python3 phone_macro.py --list")
        print("  python3 phone_macro.py --edit <名称>")
        return

    if '--list' in args:
        list_macros()
    elif '--record' in args:
        idx = args.index('--record')
        name = args[idx + 1] if idx + 1 < len(args) else f"macro_{int(time.time())}"
        record_macro(name)
    elif '--play' in args:
        idx = args.index('--play')
        name = args[idx + 1] if idx + 1 < len(args) else ""
        if name:
            play_macro(name)
        else:
            print("请指定宏名称")
    elif '--edit' in args:
        idx = args.index('--edit')
        name = args[idx + 1]
        path = os.path.join(MACROS_DIR, name + '.json')
        if os.path.exists(path):
            print(f"📝 编辑宏文件: {path}")
            os.system(f"nano {path}")  # 或 vi
        else:
            print(f"❌ 宏 '{name}' 不存在")

if __name__ == '__main__':
    main()
