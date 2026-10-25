#!/usr/bin/env python3
"""抓取 Artificial Analysis 榜单并解析为 JSON。
用法: python3 fetch_aa.py [输出路径] [--cache]
  默认每次都重新下载（定时任务需要）；--cache 时复用 /tmp/aa_new.html（本地调试用）
"""
import json, re, sys, os, subprocess, time, tempfile

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
USE_CACHE = '--cache' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = ARGS[0] if ARGS else os.path.join(HERE, 'aa_models_raw.json')
HTML = '/tmp/aa_new.html'
URL = 'https://artificialanalysis.ai/leaderboards/models'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36'
MIN_HTML = 100_000


def fetch():
    """下载到临时文件，校验体积后再原子替换；失败重试 3 次"""
    last = ''
    for attempt in range(1, 4):
        fd, tmp = tempfile.mkstemp(dir='/tmp', suffix='.html')
        os.close(fd)
        r = subprocess.run(['curl', '-s', '-L', '-m', '90', '-A', UA,
                            '-H', 'Accept-Language: en-US,en;q=0.9',
                            '-w', '%{http_code}', URL, '-o', tmp],
                           capture_output=True, text=True)
        code = r.stdout.strip()
        size = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        if code == '200' and size >= MIN_HTML:
            os.replace(tmp, HTML)
            print(f'[fetch] ok {size} bytes (attempt {attempt})', file=sys.stderr)
            return
        last = f'http={code} size={size}'
        print(f'[fetch] attempt {attempt} failed: {last}', file=sys.stderr)
        if os.path.exists(tmp):
            os.unlink(tmp)
        time.sleep(5 * attempt)
    sys.exit(f'ERROR: fetch failed after 3 attempts ({last})')


if not (USE_CACHE and os.path.exists(HTML) and os.path.getsize(HTML) >= MIN_HTML):
    fetch()

h = open(HTML, encoding='utf-8', errors='ignore').read()
parts = re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', h, re.S)
if not parts:
    sys.exit('ERROR: no RSC payload found — page structure may have changed')
buf = ''.join(json.loads(p) for p in parts)

models, i = [], 0
while True:
    i = buf.find('{"slug":', i)
    if i < 0:
        break
    depth = 0; instr = False; esc = False; j = i
    while j < len(buf):
        c = buf[j]
        if instr:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == '"': instr = False
        else:
            if c == '"': instr = True
            elif c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0: break
        j += 1
    try:
        o = json.loads(buf[i:j+1])
        if 'name' in o and 'intelligenceIndex' in o:
            models.append(o)
    except Exception:
        pass
    i = j + 1

if len(models) < 100:
    sys.exit(f'ERROR: only {len(models)} models parsed — refusing to overwrite good data')

best = {}
for m in models:
    score = sum(1 for v in m.values() if v is not None)
    n = m['name']
    if n not in best or score > best[n][0]:
        best[n] = (score, m)
out = [v[1] for v in best.values()]

# 原子写入，避免下游读到半截文件
fd, tmp = tempfile.mkstemp(dir=HERE, suffix='.json')
os.close(fd)
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)
os.replace(tmp, OUT)
active = sum(1 for m in out if not m.get('deprecated'))

# 记录抓取时间（北京时间），供 build.py 生成 DATA_DATE
from datetime import datetime, timedelta, timezone
meta = {
    'fetched_at': datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S+08:00'),
    'model_count': len(out),
    'active': active,
}
mp = os.path.join(HERE, 'aa_meta.json')
mfd, mtmp = tempfile.mkstemp(dir=HERE, suffix='.json')
os.close(mfd)
with open(mtmp, 'w', encoding='utf-8') as f:
    json.dump(meta, f, ensure_ascii=False)
os.replace(mtmp, mp)

print(f'OK: {len(out)} models ({active} active) -> {OUT}')
