# 🪟 Windows 端设置指南

## 前置条件

- Windows 10/11
- 手机已开无线调试，沙箱能连 ADB

## 1. 装 Node.js

```powershell
winget install OpenJS.NodeJS
```
或去 https://nodejs.org 下载 LTS 版

装完打开新的终端验证：
```powershell
node --version
```

## 2. 获取 phone-api.js

从 GitHub 下载：
```powershell
curl -O https://raw.githubusercontent.com/Lithuh-communi/for-ai/main/phone-api.js
```

或者直接复制 `/skills/phone-api.js` 的内容到 Windows 上。

## 3. 连接

先确认沙箱 IP（手机上的工作区地址），然后：

```powershell
# 查看手机状态
node phone-api.js --server http://沙箱IP:58080 status

# 看屏幕 UI
node phone-api.js --server http://沙箱IP:58080 ui

# 点击文字
node phone-api.js --server http://沙箱IP:58080 tap:text "设置"

# 截图
node phone-api.js --server http://沙箱IP:58080 screenshot

# 返回键
node phone-api.js --server http://沙箱IP:58080 key back
```

## 4. 全部命令

| 命令 | 说明 |
|------|------|
| `status` | 手机状态（电量/存储/前台App） |
| `ui` | 屏幕 UI 元素树 |
| `tap:text "文字"` | 找文字点击 |
| `tap:text "文字" --scroll` | 翻页找文字点击 |
| `tap:text "文字" --wait 10` | 等待后点击 |
| `tap:xy x y` | 坐标点击 |
| `swipe x1 y1 x2 y2` | 滑动 |
| `type "文字"` | 输入文字 |
| `screenshot` | 截图保存 |
| `key back` | 返回键 |
| `key home` | Home 键 |
| `notif` | 查看通知 |
| `shell <cmd>` | 执行 ADB shell 命令 |
| `health` | 健康检查 |
