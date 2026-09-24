#!/usr/bin/env bash
# Headless screenshot of a built page. Starts a throwaway server on a random free port,
# takes the shots, and stops the server straight away — never leaves one running.
#   scripts/shot.sh <page.html> <out-prefix> [hash1 hash2 ...]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PAGE="${1:?page}"; OUT="${2:?out prefix}"; shift 2
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')
cd "$ROOT/dist"
python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
python3 - "$PORT" <<'PY'
import socket, sys, time
p=int(sys.argv[1])
for _ in range(60):
    try:
        socket.create_connection(("127.0.0.1", p), 0.2).close(); break
    except OSError: time.sleep(0.1)
PY
i=0
for H in "${@:-}"; do
  i=$((i+1))
  "$CHROME" --headless --disable-gpu --hide-scrollbars --virtual-time-budget=9000 \
    --window-size=1600,1000 --screenshot="$ROOT/$OUT-$i.png" \
    "http://127.0.0.1:$PORT/$PAGE#$H" >/dev/null 2>&1 || true
  echo "  · $OUT-$i.png  (#$H)"
done
kill $SRV 2>/dev/null || true
echo "server on port $PORT stopped"
