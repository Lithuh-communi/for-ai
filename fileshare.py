#!/usr/bin/env python3
"""简单的局域网文件共享服务器 - 在手机浏览器中访问你的工作区文件"""

import os
import sys
import html
import json
import urllib.parse
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
SHARE_DIR = sys.argv[2] if len(sys.argv) > 2 else '/workspace'

class ShareHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SHARE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Web界面 - 美化文件列表
        if path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self._render_index()
            return

        # 文件下载 - 使用父类逻辑
        super().do_GET()

    def do_POST(self):
        """处理文件上传"""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/upload':
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self._send_json(400, {'error': '需要 multipart/form-data'})
                return

            import cgi
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )

            target_dir = form.getvalue('dir', '')
            safe_dir = os.path.normpath(os.path.join(SHARE_DIR, target_dir))
            if not safe_dir.startswith(os.path.normpath(SHARE_DIR)):
                self._send_json(403, {'error': '禁止访问'})
                return

            os.makedirs(safe_dir, exist_ok=True)

            uploaded = []
            for field in form.keys():
                if field == 'dir':
                    continue
                item = form[field]
                if item.filename:
                    filepath = os.path.join(safe_dir, os.path.basename(item.filename))
                    with open(filepath, 'wb') as f:
                        f.write(item.file.read())
                    uploaded.append(item.filename)

            self._send_json(200, {'success': True, 'files': uploaded, 'dir': target_dir})
        else:
            self._send_json(404, {'error': 'Not Found'})

    def do_DELETE(self):
        """处理文件删除"""
        parsed = urllib.parse.urlparse(self.path)
        filepath = os.path.normpath(os.path.join(SHARE_DIR, parsed.path.lstrip('/')))

        if not filepath.startswith(os.path.normpath(SHARE_DIR)):
            self._send_json(403, {'error': '禁止访问'})
            return

        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)
            self._send_json(200, {'success': True})
        else:
            self._send_json(404, {'error': '文件不存在'})

    def _send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _render_index(self):
        """渲染漂亮的Web文件管理器界面"""
        # 获取当前目录
        cur_dir = urllib.parse.urlparse(self.path).path.lstrip('/')
        abs_dir = os.path.normpath(os.path.join(SHARE_DIR, cur_dir))

        if not abs_dir.startswith(os.path.normpath(SHARE_DIR)):
            self._render_error('禁止访问')
            return

        # 列出文件
        items = []
        try:
            for name in sorted(os.listdir(abs_dir)):
                full = os.path.join(abs_dir, name)
                is_dir = os.path.isdir(full)
                size = os.path.getsize(full) if not is_dir else 0
                mtime = os.path.getmtime(full)
                items.append({
                    'name': name,
                    'is_dir': is_dir,
                    'size': size,
                    'mtime': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                })
        except PermissionError:
            self._render_error('无权限访问此目录')
            return

        rel_path = cur_dir

        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>📁 Rikkahub 工作区</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f7;
    color: #1d1d1f;
    padding: 16px;
    min-height: 100vh;
}}
.container {{ max-width: 800px; margin: 0 auto; }}
.header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 0; border-bottom: 1px solid #e0e0e0; margin-bottom: 16px;
    flex-wrap: wrap; gap: 8px;
}}
.header h1 {{ font-size: 20px; font-weight: 600; }}
.header .info {{ font-size: 13px; color: #86868b; }}
.breadcrumb {{
    font-size: 14px; padding: 8px 0 12px; color: #86868b;
    overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch;
}}
.breadcrumb a {{ color: #0071e3; text-decoration: none; }}
.breadcrumb a:hover {{ text-decoration: underline; }}
.file-list {{ list-style: none; }}
.file-item {{
    display: flex; align-items: center; padding: 12px 16px;
    background: white; border-radius: 12px; margin-bottom: 6px;
    transition: all 0.2s; cursor: pointer;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.file-item:hover {{ background: #f0f0f2; }}
.file-item:active {{ transform: scale(0.98); }}
.file-icon {{ font-size: 20px; margin-right: 12px; flex-shrink: 0; }}
.file-name {{ flex: 1; font-size: 15px; overflow: hidden; text-overflow: ellipsis; }}
.file-meta {{ font-size: 12px; color: #86868b; text-align: right; flex-shrink: 0; margin-left: 12px; }}
.file-size {{ margin-right: 8px; }}
.delete-btn {{
    background: none; border: none; color: #ff3b30; font-size: 16px;
    cursor: pointer; padding: 4px 8px; border-radius: 6px; opacity: 0;
    transition: opacity 0.2s;
}}
.file-item:hover .delete-btn {{ opacity: 1; }}
.upload-area {{
    border: 2px dashed #c7c7cc; border-radius: 12px; padding: 24px;
    text-align: center; margin-top: 16px; color: #86868b;
    transition: all 0.2s; cursor: pointer;
}}
.upload-area:hover, .upload-area.dragover {{
    border-color: #0071e3; background: #e8f0fe; color: #0071e3;
}}
.upload-area input[type="file"] {{ display: none; }}
.upload-btn {{
    display: inline-block; background: #0071e3; color: white;
    padding: 8px 20px; border-radius: 20px; font-size: 14px;
    border: none; cursor: pointer; margin-top: 8px;
}}
.empty {{ text-align: center; padding: 40px 0; color: #86868b; font-size: 14px; }}
@media (prefers-color-scheme: dark) {{
    body {{ background: #1c1c1e; color: #f5f5f7; }}
    .file-item {{ background: #2c2c2e; }}
    .file-item:hover {{ background: #3a3a3c; }}
    .header {{ border-color: #3a3a3c; }}
    .upload-area {{ border-color: #3a3a3c; }}
    .upload-area:hover {{ border-color: #0a84ff; background: #1a2638; }}
}}
</style>
</head>
<body>
<div class="container">
<div class="header">
    <h1>📁 Rikkahub 工作区</h1>
    <div class="info" id="ipDisplay">获取IP中…</div>
</div>
<div class="breadcrumb">
    <a href="/">📂 根目录</a>
    {''.join(f' / <a href="/{"/".join(parts)}">{p}</a>' for parts in [rel_path.split('/')[:i+1] for i in range(len(rel_path.split('/')))] if parts != [''])}
</div>

<ul class="file-list" id="fileList">
'''
        if not items:
            html_content += '<li class="empty">📪 此文件夹为空</li>'
        else:
            for item in items:
                icon = '📁' if item['is_dir'] else '📄'
                href = f'/{rel_path}/{item["name"]}' if rel_path else f'/{item["name"]}'
                href_enc = urllib.parse.quote(href)
                size_str = f'{item["size"]/1024:.1f} KB' if item['size'] < 1024*1024 else f'{item["size"]/1024/1024:.1f} MB'
                if item['is_dir']:
                    href_enc += '/'
                    size_str = '—'

                delete_btn = ''
                if not item['is_dir']:
                    delete_btn = f'<button class="delete-btn" onclick="deleteFile(\'{urllib.parse.quote(item["name"])}\')">✕</button>'

                html_content += f'''
    <li class="file-item" onclick="{'window.location.href=\'' + href_enc + '\'' if not item['is_dir'] else 'window.location.href=\'' + href_enc + '\''}">
        <span class="file-icon">{icon}</span>
        <span class="file-name">{html.escape(item['name'])}</span>
        <span class="file-meta">
            <span class="file-size">{size_str}</span>
            <span class="file-time">{item['mtime']}</span>
        </span>
        {delete_btn}
    </li>'''

        html_content += '''
</ul>

<div class="upload-area" id="uploadArea">
    <div>📤 点击或拖拽文件到此上传</div>
    <input type="file" id="fileInput" multiple>
    <div style="font-size:12px;margin-top:4px;" id="uploadStatus"></div>
</div>

<div style="text-align:center; padding: 20px 0 40px; color: #86868b; font-size: 12px;">
    Rikkahub File Share · 手机浏览器访问
</div>
</div>

<script>
// 获取本机IP
fetch('/api/ip')
    .then(r => r.json())
    .then(d => { document.getElementById('ipDisplay').textContent = '📡 ' + d.ip + ':' + d.port; })
    .catch(() => { document.getElementById('ipDisplay').textContent = '📡 连接到服务器'; });

// 文件上传
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const currentDir = '''' + html.escape(rel_path) + '''';

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
uploadArea.addEventListener('drop', (e) => { e.preventDefault(); uploadArea.classList.remove('dragover'); uploadFiles(e.dataTransfer.files); });
fileInput.addEventListener('change', () => { uploadFiles(fileInput.files); fileInput.value = ''; });

function uploadFiles(files) {
    if (files.length === 0) return;
    const formData = new FormData();
    formData.append('dir', currentDir);
    for (const f of files) formData.append('file', f);
    uploadStatus.textContent = '⏳ 上传中 (' + files.length + ' 个文件)...';
    fetch('/upload', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                uploadStatus.textContent = '✅ 上传成功！' + d.files.join(', ');
                setTimeout(() => location.reload(), 1000);
            } else {
                uploadStatus.textContent = '❌ 上传失败: ' + (d.error || '未知错误');
            }
        })
        .catch(e => { uploadStatus.textContent = '❌ 上传出错: ' + e.message; });
}

function deleteFile(name) {
    if (!confirm('确定删除 ' + name + ' 吗？')) return;
    const path = currentDir ? '/' + encodeURIComponent(currentDir) + '/' + encodeURIComponent(name) : '/' + encodeURIComponent(name);
    fetch(path, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => { if (d.success) location.reload(); else alert('删除失败'); })
        .catch(e => alert('删除失败: ' + e.message));
}
</script>
</body>
</html>'''
        self.wfile.write(html_content.encode())

    def _render_error(self, msg):
        self.wfile.write(f'<html><body><h3>{msg}</h3></body></html>'.encode())

    def log_message(self, format, *args):
        print(f"[FileShare] {args[0]} {args[1]} {args[2]}")

# 获取本机局域网IP
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '无法获取IP'

if __name__ == '__main__':
    # 添加IP查询API
    original_do_GET = ShareHandler.do_GET
    def do_GET_with_api(self):
        if self.path == '/api/ip':
            self._send_json(200, {'ip': get_local_ip(), 'port': PORT})
            return
        original_do_GET(self)
    ShareHandler.do_GET = do_GET_with_api

    local_ip = get_local_ip()
    print(f'╔══════════════════════════════════╗')
    print(f'║  📁 Rikkahub 文件共享已启动       ║')
    print(f'║                                  ║')
    print(f'║  手机浏览器访问:                  ║')
    print(f'║  http://{local_ip}:{PORT}              ║')
    print(f'║                                  ║')
    print(f'║  共享目录: {SHARE_DIR}       ║')
    print(f'║  按 Ctrl+C 停止服务              ║')
    print(f'╚══════════════════════════════════╝')

    server = HTTPServer(('0.0.0.0', PORT), ShareHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[FileShare] 服务已停止')
        server.server_close()
