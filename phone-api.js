#!/usr/bin/env node
/**
 * 📱 Rikkahub Phone API Client — Windows 端远程手机控制
 *
 * 通过 HTTP 调用沙箱上的 api_server.py，实时操控手机。
 *
 * 用法:
 *   node phone-api.js status                   查看手机状态
 *   node phone-api.js ui                       查看屏幕 UI
 *   node phone-api.js tap:text "发送"           按文字点击
 *   node phone-api.js tap:xy 500 1000           坐标点击
 *   node phone-api.js swipe 500 2000 500 500    滑动
 *   node phone-api.js type "你好"               输入文字
 *   node phone-api.js screenshot                截图（保存到本地）
 *   node phone-api.js key back                  按返回键
 *   node phone-api.js key home                  按 Home 键
 *   node phone-api.js health                    健康检查
 *   node phone-api.js notif                     查看通知
 *   node phone-api.js shell <cmd>               执行 ADB shell 命令
 *
 * 环境变量:
 *   PHONE_API=http://沙箱IP:58080  （默认 http://10.150.0.1:58080）
 *
 * 中继模式（沙箱网络不通时走 GitHub）:
 *   node phone-api.js --relay status           通过 GitHub 中继
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const API_HOST = process.env.PHONE_API || 'http://10.150.0.1:58080';
const RELAY_REPO = 'Lithuh-communi/for-ai';
const RELAY_TOKEN = process.env.GH_TOKEN || process.env.GITHUB_TOKEN;

// ─── HTTP 调用 ───

function apiGet(endpoint) {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint, API_HOST);
    http.get(url.href, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        if (res.statusCode >= 400) {
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        } else {
          resolve(JSON.parse(data));
        }
      });
    }).on('error', reject);
  });
}

function apiPost(endpoint, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint, API_HOST);
    const payload = JSON.stringify(body);
    const req = http.request(url.href, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
      },
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        if (res.statusCode >= 400) {
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        } else {
          resolve(JSON.parse(data));
        }
      });
    });
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

// ─── GitHub 中继模式 ───

function ghApi(path) {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: 'api.github.com',
      path: `/repos/${RELAY_REPO}/${path}`,
      headers: {
        'Authorization': `token ${RELAY_TOKEN}`,
        'User-Agent': 'phone-api-client',
        'Accept': 'application/vnd.github.v3+json',
      },
    };
    https.get(opts, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        if (res.statusCode >= 400) {
          reject(new Error(`GitHub HTTP ${res.statusCode}: ${data}`));
        } else {
          resolve(JSON.parse(data));
        }
      });
    }).on('error', reject);
  });
}

async function relayStatus() {
  // 通过 GitHub 读 sandbox 写入的状态文件
  try {
    const result = await ghApi('contents/phone_status.json');
    const content = Buffer.from(result.content.replace(/\n/g, ''), 'base64').toString();
    return JSON.parse(content);
  } catch (e) {
    throw new Error(`中继模式不可用: ${e.message}\n沙箱 AI 需先运行: echo '{"battery":...}' > /workspace/phone_status.json && git add && git commit && git push`);
  }
}

// ─── 命令处理 ───

function showStatus(data) {
  console.log('📱 手机状态');
  console.log('═'.repeat(30));
  if (data.battery) {
    console.log(`  🔋 电池: ${data.battery.level} | ${data.battery.status}`);
  }
  if (data.foreground) {
    console.log(`  📱 前台: ${data.foreground}`);
  }
  if (data.storage) {
    console.log(`  💾 存储: ${data.storage.used}/${data.storage.total}`);
  }
  if (data.wifi) {
    console.log(`  📡 WiFi: ${data.wifi}`);
  }
}

function showUI(data) {
  console.log(`👁️ UI 元素树 (${data.total} 个, ${data.clickable} 个可点击)`);
  console.log('═'.repeat(50));
  for (const el of data.elements) {
    const label = el.text || el.resource_id.split('/').pop() || '(空)';
    const cx = el.center ? `(${el.center[0]},${el.center[1]})` : '?';
    const click = el.clickable ? '🔘' : '  ';
    console.log(`  ${click} ${label.padEnd(25)} ${cx}`);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const relay = args.includes('--relay');
  if (relay) args.splice(args.indexOf('--relay'), 1);

  const cmd = args[0];

  try {
    if (relay) {
      // 中继模式 — 通过 GitHub
      if (cmd === 'status') {
        const data = await relayStatus();
        showStatus(data);
      } else {
        console.log('❌ 中继模式仅支持: status');
        process.exit(1);
      }
      return;
    }

    // 直连模式 — HTTP API
    switch (cmd) {
      case 'status':
      case 'info': {
        const data = await apiGet('/status');
        showStatus(data);
        break;
      }

      case 'ui':
      case 'tree': {
        const data = await apiGet('/ui');
        showUI(data);
        break;
      }

      case 'health':
      case 'ping': {
        const data = await apiGet('/health');
        console.log(data.status === 'ok' ? '✅ 连接正常' : `⚠️ ${data.status}`);
        break;
      }

      case 'notif':
      case 'notifications': {
        const data = await apiGet('/notifications');
        console.log(`🔔 ${data.count} 条通知:`);
        for (const n of data.notifications) {
          console.log(`  ${n.title || '?'}: ${n.text || ''}`);
        }
        break;
      }

      case 'screenshot':
      case 'shot': {
        const data = await apiGet('/screenshot');
        const buf = Buffer.from(data.image, 'base64');
        const filename = `phone_${Date.now()}.png`;
        const filepath = path.join(process.cwd(), filename);
        fs.writeFileSync(filepath, buf);
        console.log(`✅ 截图已保存: ${filepath}`);
        console.log(`   📐 ${data.size} | ${(buf.length / 1024).toFixed(1)} KB`);
        break;
      }

      case 'tap':
      case 'tap:text': {
        const text = args[1];
        if (!text) { console.log('用法: phone-api.js tap:text "文字"'); process.exit(1); }
        const params = { text, scroll: args.includes('--scroll'), wait: 0 };
        const waitIdx = args.indexOf('--wait');
        if (waitIdx >= 0) params.wait = parseInt(args[waitIdx + 1]) || 10;
        const data = await apiPost('/tap/text', params);
        if (data.success) {
          console.log(`✅ 点击 "${text}" @ (${data.x},${data.y}) [${data.match_type}]`);
        } else {
          console.log(`❌ ${data.error}`);
        }
        break;
      }

      case 'tap:xy':
      case 'coord': {
        const x = parseInt(args[1]);
        const y = parseInt(args[2]);
        if (isNaN(x) || isNaN(y)) { console.log('用法: phone-api.js tap:xy x y'); process.exit(1); }
        const data = await apiPost('/tap/xy', { x, y });
        console.log(`✅ 点击 (${x},${y})`);
        break;
      }

      case 'swipe': {
        const [x1, y1, x2, y2] = args.slice(1, 5).map(Number);
        if ([x1, y1, x2, y2].some(isNaN)) { console.log('用法: phone-api.js swipe x1 y1 x2 y2'); process.exit(1); }
        await apiPost('/swipe', { x1, y1, x2, y2 });
        console.log(`✅ 滑动 (${x1},${y1}) → (${x2},${y2})`);
        break;
      }

      case 'type':
      case 'text': {
        const text = args.slice(1).join(' ');
        if (!text) { console.log('用法: phone-api.js type "文字"'); process.exit(1); }
        await apiPost('/type', { text });
        console.log(`✅ 输入: ${text}`);
        break;
      }

      case 'key':
      case 'keyevent': {
        const keyMap = { back: 4, home: 3, enter: 66, power: 26, volume_up: 24, volume_down: 25 };
        const key = keyMap[args[1]] || parseInt(args[1]);
        if (isNaN(key)) { console.log('用法: phone-api.js key back|home|enter|power|24'); process.exit(1); }
        const data = await apiPost('/key', { keycode: key });
        console.log(`✅ ${data.key}`);
        break;
      }

      case 'shell':
      case 'sh': {
        const cmd2 = args.slice(1).join(' ');
        if (!cmd2) { console.log('用法: phone-api.js shell "命令"'); process.exit(1); }
        const data = await apiPost('/shell', { cmd: cmd2 });
        console.log(data.output);
        break;
      }

      case 'macro':
      case 'macro:play': {
        const name = args[1];
        if (!name) { console.log('用法: phone-api.js macro 宏名称'); process.exit(1); }
        await apiPost('/macro/play', { name });
        console.log(`✅ 宏 "${name}" 回放完成`);
        break;
      }

      default:
        console.log(`
📱 Rikkahub Phone API Client

用法:
  node phone-api.js <命令> [参数]

命令:
  status             查看手机状态
  ui                 查看屏幕 UI 树
  tap:text "文字"     按文字点击
  tap:xy x y         坐标点击
  swipe x1 y1 x2 y2  滑动
  type "文字"         输入
  key back/home/...  按键
  screenshot         截图
  notif              通知
  shell "cmd"        ADB shell
  macro 宏名称        回放宏
  health             健康检查

选项:
  --scroll        tap:text 时启用滚动查找
  --wait 秒       tap:text 时等待元素出现
  --relay         使用 GitHub 中继模式

环境变量:
  PHONE_API=http://沙箱IP:58080

示例:
  node phone-api.js status
  node phone-api.js tap:text "微信" --wait 10
  node phone-api.js screenshot
  PHONE_API=http://192.168.1.100:58080 node phone-api.js ui
`);
    }
  } catch (e) {
    console.error(`❌ 错误: ${e.message}`);
    if (e.code === 'ECONNREFUSED' || e.code === 'ECONNRESET') {
      console.error('\n💡 沙箱 API 服务器未启动或网络不通。');
      console.error('   在沙箱里启动: python3 /workspace/api_server.py');
      console.error('   或用 --relay 走 GitHub 中继模式');
    }
    process.exit(1);
  }
}

main();
