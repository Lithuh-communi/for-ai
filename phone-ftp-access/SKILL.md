---
name: phone-adb-access
description: Connect to the user's Android phone via ADB (Android Debug Bridge) over WiFi to access files, run shell commands, manage apps, and control the device. Also supports FTP as fallback. Trigger when the user says "连手机", "手机文件", "操作手机", "手机", "phone files", "adb", "安卓手机", "手机shell".
---

# 📱 手机 ADB 远程控制 Skill

通过 ADB over WiFi 连接用户的安卓手机，实现**文件操作 + 系统命令 + App 管理**等底层控制。

> ⚠️ **每次对话开始时，先询问用户当前的 ADB 连接信息**（IP 和端口可能变化）。

---

## 📡 第一步：建立连接

让用户提供以下信息：

1. 打开手机 **设置 → 开发者选项 → 无线调试** → **启用**
2. 点 **「使用配对码配对设备」**
3. 把显示的 **配对码 + IP:端口** 发给你

```bash
# 配对（只需做一次）
adb pair <IP>:<配对端口> <配对码>

# 连接（每次要用时）
adb connect <IP>:<服务端口>
```

验证连接：
```bash
adb devices -l
# 应显示: <IP>:<端口>  device  product:xxx model:xxx device:xxx
```

> 💡 如果 ADB 不可用，可回退到 FTP 方式（详见文末）。

---

## 🔧 第二步：常用操作

> ⚠️ ADB 连接在每次 shell 命令间会断开。**所有操作必须在同一个 shell 会话中完成**，方式有二：
> 1. 用 `adb shell "多个命令用分号隔开"` 方式批处理
> 2. 或用 Python 脚本包装多条命令

### 📂 文件操作

```bash
# 列出目录
adb shell "ls -la /sdcard/Download/"

# 读取文件内容
adb shell "cat /sdcard/Download/notes.txt"

# 从手机拉文件到工作区
adb pull /sdcard/Download/file.txt /workspace/

# 从工作区推文件到手机
adb push /workspace/file.txt /sdcard/Download/

# 删除文件
adb shell "rm /sdcard/Download/temp.txt"

# 创建目录
adb shell "mkdir -p /sdcard/1a_ai_workspace"

# 查看文件大小和存储
adb shell "df -h /sdcard/"
adb shell "du -sh /sdcard/DCIM/"
```

### 🖥 系统命令

```bash
# 设备信息
adb shell "getprop ro.product.manufacturer; getprop ro.product.model; getprop ro.build.version.release"

# 电池状态
adb shell "dumpsys battery | grep -E 'level|status|temperature|AC powered|USB powered'"

# 内存
adb shell "free -h"

# 运行进程
adb shell "ps -ef | head -20"

# 前台 App
adb shell "dumpsys window | grep mCurrentFocus"

# WiFi 信息
adb shell "dumpsys wifi | grep -i ssid | head -1"
```

### 📸 截屏录屏

```bash
# 截屏（保存到工作区）
adb exec-out screencap -p > /workspace/screenshot.png

# 录屏（30秒）
adb shell screenrecord /sdcard/record.mp4 --time-limit 30
adb pull /sdcard/record.mp4 /workspace/
```

### 📦 App 管理

```bash
# 列出所有第三方 App
adb shell "pm list packages -3"

# 安装 App
adb install /workspace/app.apk

# 卸载 App
adb shell "pm uninstall -k com.example.app"

# 查看 App 信息
adb shell "dumpsys package com.example.app | grep -E 'versionName|versionCode|firstInstallTime'"

# 强制停止 App
adb shell "am force-stop com.example.app"

# 启动 App
adb shell "monkey -p com.example.app 1"
```

### 🗄 访问 App 数据目录

```bash
# 注意：需要 root 或 App 可调试才能访问 /data/data/
# 但可以通过 backup 方式导出数据

# 查看 App 安装路径
adb shell "pm path com.example.app"
```

---

## 🐍 进阶：用 Python 批处理

由于 ADB 连接不能跨命令持久，复杂的操作建议用 Python 脚本包装：

```python
import subprocess, os, io

ADB = "adb connect 10.150.0.1:40745 && adb"

def run(cmd):
    """执行 adb shell 命令并返回输出"""
    full_cmd = f"{ADB} shell {cmd}"
    r = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout

def pull(remote, local):
    """从手机拉文件"""
    subprocess.run(f"{ADB} pull {remote} {local}", shell=True, timeout=60)

def push(local, remote):
    """推文件到手机"""
    subprocess.run(f"{ADB} push {local} {remote}", shell=True, timeout=60)

# 示例：列出 Download 下所有 apk
output = run("ls /sdcard/Download/ | grep apk")
apks = [f for f in output.split() if f.endswith('.apk')]
print(f"找到 {len(apks)} 个 APK")
```

---

## ⚠️ 注意事项

1. **IP 可能变化**: 每次使用前询问用户当前 ADB 地址
2. **连接超时**: 长时间不用会断开，重新 `adb connect` 即可
3. **配对仅一次**: 配对成功后，后续只需 `adb connect` 无需再配对
4. **无线调试需保持**: 手机无线调试开关要保持开启
5. **非 root**: 普通 ADB 无法访问 `/data/data/` 目录内容（但有 root 可以）
6. **文件路径**: `/sdcard/` 等于手机内部存储根目录

---

## 🔄 回退方案：FTP

如果 ADB 不可用，可回退到 FTP：

- **App**: Material Files → FTP 服务器 → 启动
- **连接**: `ftp://<IP>:2121/` 用户 `anonymous` 无密码
- **工具**: `lftp -u anonymous, -e "命令; quit" ftp://<IP>:2121/`
- **限制**: 只能文件操作，不能执行命令

---

## 📋 完整的连接流程模板

```
我: 请把手机「设置 → 开发者选项 → 无线调试」的页面截图发我，
    或者告诉我「IP 地址和端口」那一行显示的是什么？

用户: 10.150.0.1:40745

我: 好，我来连接。
    adb connect 10.150.0.1:40745
    → connected to 10.150.0.1:40745
    
    连上了！你想做什么？
```
