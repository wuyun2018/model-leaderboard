#!/bin/sh
# 本地预览服务器：手机/平板同网段可访问
# 用法: ./serve.sh [端口]
set -eu
cd "$(dirname "$0")"
PORT=${1:-8080}

IP=$(ip route get 1.1.1.1 2>/dev/null | sed -n 's/.*src \([0-9.]*\).*/\1/p' | head -1)
[ -z "$IP" ] && IP=$(ifconfig 2>/dev/null | awk '/inet /{print $2}' | grep -v '^127' | head -1)
[ -z "$IP" ] && IP="<本机IP>"

echo "本地:  http://localhost:$PORT"
echo "手机:  http://$IP:$PORT   （同一 Wi-Fi 下）"
echo "Ctrl+C 停止"
echo
exec python3 -m http.server "$PORT" --bind 0.0.0.0
