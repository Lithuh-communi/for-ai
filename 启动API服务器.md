# 🌉 启动 HTTP API Bridge

拉取最新代码后在沙箱里运行：

```bash
cd /skills

# 1. 拉最新代码
git pull origin master

# 2. 启动 API 服务器
python3 /workspace/api_server.py

# 应该看到:
# 🌉 Rikkahub HTTP API Bridge
# 地址: http://0.0.0.0:58080
# ADB: 10.150.0.1:40745
```

启动后，Windows 端的 `phone-api.js` 就能直接调用了：

```bash
# 查看手机状态
node phone-api.js status

# 看屏幕
node phone-api.js ui

# 点击"微信"
node phone-api.js tap:text "微信" --wait 10

# 截图
node phone-api.js screenshot
```

连接架构：
```
Windows (Claude Code)              手机 + 沙箱
  phone-api.js ──HTTP:58080──→ api_server.py
                                     ├─ ADB → phone
                                     ├─ OCR / UI tree
                                     ├─ macro play
                                     └─ screenshot
```
