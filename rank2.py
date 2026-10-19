import json
M = json.load(open('aa_models_raw.json'))
M = [m for m in M if not m.get('deprecated')]

def _n(v):
    try:
        return float(v)
    except Exception:
        return None

# 只保留旗舰/主力档位：排除 (low)/(medium)/(non-reasoning) 等降档，避免同一模型刷屏
def main_variant(name):
    bad = ['(Low)', '(low)', '(Medium)', '(medium)', '(Non-reasoning)', '(non-reasoning)',
           '(High)', '(high)', '(Instant)']
    return not any(b in name for b in bad)

FLAG = [m for m in M if main_variant(m['name'])]

def top(field, n=15, pool=None, asc=False, min_ctx=0, creator=None):
    pool = pool if pool is not None else FLAG
    rows = [m for m in pool if _n(m.get(field)) is not None and (m.get('contextWindowTokens') or 0) >= min_ctx]
    if creator:
        rows = [m for m in rows if m['modelCreatorName'] == creator]
    rows.sort(key=lambda m: _n(m[field]), reverse=not asc)
    return rows[:n]

def dump(title, rows, field, pct=False, extra=None):
    print(f"\n## {title}")
    for i, m in enumerate(rows, 1):
        v = _n(m[field])
        s = f"{v*100:.1f}%" if pct else (f"{v:.0f}" if field in ('intelligenceIndex','omniscience') else f"{v:.2f}")
        e = '*' if m.get('intelligenceIndexIsEstimated') else ''
        ow = ' [开源]' if m.get('isOpenWeights') else ''
        line = f"{i}. {m['name']} — {m['modelCreatorName']} — {s}{e}{ow}"
        if extra:
            line += " | " + extra(m)
        print(line)

print("======== 旗舰档（去降档变体） ========")
dump("综合智能", top('intelligenceIndex', 15), 'intelligenceIndex', extra=lambda m: f"${m.get('price1mInputTokens')}/${m.get('price1mOutputTokens')} per M")
dump("编程 SciCode", top('scicode', 12), 'scicode', pct=True)
dump("编程 Terminal-Bench 2.1", top('terminalBench21', 12), 'terminalBench21', pct=True)
dump("Agent APEX Agents", top('apexAgents', 12), 'apexAgents', pct=True)
dump("SRE 运维", top('itbenchSre', 12), 'itbenchSre', pct=True)
dump("长上下文 AA-LCR", top('lcr', 12), 'lcr', pct=True)
dump("多模态 MMMU-Pro", top('mmmuPro', 12), 'mmmuPro', pct=True)
dump("专业知识 GDPval", top('gdpvalNormalized', 12), 'gdpvalNormalized', pct=True)
dump("硬推理 HLE", top('hle', 12), 'hle', pct=True)
dump("GPQA Diamond", top('gpqa', 12), 'gpqa', pct=True)
dump("指令遵循 IFBench", top('ifbench', 12), 'ifbench', pct=True)
dump("低幻觉", top('omniscienceNonHallucination', 12), 'omniscienceNonHallucination', pct=True)

print("\n======== 开源权重模型 Top ========")
OW = [m for m in M if m.get('isOpenWeights') and main_variant(m['name'])]
dump("开源 综合智能", top('intelligenceIndex', 12, pool=OW), 'intelligenceIndex', extra=lambda m: f"${m.get('price1mInputTokens')}/{m.get('price1mOutputTokens')}")
dump("开源 编程 SciCode", top('scicode', 10, pool=OW), 'scicode', pct=True)

print("\n======== 性价比：智能/每任务成本 ========")
def eff(m):
    c = _n(m.get('intelligenceIndexCostPerTask'))
    i = _n(m.get('intelligenceIndex'))
    return (i / c) if c and c > 0 and i else None
EFF = [m for m in FLAG if eff(m)]
EFF.sort(key=eff, reverse=True)
print("\n## 每美元智能指数（越高越划算，成本>0）")
for i, m in enumerate(EFF[:15], 1):
    print(f"{i}. {m['name']} — {m['modelCreatorName']} — 智能{m['intelligenceIndex']:.0f} / 每任务${_n(m['intelligenceIndexCostPerTask']):.2f} = {eff(m):.1f}")

print("\n## 低绝对成本榜（每任务成本最低，智能≥30）")
CH = [m for m in FLAG if _n(m.get('intelligenceIndex')) and _n(m['intelligenceIndex']) >= 30 and _n(m.get('intelligenceIndexCostPerTask'))]
CH.sort(key=lambda m: _n(m['intelligenceIndexCostPerTask']))
for i, m in enumerate(CH[:15], 1):
    print(f"{i}. {m['name']} — {m['modelCreatorName']} — 智能{m['intelligenceIndex']:.0f} — ${_n(m['intelligenceIndexCostPerTask']):.2f}/任务 — in ${m.get('price1mInputTokens')}/out ${m.get('price1mOutputTokens')}")

print("\n## 速度榜（tokens/s）")
dump("速度", top('medianOutputTokensPerSecond', 12), 'medianOutputTokensPerSecond')
print("\n## 低延迟榜（TTFT 秒）")
dump("低延迟", top('medianTimeToFirstTokenSeconds', 12, asc=True), 'medianTimeToFirstTokenSeconds')
print("\n## 超长上下文（>=1M）")
dump("上下文", top('contextWindowTokens', 10), 'contextWindowTokens')
