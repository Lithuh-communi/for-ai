#!/usr/bin/env python3
"""adb_utils v1.0 — 统一 ADB 连接与执行层"""

import subprocess, os, time, datetime
import numpy as np
import cv2

ADB_HOST = os.environ.get("ADB_HOST", "10.150.0.1:40745")
RETRY_COUNT = 3
RETRY_DELAY = 2
LOG_FILE = "/tmp/rikkahub.log"


def log(level, module, msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {module} | {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1


def is_connected():
    stdout, _, rc = _run("adb devices 2>/dev/null")
    for line in stdout.split("\n"):
        if "device" in line and "devices" not in line and "offline" not in line:
            return True
    return False


def connect(host=None):
    host = host or ADB_HOST
    if is_connected():
        return True
    log("INFO", "adb_utils", f"Connecting to {host}...")
    stdout, stderr, rc = _run(f"adb connect {host} 2>/dev/null")
    success = "connected" in stdout.lower() or "already" in stdout.lower()
    if success:
        log("INFO", "adb_utils", f"Connected to {host}")
    else:
        log("ERROR", "adb_utils", f"Failed to connect: {stdout.strip()}")
    return success


def adb_shell(cmd, retry=RETRY_COUNT):
    for attempt in range(retry):
        connect()
        stdout, stderr, rc = _run(f"adb shell {cmd}")
        if rc == 0:
            return stdout.strip()
        log("WARN", "adb_utils", f"shell cmd failed (attempt {attempt+1}): {cmd[:60]}")
        time.sleep(RETRY_DELAY)
    log("ERROR", "adb_utils", f"shell cmd exhausted retries: {cmd[:60]}")
    return ""


def adb(cmd, retry=RETRY_COUNT):
    for attempt in range(retry):
        connect()
        stdout, stderr, rc = _run(f"adb {cmd}")
        if rc == 0:
            return stdout.strip()
        log("WARN", "adb_utils", f"adb cmd failed (attempt {attempt+1}): {cmd[:60]}")
        time.sleep(RETRY_DELAY)
    log("ERROR", "adb_utils", f"adb cmd exhausted retries: {cmd[:60]}")
    return ""


def pull(remote, local):
    log("INFO", "adb_utils", f"pull {remote} -> {local}")
    out = adb(f"pull \"{remote}\" \"{local}\"")
    return "error" not in out.lower()


def push(local, remote):
    log("INFO", "adb_utils", f"push {local} -> {remote}")
    out = adb(f"push \"{local}\" \"{remote}\"")
    return "error" not in out.lower()


def screenshot():
    pid = os.getpid()
    path = f"/tmp/_adb_screen_{pid}.png"
    _run(f"adb exec-out screencap -p > {path}")
    if not os.path.exists(path):
        log("ERROR", "adb_utils", "screenshot failed: no file produced")
        return None
    img = cv2.imread(path)
    try:
        os.remove(path)
    except:
        pass
    return img
