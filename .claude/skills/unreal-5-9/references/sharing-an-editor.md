# Several agent sessions on one editor and one checkout

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), on 10 and 11 November 2026, while building a small sports game. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

Up to five sessions worked in the same folder against the same running editor. Tool calls are serial, but Play In Editor, the open level, a relaunch and the files on disk are shared state.

## 1. The editor

- **One editor, several agent sessions.** Tool calls are serial, but Play In Editor, the open level and a relaunch are shared state. What worked: say which files and content folders are yours, never rewrite a shared source file whole, commit with explicit pathspecs, and announce every quit-build-relaunch and every stretch of PIE before starting it.
- **Queue the editor like a lock.** With four sessions, each asked for it by message, said what it needed (PIE or PIE-stopped, minutes, whether it saves a level), and passed it on by name. Files on disk are the build: say "compiles as it stands" before someone else relaunches.
- **Sharing the editor.** Sessions told each other, by message, before every PIE start, level save and relaunch, and named the folders each owned; one relaunch carried two sessions' C++. A level script that removes only its own label prefix (`DRESS_`, against the base script's `GAME_`) let a second session dress the same level without the first one's script undoing it.
- **A read-only MCP call during someone else's capture is still a suspect.** A take ended three seconds after another session's one-line status poll; a later uninterrupted run cleared it, but the rule since is no MCP calls at all, reads included, while another session records.

A level with unsaved changes blocks the next `load_level`, and a temporary actor is enough to dirty it: `editor-python.md`, section 5. A take lost with two possible causes, one of them another session's poll: `capture-and-recording.md`, section 5.

## 2. The build

- **Files on disk are the build.** A full build compiles every file in the module folder, another session's untracked files included. Compile-check your own file alone first, or build a copy in a scratch folder: `drivable-game.md`, section 4.
- **One relaunch can carry several sessions' C++.** Say "compiles as it stands" before someone else relaunches.

## 3. A worktree for platform work

Packaging compiles the editor module and cooks for minutes, so it cannot share a checkout with a running editor (`packaging.md`, section 1). Here the Mac and iOS packaging, the web build and the play-stats work each ran in their own Git worktree on their own branch, and the editor stayed on the main checkout. Notes written on such a branch reach the others only when it is merged: merge often, or the skill forks.

## 4. Commits

Commit only your own paths, through a private index when another session may be staging (`GIT_INDEX_FILE`, then `commit-tree` and `update-ref HEAD <new> <old>`).
