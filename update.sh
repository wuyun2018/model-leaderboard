#!/bin/sh
# 一键更新：AA 细分指标 + OpenRouter 用量/Design Arena + 重建页面
# 用法: ./update.sh            正常更新
#       ./update.sh --push     更新后 git 提交并推送（GitHub Pages 场景）
set -eu
cd "$(dirname "$0")"

mkdir -p logs
LOG="logs/update-$(date +%Y%m%d-%H%M%S).log"
[ -f .env ] && . ./.env
PY=${PYTHON:-python3}

exec 3>&1              # 保留终端输出
exec >>"$LOG" 2>&1     # 之后全部写日志

echo "=== $(date '+%F %T') 开始更新 ==="
$PY fetch_aa.py
$PY fetch_openrouter.py || echo "!! OpenRouter 抓取失败，沿用上次 realdata.js"
$PY build.py

if [ "${1:-}" = "--push" ]; then
  if [ -n "$(git status --porcelain 2>/dev/null || true)" ]; then
    git add -A
    git commit -q -m "chore: daily refresh $(date +%F)" || true
    if git push -q; then echo "已推送"; else echo "!! git push 失败（检查凭据）"; fi
  else
    echo "无变更，跳过提交"
  fi
fi

echo "=== $(date '+%F %T') 完成 ==="

# 只保留最近 30 份日志
ls -1t logs/update-*.log 2>/dev/null | tail -n +31 | while read -r f; do rm -f "$f"; done

cat "$LOG" >&3
exit 0
