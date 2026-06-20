#!/usr/bin/env python3
"""
🌉 Rikkahub HTTP API Bridge v1.0
将手机控制能力暴露为 REST API，供远程客户端（如 Windows Claude Code）调用。

启动:
  python3 api_server.py [--port 58080] [--host 0.0.0.0]

环境变量:
  ADB_HOST - 手机 ADB 地址（默认 10.150.0.1:40745）
  API_PORT - 端口（默认 58080）
"""

import sys, os, json, base64, time, io

# ─── 配置 ───
HOST = sys.argv[sys.argv.index('--host') + 1] if '--host' in sys.argv else os.environ.get("API_HOST", "0.0.0.0")
PORT = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else int(os.environ.get("API_PORT", 58080))

# 导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from adb_utils import adb_shell, screenshot, connect, log
from phone_controller import (
    parse_ui, smart_find, smart_find_scroll, wait_for_element,
    shot, match_template, save_template
)
from phone_monitor import get_battery, get_foreground_app, get_notifications, get_storage, get_wifi

# ─── HTTP 服务器（纯标准库，零依赖）───
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class APIHandler(BaseHTTPRequestHandler):
    """REST API 处理器"""

    def _send(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self):
        self._send({"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)

        try:
            # GET /status — 手机状态
            if path == "/status":
                self._send({
                    "battery": get_battery(),
                    "foreground": get_foreground_app(),
                    "storage": get_storage(),
                    "wifi": get_wifi(),
                    "adb_host": os.environ.get("ADB_HOST", ""),
                })

            # GET /ui — UI 树
            elif path == "/ui":
                elements = parse_ui()
                clickable = [e for e in elements if e.get("clickable")]
                self._send({
                    "total": len(elements),
                    "clickable": len(clickable),
                    "elements": [
                        {
                            "text": e.get("text", ""),
                            "resource_id": e.get("resource_id", ""),
                            "center": e.get("center"),
                            "bounds": e.get("bounds"),
                            "clickable": e.get("clickable"),
                        }
                        for e in clickable[:20]
                    ],
                })

            # GET /screenshot — 截图（base64）
            elif path == "/screenshot":
                img = shot()
                if img is None:
                    self._send({"error": "截图失败"}, 500)
                    return
                import cv2
                _, buf = cv2.imencode(".png", img)
                b64 = base64.b64encode(buf).decode("utf-8")
                self._send({"image": b64, "size": f"{img.shape[1]}x{img.shape[0]}"})

            # GET /notifications — 通知
            elif path == "/notifications":
                notifs = get_notifications()
                self._send({"count": len(notifs), "notifications": notifs[:10]})

            # GET /health — 健康检查
            elif path == "/health":
                adb_ok = connect()
                self._send({
                    "status": "ok" if adb_ok else "adb_disconnected",
                    "adb": adb_ok,
                })

            else:
                self._send({"error": "not found", "paths": ["/status", "/ui", "/screenshot", "/notifications", "/health"]}, 404)

        except Exception as e:
            log("ERROR", "api", str(e))
            self._send({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            body = self._read_body()

            # POST /tap/text — 按文字点击
            if path == "/tap/text":
                text = body.get("text", "")
                if not text:
                    self._send({"error": "text required"}, 400)
                    return
                scroll = body.get("scroll", False)
                wait = body.get("wait", 0)

                if wait > 0:
                    results = wait_for_element(text, wait)
                elif scroll:
                    results, strategy, latency, scrolls = smart_find_scroll(text)
                else:
                    results, strategy, latency = smart_find(text)

                if results:
                    el = results[0]
                    cx, cy = el["center"]
                    adb_shell(f"input tap {cx} {cy}")
                    self._send({
                        "success": True,
                        "match_type": el.get("match_type", "?"),
                        "x": cx, "y": cy,
                        "text": el.get("text", ""),
                    })
                else:
                    self._send({"success": False, "error": f"未找到 '{text}'"})

            # POST /tap/xy — 坐标点击
            elif path == "/tap/xy":
                x, y = body.get("x", 0), body.get("y", 0)
                adb_shell(f"input tap {x} {y}")
                self._send({"success": True, "x": x, "y": y})

            # POST /swipe — 滑动
            elif path == "/swipe":
                x1, y1 = body.get("x1", 0), body.get("y1", 0)
                x2, y2 = body.get("x2", 0), body.get("y2", 0)
                duration = body.get("duration", 300)
                adb_shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")
                self._send({"success": True})

            # POST /type — 输入文字
            elif path == "/type":
                text = body.get("text", "")
                if any("一" <= c <= "鿿" for c in text):
                    escaped = text.replace("'", "\\'")
                    adb_shell(f"service call clipboard 4 i32 1 s16 '{escaped}' s16 'label'")
                else:
                    adb_shell(f"input text '{text}'")
                self._send({"success": True, "text": text})

            # POST /key — 按键
            elif path == "/key":
                keycode = body.get("keycode", 4)
                adb_shell(f"input keyevent {keycode}")
                names = {4: "back", 3: "home", 66: "enter", 26: "power"}
                self._send({"success": True, "key": names.get(keycode, str(keycode))})

            # POST /macro/play — 回放宏
            elif path == "/macro/play":
                name = body.get("name", "")
                if not name:
                    self._send({"error": "name required"}, 400)
                    return
                from phone_macro import play_macro
                play_macro(name, step_timeout=body.get("timeout", 15))
                self._send({"success": True, "macro": name})

            # POST /shell — 执行 ADB shell 命令
            elif path == "/shell":
                cmd = body.get("cmd", "")
                if not cmd:
                    self._send({"error": "cmd required"}, 400)
                    return
                output = adb_shell(cmd)
                self._send({"success": True, "output": output[:2000]})

            else:
                self._send({"error": "not found"}, 404)

        except json.JSONDecodeError:
            self._send({"error": "invalid json"}, 400)
        except Exception as e:
            log("ERROR", "api", str(e))
            self._send({"error": str(e)}, 500)

    def log_message(self, format, *args):
        log("INFO", "api", f"{args[0]} {args[1]} {args[2]}")


def main():
    # 确保 ADB 连通
    connect()

    server = HTTPServer((HOST, PORT), APIHandler)
    print(f"""
╔══════════════════════════════════════════╗
║  🌉 Rikkahub HTTP API Bridge            ║
║                                          ║
║  地址: http://{HOST}:{PORT}                 ║
║                                          ║
║  端点:                                    ║
║    GET  /health        健康检查          ║
║    GET  /status        手机状态          ║
║    GET  /ui            UI 元素树         ║
║    GET  /screenshot    截图             ║
║    GET  /notifications 通知列表          ║
║    POST /tap/text      按文字点击        ║
║    POST /tap/xy        坐标点击          ║
║    POST /swipe         滑动屏幕          ║
║    POST /type          输入文字          ║
║    POST /key           按键             ║
║    POST /macro/play    回放宏           ║
║    POST /shell         ADB shell        ║
║                                          ║
║  ADB: {os.environ.get('ADB_HOST', '未设置'):<32} ║
╚══════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()
