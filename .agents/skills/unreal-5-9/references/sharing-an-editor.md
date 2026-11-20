# Several agent sessions on one editor and one checkout

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), from 10 to 17 November 2026, while building two small games: a sports game, then a runner made for a game jam. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

Up to five sessions worked in the same folder against the same running editor. Tool calls are serial, but Play In Editor, the open level, a relaunch and the files on disk are shared state.

The owner is one of the users. In a second game (12 to 17 November 2026) the owner played in the editor the agents drove and worked in other apps while their runs went, and the corrections they had to make most often were about this, not about the engine: their mouse or front window taken three times, and an agent's action landing in their play four times (a relaunch, a second editor window, probes that left a switch off, a probe that left a game running).

## 1. The editor

- **Play In Editor you did not start is the owner's. Never stop it, quit the editor or load a level under it without saying so first.** On 12 November 2026 an agent relaunched the editor for a settings change 19 seconds into the owner's first play of a test level; the owner reported "the gym crashed after completing". The log showed no crash, only the agent's own `StopPIE` and `QUIT_EDITOR`. `scripts/ue_relaunch.sh` now refuses while a play session is running unless given `--force`. While the owner is about to look at something, do work that does not touch the editor.
- **Tag every play session an agent starts, and make every "is someone playing?" check read the tag.** A guard that only asks whether a play world exists took another session's probe for the owner and waited; neither session could tell who had started play. Put a tag on the game mode actor when a script starts play, as the recorder below does.
- **Never run another session's generator or build script as a "check".** It writes its outputs: running a font session's atlas builder to see whether it still worked rewrote the glyph table in the game and the atlas image, which had to be restored from Git.
- **One editor, several agent sessions.** Tool calls are serial, but Play In Editor, the open level and a relaunch are shared state. What worked: say which files and content folders are yours, never rewrite a shared source file whole, commit with explicit pathspecs, and announce every quit-build-relaunch and every stretch of PIE before starting it.
- **Queue the editor like a lock.** With four sessions, each asked for it by message, said what it needed (PIE or PIE-stopped, minutes, whether it saves a level), and passed it on by name. Files on disk are the build: say "compiles as it stands" before someone else relaunches.
- **Sharing the editor.** Sessions told each other, by message, before every PIE start, level save and relaunch, and named the folders each owned; one relaunch carried two sessions' C++. A level script that removes only its own label prefix (`DRESS_`, against the base script's `GAME_`) let a second session dress the same level without the first one's script undoing it.
- **A probe's Play In Editor must not lock the owner's mouse, and anything typed into the editor reaches it.** Run on 5.9.0 on a Mac, 13 November 2026.
  - The game's own `SetInputMode(FInputModeGameOnly())` in the player controller's `BeginPlay` locks the cursor to the viewport every time a probe starts play; the owner asked for background runs to stop capturing their mouse. In the editor (`GIsEditor`), use `FInputModeGameAndUI` with `SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock)` and `SetHideCursorDuringCapture(false)`. Off-screen `-game` runs need the same treatment, keyed on `-RenderOffScreen` (`capture-and-recording.md`, section 5); keep game-only for a packaged build a player starts.
  - Keys pressed while the editor is in front go to the probe's game: a testing key toggled three times in one second (logged by the game) during a sound probe ran a take five times too fast and failed one check; the re-run passed. A relaunch with `open -a` brings the editor to the front, so say so before one, and log every testing key the game acts on, so a stray key shows up in the log.
- **A read-only MCP call during someone else's capture is still a suspect.** A take ended three seconds after another session's one-line status poll; a later uninterrupted run cleared it, but the rule since is no MCP calls at all, reads included, while another session records.

- **A second editor on the same project needs the owner told first, and its own port and process name.** Run on 5.9.0 on a Mac, 12 November 2026, to record footage of an older commit from a worktree while the owner and another session used the main editor.
  - The port: `ServerPortNumber=8010` under `[/Script/ModelContextProtocol.ModelContextProtocolSettings]` in the copy's `Config/DefaultEditorPerProjectUserSettings.ini`; point the client at it with `UE_MCP_URL`. `bThrottleCPUWhenNotForeground=False` under `[/Script/UnrealEd.EditorPerformanceSettings]` in the same file keeps it drawing at full rate behind other windows.
  - The process: `ue_relaunch.sh` and `ue_wait.sh` find "the" editor with `pgrep -f UnrealEditor.app/Contents/MacOS/UnrealEditor`; a second one makes a relaunch wait 90 s and then kill both. Starting the binary with another `argv[0]` (`( exec -a MyGameBrollEditor ".../UnrealEditor.app/Contents/MacOS/UnrealEditor" /abs/copy/MyGame.uproject -abslog=/abs/log & )`) hid it from both scripts and the editor ran normally. `-abslog` keeps its log apart from the main editor's.
  - What went wrong: the two windows are identical, both titled with the project's name. Four seconds after the second one opened, the owner closed the main editor by hand, taking it for a duplicate, and played in the old build for several minutes without knowing. Nothing on screen says which checkout a window belongs to. Say in chat before launching, wait for the owner to be between play sessions, and put a toast in the new editor (`EditorAppToolset.ShowNotification`, `expireDuration` in seconds) saying which one it is.
  - Play In Editor that someone else started in your editor is still theirs: the recorder used here tags the game mode of each session it starts (`tags` on the game mode actor) and refuses to stop one without the tag.

- **An editor with no window is a second editor nobody can mistake for the first.** Run on 5.9.0 on a Mac, 12 November 2026, from a worktree, to re-import two characters with the editor's own import tool while the owner and another session used the main editor.
  - `( exec -a MyGamePolishEditor ".../UnrealEditor.app/Contents/MacOS/UnrealEditor" /abs/copy/MyGame.uproject -RenderOffScreen -nosplash -unattended -nosound -ModelContextProtocolPort=18464 -abslog=/abs/log & )`, the client pointed at it with `UE_MCP_URL`. Nothing appeared on screen, `info` named the worktree's project, the import ran and saved, and `QUIT_EDITOR` closed it.
  - For the first half minute every tool call came back "Not run: the Unreal Editor is running a slow task": ask again every few seconds until the script runs.
  - `-game` runs from the editor binary match the main checkout's `pgrep` for "the editor" too; none was killed here, but giving them their own `argv[0]` the same way costs nothing.

A level with unsaved changes blocks the next `load_level`, and a temporary actor is enough to dirty it: `editor-python.md`, section 5. A take lost with two possible causes, one of them another session's poll: `capture-and-recording.md`, section 5.

## 2. The build

- **Files on disk are the build.** A full build compiles every file in the module folder, another session's untracked files included. Compile-check your own file alone first, or build a copy in a scratch folder: `drivable-game.md`, section 5.
- **One relaunch can carry several sessions' C++.** Say "compiles as it stands" before someone else relaunches.
- **Only one Unreal Build Tool runs per engine install.** `Build.sh ... -waitmutex` waits for it; `RunUAT.sh BuildCookRun` does not. A package started while another session's editor build held the lock failed at once with `ConflictingInstance` in the UBT log, which AutomationTool reported as `ExitCode=10 (Error_SDKNotFound)`. Retry after a minute rather than chasing the SDK.

## 3. A worktree for platform work

Packaging compiles the editor module and cooks for minutes, so it cannot share a checkout with a running editor (`packaging.md`, section 1). Here the Mac and iOS packaging, the web build and the play-stats work each ran in their own Git worktree on their own branch, and the editor stayed on the main checkout. Notes written on such a branch reach the others only when it is merged: merge often, or the skill forks.

## 4. Commits

Commit only your own paths, through a private index when another session may be staging (`GIT_INDEX_FILE`, then `commit-tree` and `update-ref HEAD <new> <old>`).
