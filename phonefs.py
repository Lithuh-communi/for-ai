#!/usr/bin/env python3
"""Rikkahub 手机文件管理器 - 通过FTP操作手机文件"""

import os
import sys
import json
import html
import urllib.parse
import io
import time
from ftplib import FTP, error_perm
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

FTP_HOST = '10.166.72.151'
FTP_PORT = 2121

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.html')

def get_ftp(max_retries=2):
    last_error = None
    for attempt in range(max_retries):
        try:
            ftp = FTP()
            ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
            ftp.login('anonymous', '')
            return ftp
        except Exception as e:
            last_error = e
            try:
                ftp.close()
            except:
                pass
            time.sleep(1)
    raise last_error

def ftp_list(path):
    ftp = get_ftp()
    try:
        ftp.cwd(path)
        items = []
        ftp.retrlines('LIST', items.append)
        parsed = []
        for line in items:
            parts = line.split()
            if len(parts) < 9:
                continue
            perms = parts[0]
            name = ' '.join(parts[8:])
            is_dir = perms.startswith('d')
            try:
                size = int(parts[4])
            except:
                size = 0
            try:
                months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
                         'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
                month = months.get(parts[5], '01')
                day = parts[6].zfill(2)
                t = parts[7]
                if ':' in t:
                    mtime = month + '-' + day + ' ' + t
                else:
                    mtime = t + '-' + month + '-' + day
            except:
                mtime = ''
            parsed.append({
                'name': name,
                'is_dir': is_dir,
                'size': size,
                'mtime': mtime,
                'perms': perms
            })
        return parsed
    except Exception as e:
        return {'error': str(e)}
    finally:
        ftp.quit()

def fmt_size(size):
    if size < 1024:
        return str(size) + ' B'
    elif size < 1024*1024:
        return '{:.1f} KB'.format(size/1024)
    else:
        return '{:.1f} MB'.format(size/1024/1024)

def esc(s):
    return html.escape(s)

def urlq(s):
    return urllib.parse.quote(s)

class PhoneFSHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/' or path == '/browse':
            dir_path = query.get('dir', ['/'])[0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self._render_page(dir_path)
            return

        if path == '/api/list':
            dir_path = query.get('dir', ['/'])[0]
            result = ftp_list(dir_path)
            if isinstance(result, dict):
                self._send_json(200, result)
            else:
                self._send_json(200, {'items': result})
            return

        if path == '/api/download':
            file_path = query.get('file', [''])[0]
            if not file_path:
                self._send_json(400, {'error': 'Missing file param'})
                return
            self._download_file(file_path)
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/upload':
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self._send_json(400, {'error': '需要 multipart/form-data'})
                return

            import cgi
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type}
            )

            target_dir = form.getvalue('dir', '/')
            uploaded = []

            ftp = get_ftp()
            try:
                ftp.cwd(target_dir)
                for field in form.keys():
                    if field == 'dir':
                        continue
                    item = form[field]
                    if item.filename:
                        filename = os.path.basename(item.filename)
                        data = item.file.read()
                        ftp.storbinary('STOR ' + filename, io.BytesIO(data))
                        uploaded.append(filename)
                self._send_json(200, {'success': True, 'files': uploaded})
            except Exception as e:
                self._send_json(500, {'error': str(e)})
            finally:
                ftp.quit()
            return

        if path == '/api/delete':
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                file_path = body.get('file', '')
                is_dir = body.get('is_dir', False)
            except:
                self._send_json(400, {'error': 'Invalid JSON'})
                return

            ftp = get_ftp()
            try:
                if is_dir:
                    ftp.rmd(file_path)
                else:
                    ftp.delete(file_path)
                self._send_json(200, {'success': True})
            except Exception as e:
                self._send_json(500, {'error': str(e)})
            finally:
                ftp.quit()
            return

        if path == '/api/mkdir':
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                dir_path = body.get('dir', '')
            except:
                self._send_json(400, {'error': 'Invalid JSON'})
                return

            ftp = get_ftp()
            try:
                ftp.mkd(dir_path)
                self._send_json(200, {'success': True})
            except Exception as e:
                self._send_json(500, {'error': str(e)})
            finally:
                ftp.quit()
            return

        self._send_json(404, {'error': 'Unknown action'})

    def _download_file(self, file_path):
        ftp = get_ftp()
        try:
            buf = io.BytesIO()
            ftp.retrbinary('RETR ' + file_path, buf.write)
            buf.seek(0)
            filename = os.path.basename(file_path)
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
            self.send_header('Content-Length', str(buf.getbuffer().nbytes))
            self.end_headers()
            self.wfile.write(buf.getvalue())
        except Exception as e:
            self._send_json(500, {'error': str(e)})
        finally:
            ftp.quit()

    def _send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _render_page(self, dir_path):
        items = ftp_list(dir_path)
        if isinstance(items, dict) and 'error' in items:
            self.wfile.write('<html><body><h3>Error: ' + esc(items['error']) + '</h3></body></html>'.encode())
            return

        # 面包屑
        parts = dir_path.strip('/').split('/') if dir_path.strip('/') else []
        breadcrumb = '<a href="/" style="color:#0a84ff;text-decoration:none;">📱 手机</a>'
        accum = ''
        for p in parts:
            accum += '/' + p
            breadcrumb += ' <span style="color:#666;">/</span> '
            breadcrumb += '<a href="/?dir=' + urlq(accum) + '" style="color:#0a84ff;text-decoration:none;">' + esc(p) + '</a>'

        # 文件列表
        file_html = ''
        if dir_path != '/':
            parent = '/'.join(dir_path.strip('/').split('/')[:-1]) or '/'
            file_html += '<a href="/?dir=' + urlq(parent) + '" class="item" style="color:#0a84ff;">'
            file_html += '<span class="icon">📂</span><span class="name">.. (返回上级)</span><span class="meta"></span></a>'

        for item in items:
            icon = '📁' if item['is_dir'] else '📄'
            name = esc(item['name'])
            sz = fmt_size(item['size']) if not item['is_dir'] else '—'
            mt = esc(item.get('mtime', ''))
            full_path = (dir_path.rstrip('/') + '/' + item['name']).replace('//', '/')

            if item['is_dir']:
                href = '/?dir=' + urlq(full_path)
                del_btn = ''
            else:
                href = '#dl'
                del_btn = '<button class="del" onclick="deleteFile(\'' + urlq(full_path) + '\',false);event.stopPropagation();">✕</button>'

            file_html += '<a href="' + href + '" class="item"'
            if not item['is_dir']:
                file_html += ' onclick="downloadFile(\'' + urlq(full_path) + '\');return false;"'
            file_html += '>'
            file_html += '<span class="icon">' + icon + '</span>'
            file_html += '<span class="name">' + name + '</span>'
            file_html += '<span class="meta"><span class="size">' + sz + '</span> <span class="time">' + mt + '</span></span>'
            file_html += del_btn
            file_html += '</a>'

        if not file_html:
            file_html = '<div class="empty">📪 此文件夹为空</div>'

        # 读取模板并替换
        try:
            with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                template = f.read()
        except:
            template = '<html><body><h3>Template not found</h3></body></html>'
            self.wfile.write(template.encode())
            return

        template = template.replace('__BREADCRUMB__', breadcrumb)
        template = template.replace('__FILE_LIST__', file_html)
        template = template.replace('__CURRENT_DIR__', esc(dir_path))

        self.wfile.write(template.encode())

    def log_message(self, format, *args):
        print('[PhoneFS] ' + args[0] + ' ' + args[1] + ' ' + args[2])

def find_files(ftp, path, pattern, max_results=50):
    """递归搜索文件"""
    results = []
    try:
        items = []
        ftp.cwd(path)
        ftp.retrlines('LIST', items.append)
        for line in items:
            parts = line.split()
            if len(parts) < 9:
                continue
            name = ' '.join(parts[8:])
            full_path = (path.rstrip('/') + '/' + name).replace('//', '/')
            is_dir = parts[0].startswith('d')
            if pattern.lower() in name.lower():
                results.append(full_path)
            if is_dir and len(results) < max_results:
                results.extend(find_files(ftp, full_path, pattern, max_results - len(results)))
    except Exception:
        pass
    return results[:max_results]

if __name__ == '__main__':
    if '--find' in sys.argv:
        idx = sys.argv.index('--find')
        pattern = sys.argv[idx + 1]
        ftp = get_ftp()
        results = find_files(ftp, '/', pattern)
        for r in results:
            print(r)
        ftp.quit()
        sys.exit(0)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    print('╔══════════════════════════════════╗')
    print('║  📱 手机文件管理器已启动          ║')
    print('║                                  ║')
    print('║  浏览器访问:                      ║')
    print('║  http://localhost:' + str(port) + '                 ║')
    print('║                                  ║')
    print('║  通过 FTP 连接手机进行操作        ║')
    print('║  按 Ctrl+C 停止                  ║')
    print('╚══════════════════════════════════╝')
    server = HTTPServer(('0.0.0.0', port), PhoneFSHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
        server.server_close()
