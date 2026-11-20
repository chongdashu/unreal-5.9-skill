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

**A probe leaves the editor as it found it.** Run on 5.9 on a Mac, 12 to 15 November 2026, with the owner playing in the same editor between probes.

- **Stop only the game you started, refuse one you did not, and put back every console variable you set, in a `finally`.** One probe that ended without `StopPIE` left a game running with the computer playing; the next refused to start, and the session looked like a person's. Console variables outlive the play session: probes that set `game.Teach 0` to skip the tutorial left it at 0, and the owner's next play had no tutorial and was reported as a bug. Five probes had each pasted the same restore step on their last line, where an exception skipped it. Read each variable at the start (`SystemLibrary.get_console_variable_int_value` / `_float_` / `_string_`) and restore in `finally`, with the open level.
- **When the owner reports something missing, read the shared editor's switches first.** The tutorial stops had passed in the probe at every distance; the owner's play had none because a probe had left the switch off.
- **Load your own level.** A probe that relied on the editor's startup map had been failing since another session changed that map; once it loaded its level, it passed 18 of 18.
- **Fetch the play world again after the game changes level.** The old world is torn down by the travel, and a probe timing frames on it broke.
- **Wait on a named game phase with a timeout, never a fixed sleep.** A 0.5 s sleep before checking an opening beat broke the evening a new intro was added; a wait on the HUD's state with a 1.5 s limit replaced it.
- **Write the receipt to a file under the project's ignored output folder as well as returning it.** Several records could cite only "the session's report" for a soak's counts, so nobody could check them later.

## 4. What the tool accepts and returns

- **execute_python rejects an `import` inside a function** ("imports must be at the top level of the script"); put every import at the top of the file.
- **What `call_tool` returns inside a script** is a dict, not JSON text. The shape for a capture is in `capture-and-recording.md`, section 5.
- **Python details.** `unreal.Vector.equals` takes no tolerance argument: compare `(a - b).length()`. A `VisibleAnywhere` enum reads as `<MatchPhase.MATCH_OVER: 3>`. `uemcp.py` prints only the first 6,000 characters of a result unless `--max` is raised, and `--media-dir` goes after the subcommand.
- **Python property names drop the `b`.** A C++ `bSeated` is `seated` in `set_editor_property`. Actors have no `rerun_construction_scripts` in Python; properties set after the spawn were picked up when play began.
- **`get_editor_world()` returned `None` while PIE was running.** Guard it before calling methods on it.
- **`unreal.GameplayStatics.project_world_to_screen(controller, location, False)` returned the `Vector2D` alone,** not a tuple with the bool (5.9, 2026-11-13): indexing it raised "'Vector2D' object is not subscriptable". Read `.x` and `.y`; off screen shows as zero or negative.

## 5. Levels

- **A level's game mode from Python:** `editor_world.get_world_settings().set_editor_property("default_game_mode", unreal.load_class(None, "/Script/<Module>.<Class>"))`.
- **Tags from Python:** `actor.set_editor_property("tags", [unreal.Name("ViewerSubject"), unreal.Name("CH_Player")])`; a C++ `bool bGameCamera` property reads as `game_camera`.
- **`load_level` refuses while another level has unsaved changes.** It raises a script error naming the dirty package. Pass `unsaved_changes_policy=unreal.LevelEditorUnsavedChangesPolicy.DISCARD` (or `SAVE`) only when you know whose change it is. A temporary actor spawned to read a skeleton is enough to dirty the open level.
- **Lay out a level people will open as placed actors, from a re-runnable script.** A game mode that spawns the whole set at `BeginPlay` (fine for a greybox) leaves the level file empty: the owner opened the maps and found them blank, with nothing whose visibility could be toggled. A script that placed the set's 341 objects from the floor plan, wiping by label prefix, fixed it, and the level could then be looked at and toggled without playing.
- **A `load_level` in the first seconds after a relaunch can do nothing**, with no error: the wait script reported ready, the call returned, and the editor stayed on the startup map. Read the open level back before starting PIE.

## 6. A running game

- **Spawning into a running game from Python.** `EditorActorSubsystem` and `EditorLevelLibrary` spawns return `None` during PIE, and `GameplayStatics.begin_deferred_actor_spawn_from_class` / `finish_spawning_actor` are not exposed. The cheat console is: `unreal.SystemLibrary.execute_console_command(world, "summon CameraActor", controller)` spawned a camera in the PIE world, found by comparing `get_all_actors_of_class` before and after. Move it, set its field of view and `constrain_aspect_ratio`, call `controller.set_view_target_with_blend(camera, 0.0)`, and `CaptureGameViewport` shows that view with the real lighting; hand the view back to the game's camera afterwards.
- **Play In Editor in a window of a chosen size cannot be started from Python.** `LevelEditorSubsystem.editor_request_begin_play_with_settings(settings)` is new and takes a copy from `get_play_settings()`, with `new_window_width/height` settable, but the play mode (viewport or new window) is `LastExecutedPlayModeType`, which Python cannot reach, and `unreal.PlayModeType` does not exist.

## 7. Calls that say yes and do nothing

- **`EditorAssetLibrary.delete_asset` said True and deleted nothing.** Six imported textures that nothing referenced were "deleted" twice from Python with Play In Editor stopped; each call returned True, `does_asset_exist` stayed True and the `.uasset` files stayed on disk. They were removed as files, with the editor relaunched afterwards. Read back after any delete.
- More of the same kind: an import that leaves packages unsaved and a re-import that lists only new assets (`import-and-materials.md`), a `load_level` that does nothing in the first seconds after a relaunch (section 5).

- **A texture read straight after the editor starts can report a 32 px stand-in.** `blueprint_get_size_x()` on a 1024 px UI texture returned 32 in the first seconds after a relaunch, while the texture was still being built, and 1024 a minute later; the import's own receipt had said 1024. A probe that checks a texture's size waits and reads again while the answer is 32. Seen on 5.9, 2026-11-12.

## 8. Python with no editor window

`UnrealEditor-Cmd <.uproject> -run=pythonscript -script=<abs .py>` runs a script that changes and saves assets without the editor open. The flags it needs and how it reports are in `packaging.md`, section 1.
