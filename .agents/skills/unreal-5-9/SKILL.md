---
name: unreal-5-9
description: "For projects on Unreal Engine 5.9 (on 5.8 use unreal-5-8). Build and ship a game from an AI agent, through the built-in Unreal MCP plugin. Covers the editor channel (server setup, .mcp.json, the four meta-tools, the execute_python tool, relaunching after C++ changes on macOS), making a game an agent can play and assert on (console-variable test hooks, simulated keys, pads and fingers, probes), importing glTF characters, clips and environments, sockets and materials, animation driven from C++, a canvas menu and HUD, sound, Play In Editor captures and frame-exact footage, several agent sessions on one editor, and packaging for Mac, iOS and the web (Wasm, WebGPU). Use for any agentic Unreal session: unreal mcp, ModelContextProtocol plugin, call_tool, execute_python, PythonScriptingTools, CaptureGameViewport, StartPIE, editor python, PIE screenshot, greybox in Unreal, Tripo or Blender assets into Unreal, UAnimInstance proxy, touch controls and safe area, BuildCookRun, iPhone build, Unreal web build."
metadata:
  short-description: "Field lessons for building and shipping a UE 5.9 game with an agent over Unreal MCP."
  version: 3.1.1
  tested-against:
    unreal-engine: 5.9.0 (changelist 60351404, the launcher's install; Experimental Unreal MCP plugin, tool-search mode). The web build used a source checkout at tag 5.9.0-preview-1.
    os: macOS 26.6, Apple Silicon (M4 Max); an iPhone 15 Pro Max (iOS 26.6); Chrome 157
    date: 2026-11-11 (3.1.0 and 3.1.1, 2026-11-12, renamed the skill, moved the 5.8 pages out and replaced the game's names with stand-ins; nothing was re-run)
  earlier: named unreal-mcp up to 3.0.0. Its 1.0.0, field-tested on UE 5.8 (2026-09-09), is now the separate skill unreal-5-8. Lessons kept from it that were not re-run on 5.9 are marked "5.8"; see references/from-5.8.md.
---

# Unreal MCP on UE 5.9 — field lessons

> **Check the engine version first.** This skill is for UE 5.9. On UE 5.8 use the `unreal-5-8` skill: the Python tool, the capture tool and the helper scripts here do not work there.

Unreal Engine ships an in-process MCP server (plugin `ModelContextProtocol`, shown as "Unreal MCP") that exposes editor toolsets to an agent. This skill is what two real projects paid for: a Unity harbor scene rebuilt in UE 5.8 over MCP, and a small sports game taken on UE 5.9 from a greybox to a dressed, scored match with sound, a menu and HUD, pad and touch controls, and Mac, iPhone and web builds. **It is the lessons layer, not Epic's reference.** When Epic's docs and this skill disagree on a tool's name or arguments, run `describe_tools` on the live server and believe that.

## Where to look

`SKILL.md` is the method and the traps everyone hits. The measured detail is one file per job; open the one for the job in hand.

| Job | File in `references/` |
|---|---|
| A new project, launching, the log, the handshake, `.mcp.json` | `setup-and-lifecycle.md` |
| Writing editor scripts: levels, Play In Editor, readbacks, what Python refuses | `editor-python.md` |
| Test hooks in C++, probes, compile checks, headless runs | `drivable-game.md` |
| Importing `.glb` meshes, characters and clips; sockets; materials; sky | `import-and-materials.md` |
| Animation from C++: cross-fades, legs under a swing, a turning head, hit timing, rig limits | `animation.md` |
| A menu and HUD on the canvas; keys, each kind of pad, touch, a phone's safe area | `hud-and-input.md` |
| Importing sound and checking it from a recording | `sound.md` |
| Captures, exposure, framing, frame rate, frame-exact footage | `capture-and-recording.md` |
| Several agent sessions on one editor and one checkout | `sharing-an-editor.md` |
| A standalone Mac app; building, signing and running on an iPhone | `packaging.md` |
| A web build (Wasm, WebGPU), hosting it, play stats from it | `web.md` |
| Arriving from 5.8, and the 5.8 lessons not yet re-run | `from-5.8.md` (the 5.8 pages themselves are in the `unreal-5-8` skill) |

## Philosophy: a serial channel into a modal, stateful GUI

The editor is one process with one game thread. MCP is a loopback HTTP channel into it; every tool call runs serially on that thread. Nothing about this is a batch pipeline:

- **A responsive server is not proof of a usable editor.** A hidden modal dialog freezes the game thread while HTTP keeps saying hello (5.8). And a running editor is not proof of a server: one that could not bind its port runs happily with no server at all.
- **Return values lie by omission.** Imports return empty lists on success, saves skip silently, edits "succeed" on the wrong asset class (5.8); on 5.9 a delete returned True and deleted nothing. Proof is what you read back: positions, speeds, a rule's verdict, a PNG on disk.
- **Two surfaces, in order of reach.** (1) Shipped toolsets, discovered with `list_toolsets` / `describe_toolsets` / `describe_tools`, called with `call_tool`. (2) `execute_python`: full editor Python with the `unreal` module, top-level `await`, and `call_tool` available inside the script. Most real work is (2). Write your own C++ toolset only for something neither offers.
- **Make the game drivable.** An agent cannot press keys. Give every input a console-variable twin and every measurable state a debug property, and play becomes something you can script and assert on.
- **The editor's picture is one renderer's picture.** The phone and the browser builds here drew without Lumen or Nanite. A look is not done until the packaged build shows it.

**Before touching the editor, ask:**
1. Is Play In Editor running? (Level edits during PIE fail quietly; check `get_game_world()`.)
2. Is the editor actually ready? (Process alive, no "Fatal error" or "unable to bind" in the log, the expected level open.)
3. Will this script be re-run? (Then every create needs an exists-guard, and actors a label prefix to wipe by.)
4. What number or file will prove it worked?
5. Does this change need C++? (On macOS that means quit, build, relaunch: plan to batch them.)
6. Is another session using this editor? (Then say what you are about to do first: `references/sharing-an-editor.md`.)

**Core principles:**
1. **Discover, then reach.** Look for a shipped tool first; do everything else in `execute_python`.
2. **End every script with its receipt.** The last expression is the return value: make it a JSON string of what happened, errors included.
3. **Idempotent by construction.** Load-if-exists before create; label actors with a prefix and wipe-and-rebuild by prefix.
4. **Probe, don't eyeball.** Stage the situation, let it run, read the verdict back. Then look at a frame.
5. **Measure before turning a dial.** Exposure, camera, timing and a complaint about feel are converged by numbers from captures and logs, not by adjectives.

## The order that worked

The 5.9 game was built in this order. Each stage left something a script could check before the next began.

| Stage | What proved it | File |
|---|---|---|
| 1. An editor that answers | `uemcp.py info` names the project; the expected level is open | `setup-and-lifecycle.md` |
| 2. A greybox with test hooks: engine shapes, input built in code, a console variable for every input | simulated keys move the pawn at the expected speed; 12 of 12 staged rule cases; the computer plays both sides | `drivable-game.md`, `editor-python.md` |
| 3. Assets through a test level first, with an orbit viewer | measured scale and facing, every clip listed by the import | `import-and-materials.md` |
| 4. The real level, characters in play, sockets, animation from code | a `CurrentClip` property polled over 30 s of auto-play shows every clip | `animation.md` |
| 5. Feel | two distances logged per hit, before and after | `animation.md`, section 4 |
| 6. Sound | a count of every cue asked for, and a recording with a burst at each logged event | `sound.md` |
| 7. Menu and HUD | every sprite and string drawn is logged to a property a probe reads | `hud-and-input.md` |
| 8. Dressing and a crowd, with several sessions at once | each session's label prefix and folders; announced relaunches | `sharing-an-editor.md` |
| 9. Pads and touch | simulated axes and fingers through the real input stack | `hud-and-input.md` |
| 10. Footage | a frame counter that never skips | `capture-and-recording.md` |
| 11. Packaged builds: Mac, then iPhone, then the web, each in its own worktree | a screenshot and a log from the packaged game | `packaging.md`, `web.md` |

Packaging came late here, and it found three look problems the editor never showed: imported meshes drawn grey in the Mac app, a phone picture the owner called "very dark", and a web page with a flat brown sky and black shade. Run a first packaged build as soon as the level has imported meshes in it.

## Quick start (macOS)

```bash
# 1. Build the editor target (a fresh module compiled in 22 s against the installed engine)
cd "/Users/Shared/Epic Games/UE_5.9" && ./Engine/Build/BatchFiles/Mac/Build.sh <Project>Editor Mac Development \
  -project="/abs/path/<Project>.uproject" -waitmutex
# 2. Launch; the server auto-starts on 127.0.0.1:8000/mcp. Not `open -g`: a background launch leaves the splash on screen
open -a "/Users/Shared/Epic Games/UE_5.9/Engine/Binaries/Mac/UnrealEditor.app" --args "/abs/path/<Project>.uproject"
# 3. Wait properly: this exits early if the editor died or could not bind its port
scripts/ue_wait.sh <Project> [level-name]
# 4. First calls
python3 scripts/uemcp.py info                       # which editor answered: project file, engine version, pid
python3 scripts/uemcp.py py -c 'unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()'
```

The `.uproject` needs `ModelContextProtocol` (on by default), `AllToolsets` and `PythonScriptPlugin` enabled. The very first launch of an engine version on a Mac is slow and silent: about three minutes with no log file and a near-idle process while macOS loads its libraries, then about six more to a ready server. Later launches took 15 to 25 seconds. Project settings, the handshake and `.mcp.json`: `references/setup-and-lifecycle.md`.

## The surfaces

### 1. Shipped toolsets (discover)

`tools/list` shows only the four meta-tools: `list_toolsets`, `describe_toolsets`, `describe_tools`, `call_tool`. `call_tool` takes `toolset_name`, `tool_name` and `arguments` separately. Ones that earned their keep:

| Tool | Used for | Watch out |
|---|---|---|
| `...python_scripting.PythonScriptingTools.execute_python` | everything | call `read_me` once first; see below |
| `EditorToolset.EditorAppToolset.StartPIE` / `StopPIE` | play | `{}` works: in the viewport, 2 s warm-up, 30 s limit |
| `SceneCaptureToolset.SceneCaptureToolset.CaptureGameViewport` | frames of PIE with the HUD | pass **both** arguments, `{"world": null, "maxResolution": 1600}`; omitting `world` is an error although it is described as optional |
| `ConsoleToolset.ConsoleToolset.SetCVarValue` / `GetCVarValue` | driving and reading console variables | works on your own cvars, strings included, while PIE runs |
| `ConsoleToolset.ConsoleToolset.RunConsoleCommand` | `QUIT_EDITOR`, `ModelContextProtocol.GenerateClientConfig ClaudeCode` | refuses any command containing `py` |
| `ConsoleToolset.LogsToolset.GetLogEntries` | reading `print` output (`LogPython`) | |
| `EditorToolset.SkeletalMeshToolset.ImportFile` / `StaticMeshToolset.ImportFile` | importing `.glb` (or `.fbx`) characters, clips and environments | the result lists every asset made, but only what is new on a re-import; `bReplaceExisting` and `bSave` default to false; object positions are baked into the meshes, so place actors at the origin |
| `EditorToolset.SkeletalMeshToolset.AddSocket` / `SetSocketTransform` | attachment sockets | a re-import removes them: add them in the script that imports |
| `EditorToolset.SoundWaveToolset.ImportFile` / `ExportWav` | importing `.flac` or `.wav` as Sound Waves; exporting one to compare with its source | no shipped tool plays or records sound: record the game's output with `unreal.AudioMixerLibrary` (`references/sound.md`) |

A capture is the shape of the editor viewport, not of your camera: a 16:9 constrained camera came back as 1600×1598 with black bars. Crop it (`scripts/crop169.py`). The shipped video recorder does not run on a Mac.

### 2. Editor Python (`execute_python`)

```bash
python3 scripts/uemcp.py py /abs/path/script.py     # or: py -c '<source>'
```

- **The last expression is the result.** A string comes back as it is, anything else as JSON. `print` goes to the Output Log, not to you.
- **`unreal` is pre-imported, each call is a fresh namespace,** and nothing is sandboxed.
- **Top-level `await` works, and the editor keeps ticking while you wait.** `await asyncio.sleep(2)` during PIE lets two seconds of game run, so one script can press a key, wait, and read the result. `asyncio.sleep(0)` can resume more than once per frame: time loops by `GameplayStatics.get_time_seconds(world)`, not by counting iterations.
- **Rejected before running:** imports below the top level, star imports, `time.sleep`, `subprocess.run`, `urllib.request.urlopen`, `requests.*`. Use `asyncio` equivalents.
- **Other tools from inside a script:** `await call_tool('EditorToolset.AssetToolset.ListFolders', rootPath='/Game/')`. The result is a dict.
- **Still true (5.8):** guard creates with `does_asset_exist`; force-save what Python made with `only_if_is_dirty=False`; build `unreal.Rotator` by keyword (`roll=, pitch=, yaw=`); look imports up by path afterwards.

Level setup, PIE probes and readbacks with code: `references/editor-python.md`. Import, material and placement recipes from the 5.8 port: `references/editor-python-patterns.md` in the `unreal-5-8` skill.

### 3. Your own C++ toolset (rarely)

A `UCLASS` deriving `UToolsetDefinition` with static `UFUNCTION(meta=(AICallable))` methods, registered in `StartupModule` with `UToolsetRegistry::RegisterToolsetClass`. The 5.8 port needed one to reach Python; the 5.9 game needed none. The template that compiled on 5.8 is `assets/toolset-template/` in the `unreal-5-8` skill; it has not been rebuilt against 5.9.

## Make the game drivable (C++ patterns that paid off on 5.9)

The `game.` prefix is a stand-in; choose your own.

- **A console-variable twin for every input:** `game.Auto.MoveX`, `game.Auto.Swing` (set, acted on, reset). Reset a consumed cvar from code with `->Set(0, ECVF_SetByConsole)`; a lower priority is ignored after a console set. A consumed string hook holds one request a frame.
- **A key-event hook through the real input stack:** a string cvar `game.Test.Key "W 1"` that calls `APlayerController::InputKey(FInputKeyEventArgs::CreateSimulated(...))`. It proves the Enhanced Input bindings without a keyboard. The same call with `IE_Axis` stands in for a gamepad, and `InputTouch` for fingers.
- **Staging hooks:** `game.Test.Place` and `game.Test.Launch` put a paddler and a ball flight exactly where a rule needs them, so twelve rule cases run in under a minute.
- **A receipt cvar:** `game.DumpPath /abs/file.json` writes the whole game state and a recent event log.
- **A fixed seed:** `game.Seed` made two recordings of auto-play produce the same event log for their first 746 frames.
- **`VisibleAnywhere` debug properties** on the game mode and pawns: `get_editor_property` reads them from the PIE world.
- **Input assets built in code** (`NewObject<UInputAction>`, `MapKey`, modifiers) and **tints through a transient dynamic material** on engine basic shapes: no assets on disk for a greybox.
- **Animate in code.** One clip at a time with a short cross-fade, from a small `UAnimInstance` and proxy, chosen from game state; a `CurrentClip` debug string makes "did the swing clip play?" a probe. `references/animation.md`.
- **A HUD a probe can read.** Menus and HUD drawn on the canvas from sprites, with every sprite and every written string logged to debug properties, and menu input on the player controller so simulated keys drive it. `references/hud-and-input.md`.
- **Prompts and controls per device.** Keys, each kind of gamepad and a touch screen each get their own prompts, and touch its own on-screen controls. Turn off the engine's stock touch joysticks first. `references/hud-and-input.md`.
- **A screenshot hook for packaged builds.** With no editor there is no capture tool: a cvar that requests a screenshot after N seconds, set with `-ExecCmds`, works on a Mac app and on a phone. `references/packaging.md`.
- **Globals are world-agnostic.** A console command bound to a world gets the editor world, not the PIE world; a cvar the game polls reaches whichever world is playing.

Code and the build checks that go with it: `references/drivable-game.md`.

## Verification ladder

1. **Ready:** process alive, no fatal or bind error in the log, `info` names your project, the level you expect is open.
2. **Build:** `Result: Succeeded` in the build log, then a relaunch (macOS). To check one file without disturbing a running editor, `-SingleFile`, and look for the "Compile" line.
3. **Level:** the setup script's receipt lists the actors it placed and `saved: true`.
4. **Input:** simulated keys, pad axes and fingers move the pawn at the expected speed and direction; buttons register.
5. **Rules:** staged cases return the expected verdicts (12 of 12 on the gym).
6. **Soak:** the computer plays both sides; read rally lengths, error distances, frame rate.
7. **Frame:** capture PIE, crop, look at it, and overlay it on the reference when matching a camera.
8. **Motion:** for footage, `t.OverrideFPS 30` and one capture per engine frame, with the frame counter logged.
9. **Packaged:** run the staged build, read its log, take a screenshot from inside the game. Then the device, then the page.

## Editor lifecycle you will hit

| Symptom | Cause | Do |
|---|---|---|
| First launch: no log file, process near idle, for minutes | macOS loading the engine's libraries for the first time | wait; it is not hung (about 9 minutes in total, once) |
| Editor dies 2 s into startup after turning ray tracing on | `r.RayTracing=True` needs `r.SkinCache.CompileShaders=True` | set both in `DefaultEngine.ini` |
| Editor up, every toolset registered, connection refused | `HttpListener unable to bind to 127.0.0.1:8000`. After the previous editor exits, the port stayed unbindable for another 23 s; the new editor tries once and never retries | wait until a plain `bind` on the port succeeds before launching (`scripts/ue_relaunch.sh` does) |
| A splash image stuck at "90%" on a monitor although the editor is loaded | the editor was launched in the background (`open -g`); its splash window is never dismissed | launch in the foreground; relaunch to clear it |
| "Not run: the Unreal Editor is running a slow task" | shaders or assets still compiling | retry until it clears |
| `load_level` returns and the editor stays on the startup map | called in the first seconds after a relaunch | read the open level back before starting PIE |
| `load_level` raises, naming a dirty package | another level has unsaved changes; a temporary actor is enough | save or discard, knowing whose change it is |
| Tools hang with no error (5.8) | a modal: restore-autosaves, or `create_asset` on an existing asset | `rm -rf <Project>/Saved/Autosaves` before relaunching after a kill; guard creates |
| Edits fail or spawns return `None` | PIE is running | `StopPIE` first; to spawn into the running game, `summon` from the console |
| C++ change does nothing | macOS has no Live Coding: `IsLiveCodingReady` stays false | quit, build, relaunch |
| A wait loop sits for 14 minutes | it only polled the port | also check the process and grep the log for `Fatal error` |

The 5.8 table, with its look-dev and import traps: `references/traps.md` in the `unreal-5-8` skill.

## Shipping it

- **Packaging is `RunUAT.sh BuildCookRun`,** and it compiles the editor module too: close the editor on that checkout or work in a worktree. Content the game loads by path string is not cooked unless its folder is listed.
- **Keep the agent plugins out of the game:** `"TargetAllowList": ["Editor"]` on `ModelContextProtocol`, `AllToolsets` and `PythonScriptPlugin`. For a web cook, switch them off in a copy of the project: Epic's guide says the cook fails with them on.
- **Imported meshes are Nanite, and that follows you.** In a packaged Mac game their materials drew grey until given the Nanite usage flag; iOS and the web draw the coarse fallback mesh unless it is raised or Nanite is turned off.
- **iOS from the launcher install is Metal SM5:** no Lumen, Nanite, Virtual Shadow Maps or ray tracing, so shade gets no bounced light. `xcrun devicectl` installs, launches and reads files back without Xcode's window.
- **A web build is a separate engine job.** 5.9's Wasm platform (WebGPU) packaged, hosted and played this game in Chrome, but only from an engine source checkout with Emscripten 6.0.10: the launcher's Mac install refuses the platform. The web gets the mobile renderer, so a Lumen-lit level needs a sky dome, Nanite switched off in the packaged copy, and the sky light's lower half filled with the floor's colour.
- **A HUD fitted to the canvas shrinks on a phone.** The safe area insets the canvas, not the picture. `references/hud-and-input.md`, section 5.

Steps, numbers and traps: `references/packaging.md`, `references/web.md`.

## Anti-patterns to avoid

❌ **Printing `list_toolsets`.** 35 KB into the conversation. Save it to a file and grep the names.

❌ **Running Python through the console tool.** Refused on 5.9. Use `execute_python`.

❌ **Writing a C++ toolset first.** On 5.9 check `execute_python` and the shipped toolsets before adding a module.

❌ **Waiting on the port alone.** A crashed editor and a serverless editor both refuse connections forever.

❌ **Relaunching the instant the editor quits.** The port is still unbindable for a while after the process is gone ("nothing is listening" is not the test; a successful bind is). The new editor then starts with no server and never retries.

❌ **Trusting return values over readbacks.** Read back the thing.

❌ **Signing off a look in the editor only.** The packaged Mac game, the phone and the web page each drew a different picture from the editor's.

❌ **Reading a component's transform to place this frame's event.** It is last frame's pose. Plan the point, strike from the plan.

❌ **Sharing an editor without saying so.** Another session's relaunch or level load lands in the middle of your probe. Announce PIE, level loads and relaunches; name your files. While someone records, make no calls at all, reads included.

❌ **Placing imported props at their export positions.** The importer already baked them in; the prop ends up twice as far out. Everything goes at the origin.

❌ **Reading triangle counts off an imported mesh.** Meshes arrive as Nanite; the count is the simplified fallback. Count in the authoring tool.

❌ **Setting emission on an imported glTF material.** It read back as set and changed nothing on screen. Swap in a project material.

❌ **Mixing clips from two sources unmeasured.** A preset run clip held the hips 36 cm from where the scripted clips put them. Read bone positions per clip first.

❌ **Judging exposure by eye, or by a table.** With manual exposure and a 600 lux sun, a bias of -2 was black (mean luma 0.03) and +3.5 was right (0.41). Measure the capture.

❌ **Comparing frame rates on a busy machine.** The same scene read 12, 37 and 42 to 46 frames a second as other renders finished.

❌ **Counting loop iterations as time.** `asyncio.sleep(0)` is not one frame.

❌ **File names that differ only by case.** On macOS a class file named like the module file but for one capital (`FooBar.cpp`, `Foobar.cpp`) silently overwrote it.

❌ **Break-on-first-match loops in C++.** The build's `-Werror` rejects them (`-Wunreachable-code-loop-increment`).

❌ **OS-level screen grabs as a fallback (5.8).** They grab another window. Stay on the MCP path.

❌ **Applying a critic's numbers verbatim (5.8).** Direction, then measure.

## Variation guidance

Sessions differ; do not converge on one shape.

- **Greybox vs. port:** a greybox wants code-built geometry, cvar hooks and rule probes; a port wants import scripts, bounds and triangle readbacks, and a look-dev loop.
- **Which surface:** a one-off read or a setting belongs in a shipped tool call; anything that creates, places, stages or measures belongs in a Python script that ends with its receipt.
- **Assets:** author at real scale in Blender (metres, Z up, characters facing +X), export `.glb`, import with the shipped tools, and build a small test level with an orbit viewer before anything goes near gameplay. `references/import-and-materials.md` has the measured behaviour.
- **Capture plan:** `CaptureGameViewport` for PIE with the HUD; a fixed camera actor for repeatable comparison frames; a summoned camera for any other view of the running game; exact frames for footage. `references/capture-and-recording.md`.
- **C++ vs. Blueprint:** both projects chose C++ so the agent can read, diff and test the logic. Choose Blueprint only where a human will iterate visually.
- **One target or several:** a desktop-only game can lean on Lumen and Nanite. One that will also run on a phone or in a browser needs its light and meshes to hold up on the mobile renderer, so decide the targets before the look.
- **Look-dev:** findings on sky, cloud sea, fog, outlines and flat meshes under Lumen are from the 5.8 port: `references/lookdev-and-gameplay.md` in the `unreal-5-8` skill.

## Keeping these notes

- **A lesson goes in the file for its job,** under the section it belongs to, not at the end of the newest file.
- **Lead with the rule, then what happened.** The first sentence should make sense to someone who has never seen this game; the numbers follow as the evidence.
  - Leave the project out of it: write `game.` and `MyGame` for its console variables, classes and content folders, and do not point at its scripts or docs.
- **Say how it was checked:** run on 5.9, read in the engine source, or not yet tried. Give the number that was measured.
- **Correct, don't append.** When a later run overturns an entry, change the entry.
- **On a branch, merge often.** Notes written in a worktree are invisible to the other sessions until then.
  - A branch cut before 2026-11-12 still has this skill as `unreal-mcp` with one notes file; `references/ue59-notes.md` says how to merge it.
- **Keep the long entries broken up:** a lead sentence, then sub-points.

## Files

- `scripts/uemcp.py` — the MCP client: `info`, `tools`, `toolsets`, `describe`, `call`, `py`, `raw`. Saves image results to disk.
- `scripts/ue_wait.sh`, `scripts/ue_relaunch.sh` — wait for a ready editor; quit, optionally build, relaunch.
- `scripts/crop169.py` — crop a capture to 16:9 and report its mean luminance.
- `scripts/ue_script_template.py` — a re-runnable editor script that ends with its receipt.
- `references/` — one file per job: the table under "Where to look".
- `references/from-5.8.md` — what changed from 5.8, and which 5.8 lessons were not re-run. The 5.8 pages, helpers and C++ toolset template are the `unreal-5-8` skill.
- `references/ue59-notes.md` — a stub that says where each section of the old single notes file went.

## Remember

The editor will tell you it did something it did not do, keep answering while it is frozen, and keep running with no server at all. Reach for Python, end every script with its receipt, make the game drivable so play can be asserted on, read the result back, and run the packaged build before believing the picture. Done that way, an agent took an Unreal game from a rule-checked greybox to a phone and a web page.
