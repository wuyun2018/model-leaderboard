#!/usr/bin/env python3
"""从 OpenRouter Data API 抓真实用量 + Design Arena Elo，生成 realdata.js

用法: OPENROUTER_API_KEY=sk-or-... python3 fetch_openrouter.py [--dry]
  无 key 时不改动 realdata.js（保留上次数据），退出码 0

接口（均需 Bearer key，30 req/min、500 req/day）：
  GET /api/v1/datasets/rankings-daily?start_date=&end_date=   每日 top50 模型 token 量
  GET /api/v1/datasets/app-rankings?sort=popular&limit=10     应用榜
  GET /api/v1/benchmarks?source=design-arena&arena=models&category=codecategories
  GET /api/v1/models                                          公开目录（无需 key，用于 slug→显示名）
"""
import json
import re, os, sys, time, urllib.parse, urllib.request, tempfile
from collections import defaultdict
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'realdata.js')
BASE = os.environ.get('OPENROUTER_BASE', 'https://openrouter.ai/api/v1')
KEY = os.environ.get('OPENROUTER_API_KEY', '').strip()
DRY = '--dry' in sys.argv
GAP = '—'


def get(path, params=None, auth=True, tries=3):
    url = BASE + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    headers = {'Accept': 'application/json', 'User-Agent': 'model-leaderboard/1.0'}
    if auth and KEY:
        headers['Authorization'] = 'Bearer ' + KEY
    last = ''
    for n in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = f'{type(e).__name__}: {e}'
            print(f'[openrouter] {path} try {n} failed: {last}', file=sys.stderr)
            time.sleep(3 * n)
    raise RuntimeError(f'{path} failed: {last}')


def fmt(v):
    v = float(v)
    if v >= 1e12:
        s = f'{v/1e12:.1f}'
    elif v >= 1e9:
        s = f'{v/1e9:.2f}'
    elif v >= 1e6:
        s = f'{v/1e6:.1f}M'
        return s
    else:
        return f'{v:.0f}'
    s = s.rstrip('0').rstrip('.')
    return s + ('T' if v >= 1e12 else 'B')


def pct(cur, prev):
    if not prev:
        return '新上榜'
    d = (cur - prev) / prev * 100
    out = f'{d:+.1f}%' if abs(d) < 1 else f'{d:+.0f}%'
    return '0%' if out in ('+0.0%', '-0.0%', '+0%', '-0%') else out


def main():
    if not KEY:
        print('[openrouter] OPENROUTER_API_KEY 未设置 —— 跳过自动抓取，realdata.js 保持不变')
        print('[openrouter] 设置方式: export OPENROUTER_API_KEY=sk-or-... （或在 Minis 设置里加环境变量）')
        return 0

    # 1) 模型显示名映射（公开接口，无需 key）
    name_of, auth_name, created_of = {}, {}, {}
    try:
        cat = get('/models', auth=False)
        models = cat.get('data', [])
        # 两轮：先把非 variant（id 不含冒号）写进去，再补 variant，避免 "xxx (batch)" 覆盖主名
        for strict in (True, False):
            for m in models:
                mid = m.get('id') or ''
                if not mid or (':' in mid) == strict:
                    continue
                nm = m.get('name') or mid
                nm = nm.split(': ', 1)[-1] if ': ' in nm else nm
                auth = mid.split('/')[0]
                if ': ' in (m.get('name') or '') and auth not in auth_name:
                    auth_name[auth] = m['name'].split(': ', 1)[0]
                for k in (mid, m.get('canonical_slug')):
                    if k:
                        name_of.setdefault(k, nm)
                        created_of.setdefault(k, m.get('created') or 0)
        print(f'[openrouter] catalog {len(name_of)} slugs / {len(auth_name)} authors', file=sys.stderr)
    except Exception as e:
        print(f'[openrouter] catalog failed ({e}) — 用 slug 尾部当名字', file=sys.stderr)

    # ---- 快照归并：同一产品的多个版本号快照合并显示，避免「DeepSeek V4.1 Flash」
    #      和「DeepSeek V4.1 Flash (20261017)」拆成两行各占 1、2 名 ----
    PROD_RE = re.compile(r'^(.*?)[-@_](\d{8})$')   # 尾部 8 位日期版本号

    def product_key(slug):
        """同一产品的 slug 归到同一个 key：去掉 :free/:batch 变体和尾部日期。"""
        base = slug
        for suf in (':free', ':batch', ':nitro', ':floor', ':extended', ':thinking'):
            if base.endswith(suf):
                base = base[:-len(suf)]
        m = PROD_RE.match(base)
        return m.group(1) if m else base

    def product_name(slug):
        """产品显示名：优先 catalog 名（已不含日期），否则去掉尾部日期后美化。"""
        key = product_key(slug)
        nm = name_of.get(key) or name_of.get(key + '-free')
        if not nm:
            for cand, cn in name_of.items():
                if product_key(cand) == key:
                    nm = cn
                    break
        if not nm:
            nm = key.split('/')[-1].replace('-', ' ').title()
        # 去掉名称里可能残留的 (batch)/(free) 之类变体后缀
        nm = re.sub(r'\s*\((?:batch|free|nitro|extended|thinking)\)$', '', nm)
        return nm

    def display(slug):
        base = slug
        free = base.endswith(':free')
        nm = product_name(slug)
        return nm + (' (free)' if free else '')

    def author(slug):
        a = slug.split('/')[0]
        return auth_name.get(a, a)

    # 2) 日粒度用量
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=29)
    r = get('/datasets/rankings-daily', {'start_date': start.isoformat(), 'end_date': end.isoformat()})
    rows = r.get('data', [])
    as_of = (r.get('meta') or {}).get('as_of', '')
    per_day = defaultdict(dict)
    for x in rows:
        if x['model_permaslug'] == 'other':
            continue
        per_day[x['date']][x['model_permaslug']] = int(x['total_tokens'])
    days = sorted(per_day)
    if not days:
        raise RuntimeError('rankings-daily 返回空数据')
    print(f'[openrouter] {len(days)} days {days[0]}..{days[-1]}', file=sys.stderr)

    def window(dlist, fold=True):
        agg = defaultdict(int)
        for d in dlist:
            for k, v in per_day[d].items():
                agg[product_key(k) if fold else k] += v
        return agg

    # 归并后要取显示名：优先用该产品「最新版本号」的 slug 查 catalog，
    # 查不到再退回产品 key 本身。这样 DeepSeek V4.1 Flash 的两个快照合并后仍叫原名。
    rep = {}
    for slug in {x['model_permaslug'] for x in rows}:
        pk = product_key(slug)
        prev = rep.get(pk)
        if prev is None or slug > prev:      # 版本号靠后的 slug 字典序更大
            rep[pk] = slug

    def disp(slug_or_key):
        """窗口聚合后的 key 是产品 key，映射回代表 slug 再取显示名。"""
        real = rep.get(slug_or_key, slug_or_key)
        return display(real)

    last1 = window(days[-1:])
    last7 = window(days[-7:])
    prev7 = window(days[-14:-7])
    last30 = window(days[-30:])

    def top(d, n=10, key=None):
        return sorted(d.items(), key=lambda kv: -kv[1])[:n]

    week = [[disp(k), author(k), fmt(v), pct(v, prev7.get(k, 0))] for k, v in top(last7)]
    prev_day = window(days[-2:-1])   # 昨日也需按产品归并，否则比值会飙到几千%
    today = [[disp(k), author(k), fmt(v), pct(v, prev_day.get(k, 0))] for k, v in top(last1)]

    # trending: 绝对增量（本周 vs 前一周），过滤本周 <1M
    growth = [(k, last7[k] - prev7.get(k, 0), last7[k]) for k in last7]
    growth = [g for g in growth if g[2] >= 1_000_000]
    growth.sort(key=lambda g: -g[1])
    trending = []
    for k, delta, cur in growth[:5]:
        prev = prev7.get(k, 0)
        tag = '新上榜' if prev == 0 else f'{"+" if delta > 0 else ""}{delta/prev*100:.0f}%'
        trending.append([disp(k), author(k), fmt(cur), tag])

    # 3) 厂商 token 份额
    by_auth = defaultdict(int)
    tot = 0
    prev_auth = defaultdict(int)
    for k, v in last7.items():
        a = author(rep.get(k, k))
        by_auth[a] += v
        tot += v
    ptot = sum(prev7.values()) or 1
    for k, v in prev7.items():
        prev_auth[author(rep.get(k, k))] += v
    share = []
    for a, v in sorted(by_auth.items(), key=lambda kv: -kv[1])[:9]:
        share.append([a, f'{v/tot*100:.1f}%', pct(v, prev_auth.get(a, 0)) if v >= 1e9 else GAP])
    other = 100 - sum(float(x[1].rstrip('%')) for x in share)
    if other > 0.05:
        share.append(['其他合计', f'{other:.1f}%', GAP])

    # 4) 应用榜
    apps = []
    try:
        ap = get('/datasets/app-rankings', {'sort': 'popular', 'limit': 10,
                                            'start_date': days[-1], 'end_date': days[-1]})
        for a in ap.get('data', [])[:10]:
            req = a.get('total_requests')
            apps.append([a.get('app_name', '?'),
                         fmt(req) if req else GAP,
                         fmt(a.get('total_tokens', 0))])
    except Exception as e:
        print(f'[openrouter] app-rankings failed: {e}', file=sys.stderr)

    # 5) Design Arena
    design = []
    try:
        bm = get('/benchmarks', {'source': 'design-arena', 'arena': 'models',
                                 'category': 'codecategories', 'max_results': 15})
        items = [x for x in bm.get('data', []) if x.get('elo')]
        items.sort(key=lambda x: -x['elo'])
        for x in items[:12]:
            nm = x.get('display_name') or display(x.get('model_permaslug', ''))
            design.append([nm, author(x.get('model_permaslug', '')).title(), str(int(x['elo']))])
    except Exception as e:
        print(f'[openrouter] design-arena failed: {e}', file=sys.stderr)

    # 6) 会话成本：只看 10-49 turns 档，按「应用 × 模型」展开
    sessions = []
    try:
        sc = get('/datasets/session-cost', {'turn_range': '10-49-turns', 'limit': 500})
        cells = [c for c in sc.get('data', []) if c.get('median_session_cost_usd') is not None]
        cells.sort(key=lambda c: -float(c['median_session_cost_usd']))
        seen = set()
        for c in cells:
            k = (c.get('app_slug'), c.get('model_permaslug'))
            if k in seen:
                continue
            seen.add(k)
            sessions.append([c.get('app_name') or c.get('app_slug'),
                             display(c.get('model_permaslug', '')),
                             f"${float(c['median_session_cost_usd']):.2f}"])
            if len(sessions) >= 12:
                break
    except Exception as e:
        print(f'[openrouter] session-cost failed: {e}', file=sys.stderr)

    # 7) 流量任务结构
    tasks = []
    try:
        tc = get('/classifications/task', {'window': '7d'})
        cls = (tc.get('data') or {}).get('classifications') or []
        cls = [c for c in cls if c.get('token_share') is not None]
        cls.sort(key=lambda c: -c['token_share'])
        for c in cls[:10]:
            tasks.append([c.get('display_name') or c.get('tag'),
                          f"{c['usage_share']*100:.1f}%",
                          f"{c['token_share']*100:.1f}%"])
        if len(cls) > 10:
            tasks.append(['其他合计',
                          f"{sum(x['usage_share'] for x in cls[10:])*100:.1f}%",
                          f"{sum(x['token_share'] for x in cls[10:])*100:.1f}%"])
        t_asof = (tc.get('data') or {}).get('as_of') or ''
        if t_asof:
            print(f'[openrouter] task-classifications as_of {t_asof}', file=sys.stderr)
    except Exception as e:
        print(f'[openrouter] classifications failed: {e}', file=sys.stderr)

    # 8) 两个切片：编程类 / 100K 上下文档（抽样估算，周粒度）
    def slice_cat(params, n=10):
        d = get('/datasets/rankings-daily', params)
        rows = [x for x in d.get('data', []) if x['model_permaslug'] != 'other']
        agg = defaultdict(int)
        for x in rows:
            agg[product_key(x['model_permaslug'])] += int(x['total_tokens'])
        return [[disp(k), author(k), fmt(v)] for k, v in
                sorted(agg.items(), key=lambda kv: -kv[1])[:n]]

    coding, longctx = [], []
    try:
        coding = slice_cat({'category': 'programming', 'period': 'week',
                            'start_date': days[-7], 'end_date': days[-1]})
    except Exception as e:
        print(f'[openrouter] category=programming failed: {e}', file=sys.stderr)
    try:
        longctx = slice_cat({'context_bucket': '100K',
                             'start_date': days[-7], 'end_date': days[-1]})
    except Exception as e:
        print(f'[openrouter] context_bucket failed: {e}', file=sys.stderr)

    if len(week) < 5 or not design:
        raise RuntimeError('数据不足以生成 realdata.js，保留原文件')

    def js(name, obj):
        return f'const {name} = ' + json.dumps(obj, ensure_ascii=False, indent=2) + ';\n'

    head = ('/* 自动生成 —— 由 fetch_openrouter.py 从 OpenRouter Data API 构建\n'
            f'   数据截止 {days[-1]}（周=最近7个完整日，月=最近30日） · 生成 {time.strftime("%Y-%m-%d %H:%M")}\n'
            '   注：rankings-daily 每日只给 top50 模型，跨日合计会漏掉长尾\n'
            '   许可 CC BY 4.0 · Source: OpenRouter (openrouter.ai/rankings) as of '
            f'{as_of}; Design Arena via OpenRouter */\n\n')
    body = (f'const REAL_ASOF = "{days[-1]}";\n'
            + js('REAL', {'week': week, 'today': today, 'trending': trending,
                          'share': share, 'apps': apps, 'sessions': sessions,
                          'tasks': tasks, 'coding': coding, 'longctx': longctx})
            + js('DESIGN', design))

    if DRY:
        print(head + body)
        return 0

    fd, tmp = tempfile.mkstemp(dir=HERE, suffix='.js')
    os.close(fd)
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(head + body)
    os.replace(tmp, OUT)
    print(f'OK: week={len(week)} today={len(today)} design={len(design)} apps={len(apps)} -> {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
