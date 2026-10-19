#!/usr/bin/env python3
"""模型榜单查询工具 —— 数据源 Artificial Analysis 2026-10-15 快照 (700 模型)

用法:
  python3 query.py list                      # 列出所有可用指标
  python3 query.py top scicode 10            # 按指标取前 10
  python3 query.py top scicode 10 open       # 只看开源
  python3 query.py find claude               # 按名字搜索
  python3 query.py show "Kimi K3 (Max)"      # 看某模型全部指标
"""
import json, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'aa_models_raw.json')))
M = [m for m in M if not m.get('deprecated')]

METRICS = [
    ('intelligenceIndex', '综合智能指数'),
    ('scicode', 'SciCode 科学编程'),
    ('terminalBench21', 'Terminal-Bench 2.1'),
    ('terminalBench40', 'Terminal-Bench 4.0'),
    ('terminalbenchHard', 'Terminal-Bench Hard'),
    ('tau2', 'τ²-bench 工具调用'),
    ('tauBanking', 'τ-bench 银行'),
    ('apexAgents', 'APEX Agents'),
    ('analystAgent', 'AnalystAgent 研究分析'),
    ('itbenchSre', 'IT-Bench SRE 运维'),
    ('hle', 'HLE 硬推理'),
    ('gpqa', 'GPQA Diamond'),
    ('critpt', 'CritPt 物理'),
    ('lcr', 'AA-LCR 长上下文'),
    ('mmmuPro', 'MMMU-Pro 多模态'),
    ('gdpvalNormalized', 'GDPval 专业工作'),
    ('ifbench', 'IFBench 指令遵循'),
    ('omniscience', 'Omniscience 知识广度'),
    ('omniscienceNonHallucination', '低幻觉率'),
    ('medianOutputTokensPerSecond', '输出速度 t/s'),
    ('medianTimeToFirstTokenSeconds', '首Token延迟 s'),
    ('intelligenceIndexCostPerTask', '每任务成本 USD'),
    ('contextWindowTokens', '上下文窗口'),
]
MKEYS = {k: d for k, d in METRICS}

def num(v):
    try:
        return float(v)
    except Exception:
        return None

def main_variant(name):
    bad = ('(Low)', '(low)', '(Medium)', '(medium)', '(Non-reasoning)', '(non-reasoning)', '(High)', '(high)')
    return not any(b in name for b in bad)

def cmd_list():
    print(f"{'key':32s} 说明")
    for k, d in METRICS:
        print(f"{k:32s} {d}")

def cmd_top(args):
    key = args[0]
    n = int(args[1]) if len(args) > 1 else 15
    pool = M
    if len(args) > 2 and args[2] in ('open', '开源'):
        pool = [m for m in M if m.get('isOpenWeights')]
    asc = key in ('medianTimeToFirstTokenSeconds', 'intelligenceIndexCostPerTask')
    rows = [m for m in pool if num(m.get(key)) is not None and main_variant(m['name'])]
    rows.sort(key=lambda m: num(m[key]), reverse=not asc)
    for i, m in enumerate(rows[:n], 1):
        v = num(m[key])
        s = f"{v*100:.1f}%" if v <= 1 and key not in ('intelligenceIndex', 'omniscience', 'contextWindowTokens', 'medianOutputTokensPerSecond', 'medianTimeToFirstTokenSeconds', 'intelligenceIndexCostPerTask') else f"{v:.2f}"
        ow = ' 🟢' if m.get('isOpenWeights') else ''
        print(f"{i:2d}. {m['name']}{ow} — {m['modelCreatorName']} — {s}")

def cmd_find(args):
    kw = ' '.join(args).lower()
    for m in M:
        if kw in m['name'].lower() or kw in m['modelCreatorName'].lower():
            ow = ' 🟢' if m.get('isOpenWeights') else ''
            print(f"{m['name']}{ow} — {m['modelCreatorName']} — 智能 {num(m['intelligenceIndex']):.0f} — in ${m.get('price1mInputTokens')}/out ${m.get('price1mOutputTokens')}")

def cmd_show(args):
    name = ' '.join(args).lower()
    hits = [m for m in M if name in m['name'].lower()]
    if not hits:
        print('未找到')
        return
    m = hits[0]
    print(f"== {m['name']} ({m['modelCreatorName']}) ==")
    print(f"开源权重: {'是' if m.get('isOpenWeights') else '否'} | 上下文: {m.get('contextWindowTokens')}")
    print(f"价格: in ${m.get('price1mInputTokens')}/M, out ${m.get('price1mOutputTokens')}/M, 缓存命中 ${m.get('cacheHitPrice')}")
    print(f"速度: {num(m.get('medianOutputTokensPerSecond')):.0f} t/s | 首Token: {num(m.get('medianTimeToFirstTokenSeconds')):.2f}s")
    print('-' * 46)
    for k, d in METRICS:
        v = num(m.get(k))
        if v is None:
            continue
        s = f"{v*100:.1f}%" if 0 <= v <= 1 and k not in ('intelligenceIndex', 'omniscience') else f"{v:,.2f}"
        print(f"  {d:22s} {s}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        cmd_list()
    elif sys.argv[1] == 'list':
        cmd_list()
    elif sys.argv[1] == 'top':
        cmd_top(sys.argv[2:])
    elif sys.argv[1] == 'find':
        cmd_find(sys.argv[2:])
    elif sys.argv[1] == 'show':
        cmd_show(sys.argv[2:])
    else:
        print(__doc__)
