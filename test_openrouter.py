#!/usr/bin/env python3
"""fetch_openrouter.py 的离线回归测试 —— 本地 mock OpenRouter API，验证聚合与 JS 输出。
用法: python3 test_openrouter.py
"""
import json, re, os, subprocess, sys, threading, tempfile, shutil, http.server, socketserver
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8791

# ---- 构造 30 天数据：模型 A 稳定增长，模型 B 新上榜，模型 C 衰减 ----
end = date.today() - timedelta(days=1)
days = [(end - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
rows = []
for idx, d in enumerate(days):
    rows.append({'date': d, 'model_permaslug': 'alpha/model-a', 'total_tokens': str(10**12 + idx * 10**11)})
    if idx >= 23:                                  # 最近 7 天才出现
        rows.append({'date': d, 'model_permaslug': 'beta/model-b:free', 'total_tokens': str(5 * 10**11)})
    rows.append({'date': d, 'model_permaslug': 'gamma/model-c', 'total_tokens': str(4 * 10**11 - idx * 10**10)})
    for k in range(3, 7):
        rows.append({'date': d, 'model_permaslug': f'vendor{k}/model-{k}',
                     'total_tokens': str(int(2 * 10**11 / k))})
    rows.append({'date': d, 'model_permaslug': 'other', 'total_tokens': '123'})


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path.split('?')[0]
        if p.endswith('/models'):
            body = {'data': [
                {'id': 'alpha/model-a', 'canonical_slug': 'alpha/model-a', 'name': 'Alpha: Model A'},
                {'id': 'beta/model-b:free', 'canonical_slug': 'beta/model-b', 'name': 'Beta: Model B'},
                {'id': 'gamma/model-c', 'canonical_slug': 'gamma/model-c', 'name': 'Gamma: Model C'},
            ]}
        elif p.endswith('/rankings-daily'):
            body = {'data': rows, 'meta': {'as_of': '2026-10-17T02:00:00Z'}}
        elif p.endswith('/app-rankings'):
            body = {'data': [{'rank': 1, 'app_name': 'TestApp', 'total_tokens': '999000000000'}]}
        elif p.endswith('/session-cost'):
            body = {'data': [
                {'app_name': 'Hermes Agent', 'app_slug': 'hermes-agent',
                 'median_session_cost_usd': 1.74, 'model_permaslug': 'alpha/model-a',
                 'turn_range': '10-49-turns'},
                {'app_name': 'Cline', 'app_slug': 'cline',
                 'median_session_cost_usd': 0.42, 'model_permaslug': 'beta/model-b',
                 'turn_range': '2-9-turns'},
            ], 'meta': {'as_of': '2026-10-17T02:00:00Z', 'window_days': 30}}
        elif p.endswith('/classifications/task'):
            body = {'data': {'window_days': 7, 'as_of': '2026-10-16', 'classifications': [
                {'tag': 'code:general_impl', 'display_name': 'Code Generation',
                 'usage_share': 0.23, 'token_share': 0.31},
                {'tag': 'agent:web_search', 'display_name': 'Web Search',
                 'usage_share': 0.15, 'token_share': 0.12},
            ]}}
        elif p.endswith('/benchmarks'):
            body = {'data': [
                {'model_permaslug': 'alpha/model-a', 'display_name': 'Model A', 'elo': 1500},
                {'model_permaslug': 'beta/model-b', 'display_name': 'Model B', 'elo': 1400},
            ]}
        else:
            body = {'error': 'nope'}
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(('127.0.0.1', PORT), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    work = tempfile.mkdtemp()
    for f in ('fetch_openrouter.py',):
        shutil.copy(os.path.join(HERE, f), work)
    env = dict(os.environ, OPENROUTER_API_KEY='sk-or-test',
               OPENROUTER_BASE=f'http://127.0.0.1:{PORT}')
    r = subprocess.run([sys.executable, os.path.join(work, 'fetch_openrouter.py')],
                       env=env, capture_output=True, text=True)
    srv.shutdown()
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr[-2000:])
        return 1

    js = open(os.path.join(work, 'realdata.js'), encoding='utf-8').read()

    def _sect(text, key):
        m = re.search(r'"' + key + r'"\s*:\s*(\[.*?\n  \])', text, re.S)
        return json.loads(m.group(1)) if m else []
    checks = [
        ('REAL_ASOF 是昨天', f'const REAL_ASOF = "{end.isoformat()}";' in js),
        ('模型 A 在周榜', 'Model A' in js),
        ('模型 B 带 free 后缀', 'Model B (free)' in js),
        ('Trending 含新上榜', '新上榜' in js),
        ('设计榜 1500', '"1500"' in js),
        ('应用榜', 'TestApp' in js),
        ('无 other 混入', '"other"' not in js),
        ('会话成本按花费降序', js.index('"Hermes Agent"') < js.index('"Cline"') if '"Cline"' in js else False),
        ('会话成本取到 1.74', '"$1.74"' in js),
        ('会话成本三列', all(len(r) == 3 for r in _sect(js, 'sessions'))),
        ('任务补其他合计', '其他合计' in js or len(_sect(js, 'tasks')) == 2),
        ('任务结构含 Code Generation', 'Code Generation' in js),
        ('任务份额格式化', '"23.0%"' in js),
        ('编程切片非空', 'coding' in js and js.count('"Model A"') >= 2),
    ]
    ok = True
    for name, cond in checks:
        print(('  PASS ' if cond else '  FAIL ') + name)
        ok = ok and cond

    # 用 node 校验 JS 语法
    n = subprocess.run(['node', '--check', os.path.join(work, 'realdata.js')],
                       capture_output=True, text=True)
    print(('  PASS ' if n.returncode == 0 else '  FAIL ') + 'node --check 语法')
    ok = ok and n.returncode == 0
    shutil.rmtree(work, ignore_errors=True)
    print('RESULT:', 'ALL PASS' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
