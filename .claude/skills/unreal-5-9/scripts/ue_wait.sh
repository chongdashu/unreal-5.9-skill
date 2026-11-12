#!/bin/zsh
# Wait until the Unreal Editor's MCP server answers and (optionally) the expected level is open.
#   usage: ue_wait.sh <ProjectName> [level-name-substring] [timeout-seconds]
# Exits 0 when ready, 1 if the editor process is gone, crashed, or could not bind its port, 2 on timeout.
# A loop that only polls the port waits forever on a dead or serverless editor.
PROJECT="$1"; LEVEL="${2:-}"; LIMIT="${3:-900}"
LOG="$HOME/Library/Logs/Unreal Engine/${PROJECT}Editor/${PROJECT}.log"   # the Mac log; not <Project>/Saved/Logs
HERE="$(cd "$(dirname "$0")" && pwd)"
START=$(date +%s)
sleep 3
while true; do
  if ! pgrep -f 'UnrealEditor.app/Contents/MacOS/UnrealEditor' >/dev/null; then
    echo "editor process is not running"; grep -n -A2 'Fatal error' "$LOG" 2>/dev/null | head -6; exit 1
  fi
  if grep -q 'HttpListener unable to bind' "$LOG" 2>/dev/null; then
    echo "the MCP port was still held when this editor started (an editor still quitting, or a leftover CrashReportClient): quit it, wait for the port to free, relaunch"
    exit 1
  fi
  if grep -q 'Fatal error' "$LOG" 2>/dev/null; then
    echo "fatal error in log"; grep -n -A2 'Fatal error' "$LOG" | head -6; exit 1
  fi
  OUT=$(python3 "$HERE/uemcp.py" py -c 'w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
w.get_path_name() if w else "no world"' 2>&1)
  if [ $? -eq 0 ] && { [ -z "$LEVEL" ] || [[ "$OUT" == *"$LEVEL"* ]]; }; then
    echo "ready after $(( $(date +%s) - START )) s: $OUT"; exit 0
  fi
  if [ $(( $(date +%s) - START )) -ge "$LIMIT" ]; then echo "timed out; last reply: $OUT"; exit 2; fi
  sleep 5
done
