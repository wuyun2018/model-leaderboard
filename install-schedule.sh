#!/bin/sh
# 纯本地定时更新：不推 GitHub，只刷新本机文件
# 用法:
#   ./install-schedule.sh             安装（每天 07:30）
#   ./install-schedule.sh 08:15       指定时间
#   ./install-schedule.sh --remove    卸载
#   ./install-schedule.sh --run       立刻跑一次
#   ./install-schedule.sh --dry-run   只打印将写入的 crontab，不改动
set -eu
cd "$(dirname "$0")"
DIR=$(pwd)
MARK="# model-leaderboard"

ACTION=install
WHEN=07:30
for a in "$@"; do
  case "$a" in
    --remove)  ACTION=remove ;;
    --run)     ACTION=run ;;
    --dry-run) ACTION=dryrun ;;
    -*)        echo "未知参数: $a"; exit 2 ;;
    *)         WHEN=$a ;;
  esac
done

HOUR=$(echo "$WHEN" | cut -d: -f1 | sed 's/^0*//'); [ -z "$HOUR" ] && HOUR=0
MIN=$(echo "$WHEN" | cut -d: -f2 | sed 's/^0*//'); [ -z "$MIN" ] && MIN=0
LINE="$MIN $HOUR * * * cd $DIR && ./update.sh >> logs/cron.log 2>&1 $MARK"

current() { crontab -l 2>/dev/null || true; }
bare()    { current | grep -v "$MARK" || true; }

case "$ACTION" in
  run)
    ./update.sh
    ;;
  remove)
    bare | crontab -
    echo "已移除定时任务"
    ;;
  dryrun)
    { bare; echo "$LINE"; } | sed 's/^/  /'
    echo "(dry-run，未写入)"
    ;;
  install)
    command -v crontab >/dev/null 2>&1 || { echo "找不到 crontab，请先安装 cron"; exit 1; }
    mkdir -p logs
    { bare; echo "$LINE"; } | crontab -
    echo "已安装：每天 $WHEN"
    echo "  $LINE"
    echo
    echo "查看: crontab -l | grep model-leaderboard"
    echo "立即跑一次: ./install-schedule.sh --run"
    ;;
esac
