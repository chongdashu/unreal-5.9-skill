#!/bin/zsh
# Quit the Unreal Editor if it is running, optionally rebuild, relaunch it in the background, wait until ready.
#   usage: ue_relaunch.sh /abs/path/<Project>.uproject [--build] [level-name-substring]
#   env:   UE_ENGINE (default "/Users/Shared/Epic Games/UE_5.9"), UE_MCP_PORT (default 8000)
# macOS has no Live Coding, so every C++ change goes through this.
set -u
UPROJECT="$1"; shift
BUILD=0; LEVEL=""; BACKGROUND=0
for arg in "$@"; do
  case "$arg" in
    --build) BUILD=1 ;;
    --background) BACKGROUND=1 ;;
    *) LEVEL="$arg" ;;
  esac
done
ENGINE="${UE_ENGINE:-/Users/Shared/Epic Games/UE_5.9}"
PORT="${UE_MCP_PORT:-8000}"
NAME="$(basename "$UPROJECT" .uproject)"
DIR="$(cd "$(dirname "$UPROJECT")" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
EDITOR='UnrealEditor.app/Contents/MacOS/UnrealEditor'

if pgrep -f "$EDITOR" >/dev/null; then
  python3 "$HERE/uemcp.py" call EditorToolset.EditorAppToolset.StopPIE '{}' >/dev/null 2>&1
  python3 "$HERE/uemcp.py" call ConsoleToolset.ConsoleToolset.RunConsoleCommand '{"Command":"QUIT_EDITOR"}' >/dev/null 2>&1
  for i in $(seq 1 90); do pgrep -f "$EDITOR" >/dev/null || break; sleep 1; done
  if pgrep -f "$EDITOR" >/dev/null; then
    echo "editor did not quit in 90 s; sending TERM"; pkill -f "$EDITOR"
    for i in $(seq 1 30); do pgrep -f "$EDITOR" >/dev/null || break; sleep 1; done
  fi
fi
pkill -f CrashReportClient 2>/dev/null
# The next editor cannot bind the MCP port until the last one has fully let go of it, and it never
# retries. "Nothing is listening" is not enough: just-closed connections keep the port unbindable for
# a while. So test the real thing, a plain bind, until it succeeds.
for i in $(seq 1 90); do
  python3 -c "import socket,sys; s=socket.socket(); s.bind(('127.0.0.1', int(sys.argv[1]))); s.close()" "$PORT" 2>/dev/null && break
  sleep 1
done
echo "port $PORT free after ${i} s"
rm -rf "$DIR/Saved/Autosaves"   # after a kill, the restore-autosaves prompt is a hidden modal

if [ "$BUILD" = 1 ]; then
  BUILD_LOG="${TMPDIR:-/tmp}/ue-build-$NAME.log"
  (cd "$ENGINE" && ./Engine/Build/BatchFiles/Mac/Build.sh "${NAME}Editor" Mac Development -project="$UPROJECT" -waitmutex) > "$BUILD_LOG" 2>&1
  if ! grep -q 'Result: Succeeded' "$BUILD_LOG"; then
    echo "BUILD FAILED ($BUILD_LOG)"; grep -nE 'error|Result:' "$BUILD_LOG" | head -20; exit 1
  fi
  echo "build ok"
fi

if [ "$BACKGROUND" = 1 ]; then
  open -g -a "$ENGINE/Engine/Binaries/Mac/UnrealEditor.app" --args "$UPROJECT"
else
  open -a "$ENGINE/Engine/Binaries/Mac/UnrealEditor.app" --args "$UPROJECT"
fi
"$HERE/ue_wait.sh" "$NAME" "$LEVEL" 480
