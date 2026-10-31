#!/usr/bin/env python3
"""从 aa_models_raw.json 生成 auto.js（榜单页的自动数据部分）
用法: python3 build.py
更新流程: fetch_aa.py → build.py → 刷新页面
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'aa_models_raw.json'), encoding='utf-8'))
M = [m for m in M if not m.get('deprecated')]

def num(v):
    try:
        return float(v)
    except Exception:
        return None

VARIANT = re.compile(r'\s*\((?:Low|Medium|High|Xhigh|Max|Non-reasoning|Instant|Reasoning|Thinking|Chat)[^)]*\)\s*$')

def base_name(n):
    return VARIANT.sub('', n).strip()

def flagship(m):
    """每个模型只保留最高推理档位，避免同一模型刷屏"""
    return True

_DEDUPED = None
def pool_all():
    global _DEDUPED
    if _DEDUPED is None:
        best = {}
        for m in M:
            b = base_name(m['name'])
            cur = num(m.get('intelligenceIndex')) or -1
            if b not in best or cur > (num(best[b].get('intelligenceIndex')) or -1):
                best[b] = m
        _DEDUPED = list(best.values())
    return _DEDUPED

# 智能 ≥30 的"值得用"池，避免小模型在幻觉率这类指标上刷榜
SMART30 = [m for m in pool_all() if (num(m.get('intelligenceIndex')) or 0) >= 30]

def clean(name):
    n = re.sub(r',[^)]*Fallback\)', ')', name)
    n = n.replace('(Max, Default)', '(Max)')
    return n.strip()

def money(m):
    i, o = m.get('price1mInputTokens'), m.get('price1mOutputTokens')
    if i is None and o is None:
        return '—'
    f = lambda v: ('%g' % v) if v is not None else '?'
    return f"${f(i)} / ${f(o)}"

def ctx(v):
    if not v:
        return '—'
    if v >= 1_000_000:
        x = v / 1_000_000
        return f"{x:g}M"
    return f"{v//1000}K"

def top(field, n=12, pool=None, asc=False):
    pool = pool if pool is not None else pool_all()
    rows = [m for m in pool if num(m.get(field)) is not None]
    rows.sort(key=lambda m: num(m[field]), reverse=not asc)
    return rows[:n]

def rows_std(field, n=12, pool=None, pct=True, extra=None, asc=False):
    """输出 [模型, 厂商, 分数] 或带 extra 的第4列"""
    out = []
    for m in top(field, n, pool, asc=asc):
        v = num(m[field])
        if pct:
            s = f"{v*100:.1f}%"
        elif field in ('intelligenceIndex', 'omniscience'):
            s = f"{v:.0f}"
        elif field == 'contextWindowTokens':
            s = ctx(v)
        else:
            s = f"{v:.2f}"
        nm = clean(m['name']) + (' 🟢' if m.get('isOpenWeights') else '')
        r = [nm, m['modelCreatorName'], s]
        if extra:
            r.append(extra(m))
        out.append(r)
    return out

J = lambda o: json.dumps(o, ensure_ascii=False)

CATS = []

# ---- 综合智能 ----
CATS.append({
    "id": "overall", "name": "🏆 综合智能", "kind": "list",
    "desc": "Artificial Analysis Intelligence Index —— 10 项基准加权综合分，目前最权威的单一总分。已过滤同模型的低推理档位，避免刷屏。",
    "cols": ["模型", "厂商", "智能指数", "价格 in/out (每M)"],
    "rows": rows_std("intelligenceIndex", 25, pct=False, extra=money)
})

# ---- 编程 ----
CATS.append({
    "id": "coding", "name": "💻 编程", "kind": "group",
    "desc": "四个维度分开看：写代码本身、Agentic 终端操作、真实仓库改代码、人类偏好的前端生成",
    "groups": [
        {"title": "SciCode（科学编程，写代码本身）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('scicode', 10)},
        {"title": "Terminal-Bench 2.1（Agentic 终端操作）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('terminalBench21', 10)},
        {"title": "Terminal-Bench 4.0（真实仓库改代码）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('terminalBench40', 10)},
    ]
})

# ---- Agent ----
CATS.append({
    "id": "agent", "name": "🤖 Agent", "kind": "group",
    "desc": "Agent 榜和聊天榜几乎是两套体系 —— Qwen、Kimi、GLM 在这里大幅上位",
    "groups": [
        {"title": "APEX Agents（端到端 Agent 任务）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('apexAgents', 10)},
        {"title": "τ²-bench（工具调用 / 业务流程）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('tau2', 10)},
        {"title": "τ-bench Banking（银行业务流程）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('tauBanking', 10)},
        {"title": "AnalystAgent（深度研究 / 数据分析）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('analystAgent', 10)},
        {"title": "IT-Bench SRE（运维排障）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('itbenchSre', 10)},
    ]
})

# ---- 长文本 ----
CATS.append({
    "id": "longctx", "name": "📚 长文本", "kind": "group",
    "desc": "窗口大 ≠ 用得上。AA-LCR 才是真正测「能不能读懂长文」的指标",
    "groups": [
        {"title": "AA-LCR（长上下文推理）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('lcr', 10)},
        {"title": "上下文窗口上限", "cols": ["模型", "厂商", "窗口"],
         "rows": rows_std('contextWindowTokens', 12, pct=False)},
    ]
})

# ---- 多模态 ----
CATS.append({
    "id": "multimodal", "name": "👁 多模态", "kind": "list",
    "desc": "MMMU-Pro —— 大学级图文推理，目前最硬的多模态基准",
    "cols": ["模型", "厂商", "得分"],
    "rows": rows_std('mmmuPro', 12)
})

# ---- 硬推理 ----
CATS.append({
    "id": "reasoning", "name": "🧠 硬推理", "kind": "group",
    "desc": "越难的题分越低是正常的 —— CritPt 全球最高也只有 32.9%",
    "groups": [
        {"title": "HLE（Humanity's Last Exam，最难题集）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('hle', 12)},
        {"title": "GPQA Diamond（研究生级科学问答）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('gpqa', 12)},
        {"title": "CritPt（物理推理）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('critpt', 10)},
    ]
})

# ---- 知识 / 写作 ----
CATS.append({
    "id": "knowledge", "name": "📖 知识/写作", "kind": "group",
    "desc": "专业交付物质量、知识广度、幻觉率、指令遵循",
    "groups": [
        {"title": "GDPval（专业知识工作交付物）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('gdpvalNormalized', 12)},
        {"title": "Omniscience Index（知识广度）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('omniscience', 12, pct=False)},
        {"title": "低幻觉率（要准确不要创造力时用，仅智能 ≥30）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('omniscienceNonHallucination', 12, pool=SMART30)},
        {"title": "IFBench（指令遵循 / 格式约束）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('ifbench', 12)},
    ]
})

# ---- 速度 / 成本 ----
SPEED = rows_std('medianOutputTokensPerSecond', 12, pct=False)
LAT_POOL = [m for m in pool_all() if not m.get('isReasoning')]
LAT = rows_std('medianTimeToFirstTokenSeconds', 12, pool=LAT_POOL, pct=False, asc=True)
# 高智能低成本
pool = [m for m in pool_all() if num(m.get('intelligenceIndex')) and num(m['intelligenceIndex']) >= 30
        and num(m.get('intelligenceIndexCostPerTask'))]
pool.sort(key=lambda m: num(m['intelligenceIndexCostPerTask']))
CHEAP = [[clean(m['name']) + (' 🟢' if m.get('isOpenWeights') else ''), m['modelCreatorName'],
          f"{num(m['intelligenceIndex']):.0f}", f"${num(m['intelligenceIndexCostPerTask']):.2f}",
          money(m)] for m in pool[:12]]
# 每美元智能
eff = [m for m in pool if num(m['intelligenceIndexCostPerTask']) > 0]
eff.sort(key=lambda m: num(m['intelligenceIndex']) / num(m['intelligenceIndexCostPerTask']), reverse=True)
EFF = [[clean(m['name']) + (' 🟢' if m.get('isOpenWeights') else ''), m['modelCreatorName'],
        f"{num(m['intelligenceIndex']) / num(m['intelligenceIndexCostPerTask']):.0f}",
        f"{num(m['intelligenceIndex']):.0f} @ ${num(m['intelligenceIndexCostPerTask']):.2f}"] for m in eff[:12]]

CATS.append({
    "id": "speed", "name": "⚡ 速度/成本", "kind": "group",
    "desc": "延迟榜和速度榜几乎全被小模型占据；大模型要快就得多花钱",
    "groups": [
        {"title": "输出速度（tokens/秒）", "cols": ["模型", "厂商", "t/s"], "rows": SPEED},
        {"title": "首 Token 延迟（秒，越低越好）", "cols": ["模型", "厂商", "秒"], "rows": LAT},
        {"title": "高智能低成本（智能 ≥30，按每任务成本升序）",
         "cols": ["模型", "厂商", "智能", "成本/任务", "单价 in/out"], "rows": CHEAP},
        {"title": "每美元智能指数（越高越划算）",
         "cols": ["模型", "厂商", "分/$", "明细"], "rows": EFF},
    ]
})

# ---- 开源 ----
OW = [m for m in pool_all() if m.get('isOpenWeights')]
CATS.append({
    "id": "open", "name": "🟢 开源权重", "kind": "group",
    "desc": "可自部署的开放权重模型。MiMo-V2.6-Pro 是目前唯一挤进闭源第一梯队的开源模型",
    "groups": [
        {"title": "开源综合智能", "cols": ["模型", "厂商", "智能指数", "价格 in/out"],
         "rows": rows_std('intelligenceIndex', 12, pool=OW, pct=False, extra=money)},
        {"title": "开源 SciCode（编程）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('scicode', 10, pool=OW)},
        {"title": "开源 AA-LCR（长文本）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('lcr', 10, pool=OW)},
        {"title": "开源 Agent（APEX）", "cols": ["模型", "厂商", "得分"],
         "rows": rows_std('apexAgents', 8, pool=OW)},
    ]
})

# 数据日期：优先读 fetch_aa.py 写的抓取时间，回退到当天
import time as _t
try:
    _meta = json.load(open(os.path.join(HERE, 'aa_meta.json'), encoding='utf-8'))
    DATA_DATE = _meta['fetched_at'][:10]
except Exception:
    DATA_DATE = _t.strftime('%Y-%m-%d')

out = "/* 自动生成，请勿手改 —— 由 build.py 从 aa_models_raw.json 生成 */\n"
out += f'const DATA_DATE = "{DATA_DATE}";\n'
out += f"const MODEL_COUNT = {len([m for m in M if not m.get('deprecated')])};\n"
out += "const AUTO_CATS = " + J(CATS) + ";\n"

# ---- 真实用量 + 设计偏好（来自 manual.js 的常量，这里只组装分类骨架） ----
out += """
const REAL_CATS = [
  { id:"real", name:"📊 真实用量", kind:"group",
    desc:"OpenRouter 真实 API 流量（截至 " + REAL_ASOF + "，最近 7 个完整 UTC 日）。榜单分数高 ≠ 大家在用，这里反映生产环境的真实选择；不同快照版本、:free / :batch 变体按官方口径分别排名",
    groups:[
      { title:"周用量 Top（tokens 处理量）", cols:["模型","厂商","Token","变化"], rows: REAL.week },
      { title:"单日用量 Top", cols:["模型","厂商","Token","变化"], rows: REAL.today },
      { title:"本周增长最快", cols:["模型","厂商","Token","变化"], rows: REAL.trending },
      { title:"厂商 token 份额（近一周，按 token 计）", cols:["厂商","份额","变化"], rows: REAL.share },
      { title:"热门 Agent 应用（按 token 消耗）", cols:["应用","请求数","Token"], rows: REAL.apps },
      { title:"Agent 会话成本 Top（10-49 轮会话，每次花费中位数）", cols:["应用","模型","中位花费"], rows: REAL.sessions },
      { title:"流量都在干什么（近 7 天，抽样）", cols:["任务","请求占比","token 占比"], rows: REAL.tasks },
      { title:"编程类用量 Top（周粒度·抽样估算）", cols:["模型","厂商","Token"], rows: REAL.coding },
      { title:"长上下文档用量 Top（100K 档·精确）", cols:["模型","厂商","Token"], rows: REAL.longctx }
    ].filter(g => g.rows && g.rows.length)}
];

const DESIGN_CAT = { id:"design", name:"🎨 设计偏好", kind:"list",
  desc:"Design Arena 人类盲测 Elo（Text-to-HTML 代码分类）—— 补上 LMArena 缺位的主观偏好维度",
  cols:["模型","厂商","Elo"], rows: DESIGN };
"""

open(os.path.join(HERE, 'auto.js'), 'w', encoding='utf-8').write(out)

# 刷新 index.html 的脚本版本号，绕过浏览器缓存
import time
idx = os.path.join(HERE, 'index.html')
if os.path.exists(idx):
    html = open(idx, encoding='utf-8').read()
    v = str(int(time.time()))
    html2 = re.sub(r'(src="(?:manual|realdata|local|auto)\.js)\?v=\d+', r'\g<1>?v=' + v, html)
    if html2 != html:
        open(idx, 'w', encoding='utf-8').write(html2)

print(f"OK: {len(CATS)} 个自动分类 -> auto.js")
for c in CATS:
    n = len(c.get('groups', [])) if c['kind'] == 'group' else 1
    print(f"  {c['name']}  ({n} 组)")
