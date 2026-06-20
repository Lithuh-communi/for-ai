#!/usr/bin/env python3
"""phone_monitor.py v1.0 — 手机状态监控"""

import sys, time, json
from adb_utils import adb_shell, log


def get_battery():
    out = adb_shell("dumpsys battery | grep -E 'level|status|temperature|AC powered|USB powered'")
    info = {}
    for line in out.split('\n'):
        if ':' in line:
            k, v = line.strip().split(':', 1)
            info[k.strip()] = v.strip()
    return info


def get_foreground_app():
    out = adb_shell("dumpsys window | grep mCurrentFocus")
    if 'mCurrentFocus=' in out:
        return out.split('mCurrentFocus=')[-1].strip().strip('{}')
    return "unknown"


def get_notifications():
    out = adb_shell("dumpsys notification --naked | grep -E 'key=|tickerText=|android.title=' | head -30")
    notifications = []
    current = {}
    for line in out.split('\n'):
        if 'key=' in line:
            if current:
                notifications.append(current)
            current = {'key': line.split('key=')[-1].strip()}
        elif 'android.title=' in line:
            current['title'] = line.split('=')[-1].strip().strip("'")
        elif 'tickerText=' in line:
            current['text'] = line.split('=')[-1].strip().strip("'")
    if current:
        notifications.append(current)
    return notifications


def get_storage():
    out = adb_shell("df -h /sdcard/ | tail -1")
    parts = out.split()
    if len(parts) >= 5:
        return {"total": parts[1], "used": parts[2], "available": parts[3], "use%": parts[4]}
    return {}


def get_wifi():
    out = adb_shell("dumpsys wifi | grep -i ssid | head -1")
    if 'SSID' in out:
        return out.split('SSID:')[-1].strip().strip('"')
    return "unknown"


def show_info():
    print("📱 手机状态")
    print("=" * 40)
    bat = get_battery()
    print(f"🔋 电池: {bat.get('level', '?')} | 状态: {bat.get('status', '?')}")
    print(f"📱 前台: {get_foreground_app()}")
    storage = get_storage()
    print(f"💾 存储: {storage.get('used', '?')}/{storage.get('total', '?')} ({storage.get('use%', '?')})")
    print(f"📡 WiFi: {get_wifi()}")


def watch_mode(interval=5, on_sms=False):
    print(f"👁️  监控模式 (每 {interval}s 刷新)")
    print("=" * 40)
    last_notif_count = 0
    try:
        while True:
            ts = time.strftime("%H:%M:%S")
            bat = get_battery()
            foreground = get_foreground_app()
            notifs = get_notifications()

            # 新通知检测
            if len(notifs) > last_notif_count:
                new = notifs[last_notif_count:]
                for n in new:
                    print(f"\n🔔 [{ts}] 新通知: {n.get('title','')} - {n.get('text','')}")
                last_notif_count = len(notifs)

            sys.stdout.write(f"\r[{ts}] 🔋{bat.get('level','?')}% 📱{foreground[:30]:30s} 🔔{len(notifs)}")
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n监控已停止")


def main():
    args = sys.argv[1:]
    if '--watch' in args:
        interval = 5
        on_sms = '--on-sms' in args
        if '--interval' in args:
            idx = args.index('--interval')
            interval = int(args[idx + 1])
        watch_mode(interval, on_sms)
    elif '--notifications' in args:
        notifs = get_notifications()
        if notifs:
            print(f"📋 当前通知 ({len(notifs)} 条):")
            for n in notifs:
                print(f"  🔔 {n.get('title','?')}: {n.get('text','')}")
        else:
            print("📋 当前无通知")
    elif '--info' in args or not args:
        show_info()
    else:
        print("用法:")
        print("  python3 phone_monitor.py              查看状态")
        print("  python3 phone_monitor.py --info       查看状态")
        print("  python3 phone_monitor.py --notifications  查看通知")
        print("  python3 phone_monitor.py --watch --interval 5  持续监控")
        print("  python3 phone_monitor.py --watch --on-sms  监控短信")


if __name__ == '__main__':
    main()
