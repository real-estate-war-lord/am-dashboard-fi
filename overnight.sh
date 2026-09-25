#!/usr/bin/env bash
# overnight.sh — Finland Macro Dashboard v2.1 (Danish v3.0 parity + signed-indicator colours) as sequential,
# unattended Claude Code phases. Modelled on the Danish repo's overnight.sh.
#
#   ./overnight.sh preflight         # before bed: checks, Playwright, branch v2.1-ui, plan commit, test call
#   ./overnight.sh run [V1 V2 …]     # the night (default V1…V7); AUTO_RELEASE=1 publishes if everything is green
#   ./overnight.sh gate V3           # the self-check (used by the agent and by this wrapper)
#   ./overnight.sh release           # morning: merge v2.1-ui → main, tag v2.1, push (GitHub Pages deploys)
#   ./overnight.sh status            # quick look at the report
#
# Never pushes except in `release` (or AUTO_RELEASE=1 after an all-green night). Logs live in logs/ (git-excluded).
set -u
REPO="$(cd "$(dirname "$0")" && pwd)"; cd "$REPO" || exit 1
BRANCH="v2.1-ui"; TAG="v2.1"
ALL_PHASES=(V1 V2 V3 V4 V5 V6 V7)
PHASE_TIMEOUT="${PHASE_TIMEOUT:-9000}"     # seconds per claude call (150 min)
LIMIT_WAIT="${LIMIT_WAIT:-1200}"           # seconds to sleep when a usage limit is hit
LIMIT_MAX_WAITS="${LIMIT_MAX_WAITS:-15}"
MODEL_ARGS=(); [ -n "${MODEL:-}" ] && MODEL_ARGS=(--model "$MODEL")
ALLOWED_TOOLS="Read,Edit,Write,Glob,Grep,\
Bash(git status:*),Bash(git diff:*),Bash(git log:*),Bash(git show:*),Bash(git add:*),Bash(git commit:*),Bash(git mv:*),Bash(git rm:*),Bash(git checkout -- :*),Bash(git restore:*),\
Bash(./overnight.sh gate:*),Bash(python3 scripts/build_dashboard.py:*),Bash(python3 tests/ui_v2.spec.py:*),Bash(.venv-ui/bin/python3 tests/ui_v2.spec.py:*),\
Bash(node --test:*),Bash(node --check:*),Bash(ls:*),Bash(wc:*),Bash(grep:*),Bash(head:*),Bash(tail:*),Bash(mkdir:*)"
DENIED_TOOLS="Bash(git push:*),Bash(git reset:*),Bash(git branch:*),Bash(git merge:*),Bash(curl:*),Bash(pip:*),Bash(npm:*),Bash(make fetch:*),WebFetch,WebSearch"
CLAUDE_PERMS=(--permission-mode acceptEdits --allowedTools "$ALLOWED_TOOLS" --disallowedTools "$DENIED_TOOLS")
PY="$REPO/.venv-ui/bin/python3"; [ -x "$PY" ] || PY=python3
RUN_ID="${RUN_ID:-$(date +%Y%m%d)}"
LOGS="$REPO/logs/overnight-$RUN_ID"; mkdir -p "$LOGS"
REPORT="$LOGS/OVERNIGHT_REPORT.md"
PH_DIR="$REPO/docs/v2_1/phases"
FORBIDDEN='^(\.github/|data/|config/|scripts/|docs/v2_1/ref/)'
ALLOWED_SCRIPT='^scripts/build_dashboard\.py$'

log()    { printf '%s %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOGS/run.log"; }
report() { printf '%s\n' "$*" >> "$REPORT"; }
with_timeout() { local s="$1"; shift; perl -e 'alarm shift; exec @ARGV or die "exec: $!"' "$s" "$@"; }

exclude_local() {   # keep venv, logs and the Danish reference copy out of git without touching .gitignore
  for p in '.venv-ui/' 'logs/' 'docs/v2_1/ref/'; do
    grep -qxF "$p" .git/info/exclude 2>/dev/null || echo "$p" >> .git/info/exclude
  done
}

gate() {   # $1 = phase id. Exit 0 = green. Output → logs/<run>/<phase>.gate.log
  local ph="${1:-V7}" out="$LOGS/${1:-adhoc}.gate.log"
  (
    echo "== build";    "$PY" scripts/build_dashboard.py || exit 1
    echo "== js tests"; node --test tests/*.test.js || exit 1
    echo "== py tests (informational)"; "$PY" -m unittest discover -s tests -p 'test_*.py' || echo "(python unit tests failed — informational only)"
    echo "== ui suite up to $ph (+ screenshots in docs/ui_v2/)"
    PHASE="$ph" SHOTS=1 "$PY" -u tests/ui_v2.spec.py || exit 1
    echo "== budgets"
    sz=$(wc -c < src/app.js | tr -d ' ');   [ "$sz" -le 471040 ] || { echo "app.js $sz B > 460 KB"; exit 1; }
    sz=$(wc -c < src/style.css | tr -d ' '); [ "$sz" -le 168960 ] || { echo "style.css $sz B > 165 KB"; exit 1; }
    echo "GATE GREEN"
  ) >"$out" 2>&1
  local rc=$?
  echo "gate $ph: $([ $rc -eq 0 ] && echo GREEN || echo RED) — log: $out  shots: docs/ui_v2/"
  return $rc
}

check_commit() {
  local ph="$1"
  [ "$(git rev-list --count "v21-$ph-start..HEAD")" -ge 1 ] || { echo "no commit made"; return 1; }
  [ -z "$(git status --porcelain)" ] || { echo "working tree not clean"; git status --porcelain | head; return 1; }
  local bad; bad=$(git diff --name-only "v21-$ph-start..HEAD" | grep -E "$FORBIDDEN" | grep -vE "$ALLOWED_SCRIPT")
  [ -z "$bad" ] || { echo "forbidden paths changed: $bad"; return 1; }
  [ ! -f "$PH_DIR/$ph.FAILED.md" ] || { echo "agent reported failure ($ph.FAILED.md)"; return 1; }
}

hit_limit() { grep -qiE "usage limit|rate.?limit|limit (reached|exceeded)|resets at|overloaded" "$1"; }

run_claude() {
  local waits=0
  while :; do
    with_timeout "$PHASE_TIMEOUT" claude -p "${CLAUDE_PERMS[@]}" --output-format text \
        ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} < "$1" > "$2" 2>&1
    local rc=$?
    if [ $rc -ne 0 ] && hit_limit "$2" && [ $waits -lt "$LIMIT_MAX_WAITS" ]; then
      waits=$((waits + 1)); log "usage/rate limit — sleeping $LIMIT_WAIT s ($waits/$LIMIT_MAX_WAITS)"
      cp "$2" "$2.limit$waits"; sleep "$LIMIT_WAIT"; continue
    fi
    return $rc
  done
}

run_phase() {
  local ph="$1" att="$2" prev="${3:-}" t0=$SECONDS
  local prompt="$LOGS/$ph.attempt$att.prompt.md"
  {
    cat "$PH_DIR/_COMMON.md"; echo; echo "---"; echo
    echo "# YOUR PHASE: $ph  (replace <PHASE> with $ph everywhere above)"; echo
    cat "$PH_DIR/$ph.md"
    if [ -n "$prev" ] && [ -f "$prev" ]; then
      echo; echo "## RETRY — the previous attempt of this phase was rolled back. Its gate/commit output:"
      echo '```'; tail -n 150 "$prev"; echo '```'
      echo "Start from the clean state, avoid what failed, keep the scope tight."
    fi
  } > "$prompt"
  log "$ph attempt $att: claude running (timeout ${PHASE_TIMEOUT}s)"
  run_claude "$prompt" "$LOGS/$ph.attempt$att.log"
  log "$ph attempt $att: claude exited $? after $(( (SECONDS - t0) / 60 )) min"
  local why; why=$(check_commit "$ph") || { log "$ph: $why"; echo "$why" > "$LOGS/$ph.gate.log"; return 1; }
  gate "$ph" >/dev/null || { log "$ph: gate RED ($LOGS/$ph.gate.log)"; return 1; }
  log "$ph: GREEN at $(git rev-parse --short HEAD)"
}

rollback() {
  local ph="$1"
  [ -f "$PH_DIR/$ph.FAILED.md" ] && cp "$PH_DIR/$ph.FAILED.md" "$LOGS/"
  git reset -q --hard "v21-$ph-start"; git clean -qfd -e logs -e .venv-ui -e docs/v2_1/ref -e docs/ui_v2
}

preflight() {
  local bad=0
  exclude_local
  echo "· python: $(python3 --version 2>&1)   node: $(node --version 2>&1)   claude: $(claude --version 2>&1 | head -1)"
  command -v node >/dev/null || { echo "✗ node missing"; bad=1; }
  command -v claude >/dev/null || { echo "✗ claude CLI missing"; bad=1; }
  if [ -n "$(git status --porcelain -- . ':!docs/v2_1' ':!overnight.sh' ':!tests/ui_v2.spec.py')" ]; then
    echo "✗ uncommitted changes outside docs/v2_1, overnight.sh, tests/ui_v2.spec.py:"; git status --porcelain | head; exit 1
  fi
  if ! git rev-parse --verify -q "$BRANCH" >/dev/null; then
    git stash -q -u -- docs/v2_1 overnight.sh tests/ui_v2.spec.py 2>/dev/null; local stashed=$?
    git checkout -q main && git pull -q --ff-only origin main || { echo "✗ could not update main from GitHub"; [ $stashed -eq 0 ] && git stash pop -q; exit 1; }
    echo "· main is at $(git log -1 --format='%h %s')"
    git checkout -q -b "$BRANCH" main
    [ $stashed -eq 0 ] && git stash pop -q
  fi
  git checkout -q "$BRANCH" || { echo "✗ cannot switch to $BRANCH"; exit 1; }
  if [ -n "$(git status --porcelain -- docs/v2_1 overnight.sh tests/ui_v2.spec.py)" ]; then
    chmod +x overnight.sh; git add docs/v2_1 overnight.sh tests/ui_v2.spec.py
    git commit -q -m "v2.1 P0: parity plan, phase prompts, overnight runner" && echo "✓ plan committed on $BRANCH"
  fi
  if ! "$PY" -c "import playwright" 2>/dev/null; then
    echo "· creating .venv-ui with Playwright (one-off, ~150 MB)…"
    python3 -m venv .venv-ui && .venv-ui/bin/pip -q install playwright && .venv-ui/bin/python3 -m playwright install chromium || { echo "✗ Playwright install failed"; bad=1; }
    PY="$REPO/.venv-ui/bin/python3"
  fi
  "$PY" -c "from playwright.sync_api import sync_playwright; print('✓ playwright ok')" || bad=1
  "$PY" scripts/build_dashboard.py >/dev/null && echo "✓ build ok" || { echo "✗ build failed"; bad=1; }
  node --test tests/*.test.js >/dev/null 2>&1 && echo "✓ js tests ok" || { echo "✗ js tests failed"; bad=1; }
  echo "· baseline ui suite (v2.0 checks, ~9 min)…"
  PHASE=P10 "$PY" -u tests/ui_v2.spec.py > "$LOGS/baseline.log" 2>&1 && echo "✓ baseline ui suite green" || echo "· baseline ui suite has failures — see $LOGS/baseline.log (the night can still run)"
  echo "· testing an unattended claude call…"
  if with_timeout 180 claude -p "${CLAUDE_PERMS[@]}" "Run the shell command: ls docs/v2_1 — then reply with exactly: READY" 2>&1 | grep -q READY; then echo "✓ claude -p works unattended with the allow-list"; else echo "✗ claude -p did not answer READY — run 'claude' once interactively to log in"; bad=1; fi
  [ $bad -eq 0 ] && echo "✓ PREFLIGHT OK — start the night with:  ./overnight.sh run" || { echo "✗ PREFLIGHT FAILED"; exit 1; }
}

release() {
  git checkout -q "$BRANCH" || exit 1
  [ -z "$(git status --porcelain)" ] || { echo "✗ tree not clean"; exit 1; }
  gate V7 || { echo "✗ gate not green — not releasing"; exit 1; }
  git fetch -q origin
  git checkout -q main && git merge -q --ff-only origin/main 2>/dev/null
  git merge -q --no-ff "$BRANCH" -m "Release $TAG — Danish v3.0 parity and signed-indicator colours" || { echo "✗ merge conflict — resolve by hand"; git merge --abort; git checkout -q "$BRANCH"; exit 1; }
  git tag -f "$TAG" >/dev/null
  git push -q origin main && git push -q -f origin "$TAG" && echo "✓ $TAG pushed — GitHub Pages deploys in a few minutes: https://real-estate-war-lord.github.io/am-dashboard-fi/"
  git checkout -q "$BRANCH"
}

main_run() {
  local phases; if [ $# -gt 0 ]; then phases=("$@"); else phases=("${ALL_PHASES[@]}"); fi
  exclude_local; git checkout -q "$BRANCH" || { echo "run preflight first"; exit 1; }
  [ -f "$REPORT" ] || { report "# Overnight report — FI $TAG ($(date '+%F %H:%M'))"; report "";
    report "Branch \`$BRANCH\`. Logs \`$LOGS\`. Screenshots \`docs/ui_v2/\`."; report "";
    report "| Phase | Result | Commit | Min | Notes |"; report "|---|---|---|---|---|"; }
  local fails=0 allgreen=1
  for ph in "${phases[@]}"; do
    local t0=$SECONDS; git tag -f "v21-$ph-start" >/dev/null
    if run_phase "$ph" 1 || { rollback "$ph"; run_phase "$ph" 2 "$LOGS/$ph.gate.log"; }; then
      report "| $ph | ✓ green | $(git rev-parse --short HEAD) | $(( (SECONDS - t0) / 60 )) | |"; fails=0
    else
      rollback "$ph"; allgreen=0; fails=$((fails + 1))
      report "| $ph | ✗ rolled back | – | $(( (SECONDS - t0) / 60 )) | $ph.attempt2.log, $ph.gate.log |"
      [ "$ph" = V1 ] && { report ""; report "**Stopped: V1 (audit) failed — later phases depend on it.**"; break; }
      [ $fails -ge 2 ] && { report ""; report "**Stopped: two phases in a row failed.**"; break; }
    fi
  done
  report ""
  if [ $allgreen -eq 1 ] && [ "${AUTO_RELEASE:-0}" = 1 ] && [ ${#phases[@]} -eq ${#ALL_PHASES[@]} ]; then
    log "all phases green — AUTO_RELEASE=1 → releasing"; release >>"$LOGS/release.log" 2>&1 \
      && report "**Released $TAG to GitHub Pages automatically.**" || report "**Auto-release failed — see release.log; run ./overnight.sh release by hand.**"
  else
    report "Not released. Review, then publish with: \`./overnight.sh release\`"
  fi
  report ""; report "Morning: read docs/v2_1/RELEASE_NOTES_FI.md and docs/v2_1/QA.md; screenshots in docs/ui_v2/"
  log "done — $REPORT"
}

case "${1:-}" in
  preflight) preflight ;;
  gate)      gate "${2:-V7}" ;;
  release)   release ;;
  status)    cat "$REPORT" 2>/dev/null || ls -t logs/ ;;
  run)       shift
             if command -v caffeinate >/dev/null && [ -z "${CAFFEINATED:-}" ]; then
               CAFFEINATED=1 RUN_ID="$RUN_ID" exec caffeinate -dimsu "$0" run "$@"; fi
             main_run "$@" ;;
  *) sed -n '2,10p' "$0"; exit 2 ;;
esac
