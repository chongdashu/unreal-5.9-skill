# Coming from UE 5.8

This skill began as `unreal-mcp` 1.0.0, field-tested on UE 5.8 (2026-09-09) by rebuilding a Unity harbor scene over MCP. That version is kept, as it was tested, as the separate skill `unreal-5-8`: use it for a project that is on 5.8. This page is for someone arriving on 5.9 with 5.8 habits, and for the 5.8 lessons that have not been run again.

## What changed from 5.8 to 5.9 (all checked on a live 5.9 editor)

| 5.8 lesson | 5.9 |
|---|---|
| Three meta-tools, `describe_toolset` | Four: `list_toolsets`, `describe_toolsets`, `describe_tools`, `call_tool` |
| 52 toolsets | About 106 with the `AllToolsets` plugin; `list_toolsets` returns 35 KB of text, so never print it raw |
| Write a C++ toolset to reach `py` through a console command | Not needed. `editor_toolset.toolsets.python_scripting.PythonScriptingTools.execute_python` runs full editor Python and returns the script's last expression |
| `ExecConsoleCommand("py ...")` | The shipped `ConsoleToolset.ConsoleToolset.RunConsoleCommand` **refuses any command containing `py`** and points at the Python tool |
| A custom tool to write a screenshot to disk | `SceneCaptureToolset.SceneCaptureToolset.CaptureGameViewport` returns a PNG; decode it to disk yourself (`scripts/uemcp.py` does) |
| A blocked editor still answers | Still true for modals. For slow tasks 5.9 now replies "Not run: the Unreal Editor is running a slow task..." and changes nothing |
| Hand-write `.mcp.json` | Console command `ModelContextProtocol.GenerateClientConfig ClaudeCode` writes it into the Unreal project folder |
| Python toolsets `SceneTools`, `StaticMeshTools`, `ProgrammaticToolset` | Gone. The editor toolsets are C++ now (`EditorToolset.ActorToolset`, `.AssetToolset`, `.LevelToolset`, `.EditorAppToolset`...) |
| A -90 degree yaw fix on imported characters (FBX) | Not needed through glTF: Blender +X arrives as Unreal +X (`import-and-materials.md`) |

## 5.8 lessons not run again on 5.9

Treat these as likely but unconfirmed, and read a tool's schema for units before trusting a coordinate:

- FBX import (glTF was used on 5.9 instead).
- The metres-versus-centimetres split between tools.
- The restore-autosaves and overwrite modals that hang every tool call.
- The `MarkAsGarbage` crash.
- Everything in the 5.8 skill's `lookdev-and-gameplay.md` except the C++ gameplay patterns in its section 2: sky, cloud sea, fog, outlines, flat meshes under Lumen, the critique loop.

Since confirmed on 5.9, so no longer on this list: building a material graph from Python (`import-and-materials.md`, section 4), and the C++ gameplay patterns (`drivable-game.md`).

## The 5.8 pages, read from 5.9

They are in the `unreal-5-8` skill (`.claude/skills/unreal-5-8/`), as field-tested apart from the small fixes its front matter lists. What 5.9 changed on each:

- `references/setup-and-toolset.md` — project configuration, the wire protocol by hand, the shape of a C++ toolset.
  - Wrong on 5.9: there are four meta-tools (`describe_toolsets`, `describe_tools`) and about 106 toolsets.
  - Wrong on 5.9: the settings section is `[/Script/ModelContextProtocol.ModelContextProtocolSettings]`.
  - Wrong on 5.9: the Python toolsets listed in its section 4 are gone, and `ExecConsoleCommand("py ...")` is replaced by the shipped `execute_python` tool.
  - The C++ toolset in its section 5 is no longer needed to get started. Use `setup-and-lifecycle.md` first; keep that page for the C++ toolset shape and the renderer settings.
- `references/editor-python-patterns.md` — script skeleton, FBX import, placement and units, animation notifies, look-dev objects.
  - On 5.9 run scripts through `execute_python`, not a console `py` command, and end a script with its result as the last expression rather than a receipt file and log sentinel (`editor-python.md`).
  - Its editor-viewport frames go through a custom `SaveViewportScreenshot` tool; on 5.9 use `CaptureGameViewport`.
  - The import, material, placement and notify recipes were not re-run on 5.9 (`import-and-materials.md` has what was).
- `references/lookdev-and-gameplay.md` — look-dev findings under Lumen, C++ gameplay patterns, the critique loop.
  - Not re-run on 5.9, except the C++ gameplay patterns in its section 2 (console-variable twins, debug properties, input built in code), which were used again and held (`drivable-game.md`).
- `references/traps.md` — symptom, cause, fix.
  - The 5.9 traps (silent first launch, port unbindable after a quit, ray tracing fatal error, no Live Coding on macOS, the capture tool's required arguments, the `py` console refusal) are in this skill's `SKILL.md` and `setup-and-lifecycle.md`.
  - Its `execute_tool_script` and custom-toolset rows no longer apply on 5.9. The rest was not re-run.
- `assets/toolset-template/` — the C++ toolset that compiled on 5.8. Not rebuilt against 5.9, where the shipped Python tool made it unnecessary.
- `scripts/mcp.sh`, `scripts/cap.sh` — the 5.8 command-line helpers. On 5.9 `scripts/uemcp.py` here replaces the first, and `CaptureGameViewport` replaces the custom tool the second calls. `uemcp.py` was never run against 5.8.
