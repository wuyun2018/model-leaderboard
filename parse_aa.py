import json, re, sys

b = open('/tmp/aa_payload.txt', encoding='utf-8').read()

# Find each model object starting with {"slug": and do brace matching
models = []
i = 0
while True:
    i = b.find('{"slug":', i)
    if i < 0:
        break
    depth = 0
    instr = False
    esc = False
    j = i
    while j < len(b):
        c = b[j]
        if instr:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                instr = False
        else:
            if c == '"':
                instr = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    break
        j += 1
    frag = b[i:j+1]
    try:
        o = json.loads(frag)
        if 'name' in o and 'intelligenceIndex' in o:
            models.append(o)
    except Exception:
        pass
    i = j + 1

# dedupe by name, keep the one with most non-null fields
best = {}
for m in models:
    n = m['name']
    score = sum(1 for v in m.values() if v is not None)
    if n not in best or score > best[n][0]:
        best[n] = (score, m)
models = [v[1] for v in best.values()]
print('parsed models:', len(models), file=sys.stderr)

json.dump(models, open('/tmp/aa_models.json', 'w'), ensure_ascii=False)
print('saved', len(models), file=sys.stderr)
