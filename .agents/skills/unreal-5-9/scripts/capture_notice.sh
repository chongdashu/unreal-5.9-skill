#!/bin/zsh
# Tell whoever is at the Mac that an agent's game capture or check is running off screen: a macOS notification,
# which does not take focus. At most one every few minutes, however many runs follow each other, and from any
# session: the window is shared through one stamp file.
#   usage: capture_notice.sh "what is running" [title]
#   env:   UE_NOTICE_STAMP (default $TMPDIR/ue-capture-notice), UE_NOTICE_GAP seconds (default 180)
# Call it from every capture or check runner, before the game starts. A game project ran this as its own script
# (the owner had asked "is there a way to at least indicate that a capture is running"); this general form was
# checked with zsh -n only.
STAMP="${UE_NOTICE_STAMP:-${TMPDIR:-/tmp}/ue-capture-notice}"
GAP="${UE_NOTICE_GAP:-180}"
NOW=$(date +%s)
if [ -f "$STAMP" ] && [ $((NOW - $(cat "$STAMP" 2>/dev/null || echo 0))) -lt "$GAP" ]; then
  exit 0
fi
echo "$NOW" > "$STAMP"
osascript - "${1:-A game capture is running}" "${2:-Game capture running}" <<'EOF' >/dev/null 2>&1 || true
on run argv
  display notification (item 1 of argv) with title (item 2 of argv) subtitle "Off screen, no window: your mouse stays free"
end run
EOF
