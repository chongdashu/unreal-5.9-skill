# Project setup, launching, and the wire protocol

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), on 10 and 11 November 2026, while building a small sports game. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

## 1. Project setup

`.uproject` plugins:

```json
"Plugins": [
  { "Name": "ModelContextProtocol", "Enabled": true },
  { "Name": "AllToolsets", "Enabled": true },
  { "Name": "PythonScriptPlugin", "Enabled": true }
]
```

- `ModelContextProtocol` is enabled by default; `AllToolsets` and `ToolsetRegistry` are not (source). `AllToolsets` pulls in about 40 toolset plugins (source).
- Targets from the 5.9 blank template: `DefaultBuildSettings = BuildSettingsVersion.V8`, `IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_9`. `EngineAssociation` is `"5.9"`.
- Server settings class is `UModelContextProtocolSettings`, section `[/Script/ModelContextProtocol.ModelContextProtocolSettings]` (not `...ProtocolEngine...` as on 5.8). `bAutoStartServer=True` already comes from the engine's `BaseEditorPerProjectUserSettings.ini`, so a new project needs no server config. Other settings (source): `ServerPortNumber`, `ServerUrlPath`, `AdditionalAllowedOrigins`, `MaximumProtocolVersion`, `bEnableToolSearch`, `bDumpMediaToDisk`, `Instructions`.
- Keep Play In Editor at full rate while the editor is in the background, in `Config/DefaultEditorSettings.ini`:

```ini
[/Script/UnrealEd.EditorPerformanceSettings]
bThrottleCPUWhenNotForeground=False
```

  With it, PIE held 120 frames a second while the editor was launched with `open -g` and never focused. The run without it was not measured.

- Hardware ray tracing, in `Config/DefaultEngine.ini`. The second line is mandatory: without it the editor dies two seconds into startup with `Fatal error: [RenderUtils.cpp:1143] Ray tracing requires skin cache to be enabled`:

```ini
[/Script/Engine.RendererSettings]
r.RayTracing=True
r.SkinCache.CompileShaders=True
```

  On the M4 Max the log then reads `Ray tracing is enabled.` and `Ray tracing shaders are enabled.`, `r.Lumen.HardwareRayTracing` reads 1, and a greybox scene stayed at 120 frames a second.

- Set `EditorStartupMap` and `GameDefaultMap` only after the level exists.
- The editor adds an `[/Script/AndroidFileServerEditor.AndroidFileServerRuntimeSettings]` section with a generated `SecurityToken` to `DefaultEngine.ini` on first run. Look at the file before committing it.

- **The editor rewrites `DefaultEngine.ini`** with an Android file-server section (including a generated token) on every launch until the `AndroidFileServer` plugin is disabled in the `.uproject`.

- **Keep the agent plugins out of a packaged game.** They have Runtime modules; `packaging.md` has the `.uproject` setting, and `web.md` why a web cook needs them switched off altogether.

## 2. Launch timings and the log

- Mac log: `~/Library/Logs/Unreal Engine/<Project>Editor/<Project>.log`.
- First launch of this engine on the machine: 3 minutes before the log file existed (process at about 3 MB and 0 percent CPU, stuck in the dynamic loader), then 6 minutes to the server. For a while after that, tool calls were refused with "running a slow task".
- Every later launch: 15 to 25 seconds to a ready server with the level open.
- First build of a new module: 22 seconds.
- Ready lines: `LogModelContextProtocol: Tool search enabled: registered 4 meta-tools (N toolsets discoverable via list_toolsets)`, repeated as toolsets register (N climbed from 4 to 27 in the log; `list_toolsets` later returned about 106 toolsets).
- Launch in the foreground. With `open -g` (background) the editor loaded and worked, but its splash window (720 × 370, reading 90 percent) stayed on screen for the whole session; the user found it on a second monitor. The same editor relaunched with plain `open -a` left only the main window. `scripts/ue_relaunch.sh` launches in the foreground unless given `--background`.
- Failure lines to grep for: `Fatal error`, `HttpListener unable to bind to 127.0.0.1:8000`.
- After a healthy editor quit, the port stayed unbindable for 23 seconds after the process was gone. Launching inside that window gives an editor with no server. Test with a plain bind:

```bash
python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 8000))"
```

- `QUIT_EDITOR` through `RunConsoleCommand` quits cleanly when nothing is unsaved. Check first:

```python
dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() + unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
str([p.get_name() for p in dirty])
```

- macOS has no Live Coding: `LiveCodingToolset.LiveCodingToolset.IsLiveCodingReady` stayed false after `EnableLiveCoding`. Every C++ change is quit, build, relaunch. A relaunch alone took 46 seconds with `scripts/ue_relaunch.sh`: 23 waiting for the port, 15 for the editor.

## 3. The wire protocol

- `initialize` with `protocolVersion: "2025-06-18"`, headers `Accept: application/json, text/event-stream` and a loopback `Origin`; the reply carries an `Mcp-Session-Id` header that later calls must send.
- The `initialize` result names the editor that answered, under `_meta["com.epicgames.unrealengine/instance"]`: `processId`, `engineVersion`, `projectName`, `projectFile`, `projectDirectory`. Use it when several editors may be open.
- `tools/list` returns four tools:
  - `list_toolsets {}`
  - `describe_toolsets { toolset_names: [..], include_schemas: bool }`
  - `describe_tools { tool_names: ["Toolset.Tool", ..] }` (full schemas; long)
  - `call_tool { toolset_name, tool_name, arguments }`
- A tool's text result is JSON of the form `{"returnValue": ...}`. Images arrive as separate `image` content blocks (base64 PNG).
- Claude Code config: console command `ModelContextProtocol.GenerateClientConfig ClaudeCode` wrote `<Unreal project folder>/.mcp.json`:

```json
{ "mcpServers": { "unreal-mcp": { "type": "http", "url": "http://127.0.0.1:8000/mcp" } } }
```

  If the agent session runs from a parent folder, copy the file there.

## 4. Epic's own agent skills

5.9 ships skills as Python modules in `Engine/Plugins/Experimental/Toolsets/EditorToolset/Content/Python/editor_toolset/skills/` ; a `ToolsetRegistry.AgentSkillToolset` is registered alongside (not exercised here). Worth reading before lighting work: `default_outdoor_lighting.py` (sunset sun 300 to 1,000 lux, height fog 0.000002 to 0.00002, read and set light properties on the component, check cloud coverage before blaming sky colour, at most three screenshot cycles). Its exposure table did not match manual exposure here; see the exposure table in `capture-and-recording.md`.
