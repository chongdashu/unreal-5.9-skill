# Editor Python through `execute_python`

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), on 10 and 11 November 2026, while building a small sports game. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

## 1. The tool

Full name: `editor_toolset.toolsets.python_scripting.PythonScriptingTools.execute_python`, argument `{"script": {"content": "<source>"}}`. Siblings: `read_me`, `search_symbols`, `get_symbol`.

## 2. A level script that ends with its receipt

Create and save a level, place actors, end with the receipt:

```python
import json
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MAP = "/Game/Maps/Gym"
if unreal.EditorAssetLibrary.does_asset_exist(MAP):
    levels.load_level(MAP)
else:
    levels.new_level(MAP)
sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 900),
                                    unreal.Rotator(roll=0.0, pitch=-20.0, yaw=-120.0))
sun.set_actor_label("GAME_Sun")
light = sun.get_component_by_class(unreal.DirectionalLightComponent)   # settings live on the component
light.set_editor_property("intensity", 600.0)
court = actors.spawn_actor_from_class(unreal.load_class(None, "/Script/MyGame.GameCourt"), unreal.Vector(0, 0, 0))
json.dumps({"saved": bool(levels.save_current_level())})
```

A project C++ actor class loads with `unreal.load_class(None, "/Script/<Module>.<ClassWithoutPrefix>")`.

## 3. Drive Play In Editor and read it back

Drive Play In Editor and read it back in one script:

```python
import asyncio, json
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()   # None unless PIE runs
mode = unreal.GameplayStatics.get_game_mode(world)
player = mode.get_editor_property("player")              # a VisibleAnywhere UPROPERTY
start = player.get_actor_location()
unreal.SystemLibrary.execute_console_command(world, "game.Test.Key D 1")   # a string cvar; no quotes needed
await asyncio.sleep(0.6)                                  # the game keeps running
end = player.get_actor_location()
unreal.SystemLibrary.execute_console_command(world, "game.Test.Key D 0")
json.dumps({"moved": round(end.y - start.y, 1)})          # 278.1 cm in 0.6 s at 470 cm/s
```

- Enum properties read back as `<RallyState.LIVE: 1>`; compare on the name.
- `unreal.SystemLibrary.get_console_variable_int_value("name")` reads a cvar.
- Wait on a condition with a loop around `await asyncio.sleep(0)`, bounded by `GameplayStatics.get_time_seconds(world)`. Summing `get_world_delta_seconds` per iteration ran out early.
- Time dilation for captures: `unreal.GameplayStatics.set_global_time_dilation(world, 0.25)`.

## 4. What the tool accepts and returns

- **execute_python rejects an `import` inside a function** ("imports must be at the top level of the script"); put every import at the top of the file.
- **What `call_tool` returns inside a script** is a dict, not JSON text. The shape for a capture is in `capture-and-recording.md`, section 5.
- **Python details.** `unreal.Vector.equals` takes no tolerance argument: compare `(a - b).length()`. A `VisibleAnywhere` enum reads as `<MatchPhase.MATCH_OVER: 3>`. `uemcp.py` prints only the first 6,000 characters of a result unless `--max` is raised, and `--media-dir` goes after the subcommand.
- **Python property names drop the `b`.** A C++ `bSeated` is `seated` in `set_editor_property`. Actors have no `rerun_construction_scripts` in Python; properties set after the spawn were picked up when play began.
- **`get_editor_world()` returned `None` while PIE was running.** Guard it before calling methods on it.

## 5. Levels

- **A level's game mode from Python:** `editor_world.get_world_settings().set_editor_property("default_game_mode", unreal.load_class(None, "/Script/<Module>.<Class>"))`.
- **Tags from Python:** `actor.set_editor_property("tags", [unreal.Name("ViewerSubject"), unreal.Name("CH_Player")])`; a C++ `bool bGameCamera` property reads as `game_camera`.
- **`load_level` refuses while another level has unsaved changes.** It raises a script error naming the dirty package. Pass `unsaved_changes_policy=unreal.LevelEditorUnsavedChangesPolicy.DISCARD` (or `SAVE`) only when you know whose change it is. A temporary actor spawned to read a skeleton is enough to dirty the open level.
- **A `load_level` in the first seconds after a relaunch can do nothing**, with no error: the wait script reported ready, the call returned, and the editor stayed on the startup map. Read the open level back before starting PIE.

## 6. A running game

- **Spawning into a running game from Python.** `EditorActorSubsystem` and `EditorLevelLibrary` spawns return `None` during PIE, and `GameplayStatics.begin_deferred_actor_spawn_from_class` / `finish_spawning_actor` are not exposed. The cheat console is: `unreal.SystemLibrary.execute_console_command(world, "summon CameraActor", controller)` spawned a camera in the PIE world, found by comparing `get_all_actors_of_class` before and after. Move it, set its field of view and `constrain_aspect_ratio`, call `controller.set_view_target_with_blend(camera, 0.0)`, and `CaptureGameViewport` shows that view with the real lighting; hand the view back to the game's camera afterwards.
- **Play In Editor in a window of a chosen size cannot be started from Python.** `LevelEditorSubsystem.editor_request_begin_play_with_settings(settings)` is new and takes a copy from `get_play_settings()`, with `new_window_width/height` settable, but the play mode (viewport or new window) is `LastExecutedPlayModeType`, which Python cannot reach, and `unreal.PlayModeType` does not exist.

## 7. Calls that say yes and do nothing

- **`EditorAssetLibrary.delete_asset` said True and deleted nothing.** Six imported textures that nothing referenced were "deleted" twice from Python with Play In Editor stopped; each call returned True, `does_asset_exist` stayed True and the `.uasset` files stayed on disk. They were removed as files, with the editor relaunched afterwards. Read back after any delete.
- More of the same kind: an import that leaves packages unsaved and a re-import that lists only new assets (`import-and-materials.md`), a `load_level` that does nothing in the first seconds after a relaunch (section 5).

## 8. Python with no editor window

`UnrealEditor-Cmd <.uproject> -run=pythonscript -script=<abs .py>` runs a script that changes and saves assets without the editor open. The flags it needs and how it reports are in `packaging.md`, section 1.
