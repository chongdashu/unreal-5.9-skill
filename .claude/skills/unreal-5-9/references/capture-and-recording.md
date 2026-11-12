# Play In Editor, captures, exposure, and recording footage

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), on 10 and 11 November 2026, while building a small sports game. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

## 1. Play and capture

- `EditorToolset.EditorAppToolset.StartPIE {}`: in the viewport, 2 s warm-up, 30 s limit. Options (`bSimulate`, `playMode`, `startTransform`, `warmupSeconds`) go in an `options` object. `StopPIE {}` errors if nothing is running.
- `SceneCaptureToolset.SceneCaptureToolset.CaptureGameViewport {"world": null, "maxResolution": 1600}` captures PIE with the HUD drawn. `ListWorlds {}` shows the editor and PIE worlds (`/Game/Maps/UEDPIE_0_<Map>`).
- Capture rate over MCP: 130 frames at 960 px in 41.7 s, about 3 a second. With time dilation 0.25 that is 12.5 frames per second of game time: enough for a watchable clip, encoded with `ffmpeg -framerate 12.5`.

- **Capture shape changes between launches.** After a relaunch the viewport was wider than 16:9 where before it was squarer, so the black bars moved from top and bottom to the sides. Crop by comparing the two ratios (`scripts/crop169.py` does); a crop that assumes one case silently keeps the bars.
- **Sharp captures:** set the post-process volume's motion blur amount to 0, or a paused frame of a fast clip is smeared.
- **`SceneCaptureToolset.Capture` is not a look review.** The offscreen capture from an arbitrary camera (`world={"refPath": "/Game/Maps/UEDPIE_0_<Map>.<Map>"}`, `camera={location, rotation, fOV}`, `mode="Lit"`, `options={width, height}`) has no temporal history: the same scene came back blown out, with black shadows. Use it for geometry and framing only.

## 2. Catching a moment

- **Freeze a moment to capture it.** A call-out that lasts under a second cannot be caught by `CaptureGameViewport` on demand. From a script, poll for it (`await asyncio.sleep(0)` in a loop), then `unreal.GameplayStatics.set_game_paused(world, True)`: world time stops, the HUD keeps drawing, and the capture can be taken by the next call. `slomo 0.3` widens the window; `game.Test.Launch` stages the ball that causes the call.

## 3. Exposure and framing

- Exposure. With default auto exposure and a 600 lux sun the first capture was washed out. An unbound `PostProcessVolume` with manual exposure fixed it, converged by measuring the mean luminance of the cropped capture:

| `auto_exposure_bias` (manual) | Mean luma |
|---|---|
| -2.0 | 0.03 |
| 1.5 | 0.16 |
| 2.5 | 0.26 |
| 3.5 | 0.41 |

```python
grade = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
grade.set_editor_property("unbound", True)
settings = grade.get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_method", True)
settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 3.5)
grade.set_editor_property("settings", settings)   # write the struct back
```

- Fixed exposure for the sunset level, by measuring captures: bias 3.25 gave mean luma 0.39, 3.45 gave 0.42, 3.6 gave 0.54.
- Matching a camera to a reference image: derive a first guess from the reference (where the near and far court edges sit in the frame gives distance, height, pitch and field of view), capture, then blend the reference over the capture at 50 percent. The gym's first guess (height 418 cm, pitch 13.2 degrees, horizontal field of view 34 degrees, 1080 cm behind the baseline) needed no second pass.
- **Field of view.** A camera's field of view is horizontal for a 16:9 frame, and the engine keeps that frame's vertical angle. In a squarer viewport the view is narrower than the number suggests: frame subjects by the vertical half-angle, `atan(tan(fov/2) * 9/16)`.
- **Floors and horizons.** A basic-shape cylinder scaled to 3 km rendered unlit black; at 40 m it lit normally. Past the edge of any floor the view below the horizon is black unless the level has height fog.

## 4. Frame rate

- **Cost of the real scene.** The greybox gym ran at the editor's 120 frames a second; the dressed level with 20 Nanite meshes, two skinned characters and hardware ray tracing ran at 64 to 68; with volumetric cloud and haze, about 42.
- **Frame rate is only comparable on a quiet machine.** The same scene read 12 frames per second while four Blender renders and a video encode ran, 37 a minute later, and 42 to 46 once they had finished. Count frames yourself (`SystemLibrary.get_frame_count()` over game time) and check `ps` for other renderers before blaming your change.

## 5. Recording footage: exact frames, moving cameras

Verified on 5.9.0 on a Mac while recording two trailers (2,430 frames over 14 takes, none skipped). The recorder was one project script run through `uemcp.py py`; a shell script and a list of takes re-ran a whole shoot in one go.

- **The shipped video recorder does not run on a Mac.** `SceneCaptureToolset.SceneCaptureToolset.StartViewportRecording` (and `RecordViewport`) fail with "Video recording is not supported on Mac: it needs Windows Media Foundation." Their schema is otherwise what you would want (`source: GameViewport`, `maxResolution`, `frameRate`, an MP4 under `/Saved/Recordings`); not tested on Windows.
- **Exact 30 frames a second from stills.** Set `t.OverrideFPS 30`: every engine frame then advances the game by exactly 1/30 s whatever the real frame time is. In one `execute_python` script, wait for `unreal.SystemLibrary.get_frame_count()` to change, then `await call_tool("SceneCaptureToolset.SceneCaptureToolset.CaptureGameViewport", world=None, maxResolution=1920)`. The capture finished inside the frame it was asked in: the frame counter read the same before and after on every one of 2,430 captures. Log the frame number and `GameplayStatics.get_time_seconds` per capture; a skipped frame would show as a step of 2.
- **What `call_tool` returns inside a script:** a dict, not JSON text. For the capture it is `{"image": {"mimeType": "image/png", "data": <base64>}, "width", "height", "metadata", "warnings"}`; write `base64.b64decode(result["image"]["data"])` to disk from the script. `ListWorlds` comes back as `{"returnValue": [...]}`.
- **Speed and size.** About 4 captures a second at 1803 x 1608 (about 2 while a video render ran on the same machine). `t.MaxFPS 12` was set so the engine did not run ahead; it was not needed for correctness. The image is the viewport's shape: crop the centred 16:9 (1802 x 1014 here) and scale. Put `t.OverrideFPS` and `t.MaxFPS` back to 0 in a `finally`; if Play In Editor dies mid-take the script cannot, so reset them with `ConsoleToolset.SetCVarValue`.
- **Sounds for the footage.** Stepped footage has no usable live sound. The game's event log gives each hit and bounce a game time; with a fixed step, frame = (event time - first frame's time) x 30 + 1, so the game's own sound files can be laid on the right frame afterwards. Fifteen hits placed this way measured 40 to 60 ms after their picture frame, which is one frame of intended delay plus each file's attack.
- **A camera for a take.** `summon CameraActor` from the player controller spawns into the play world (the editor's spawn calls refuse during play); set `constrain_aspect_ratio` and `aspect_ratio` on its component, `set_view_target_with_blend(camera, 0.0)`, and give the view back to the game's camera afterwards. For a crane, orbit or tilt, call `set_actor_location_and_rotation` once per captured frame with the pose for that frame. Scout with one low-resolution still per candidate camera before recording: three of twelve first guesses had to be moved or dropped (two side cameras sat in the umpire's chair, one was too close to the scoreboard).
- **`showhud`** toggles the whole HUD for clean shots; it is a toggle, so send it again afterwards.
- **Another screen shape without a build.** To see the game at a phone's upright shape, set the game camera's `aspect_ratio` from Python during Play In Editor (`mode.gym_camera.get_component_by_class(unreal.CameraComponent).set_editor_property("aspect_ratio", 9 / 19.5)`, with `constrain_aspect_ratio` already on). The viewport pillarboxes to that shape with the game's real rendering and temporal history, which the offscreen `Capture` tool does not give; crop the centred `height x aspect` strip from `CaptureGameViewport`. `FieldOfView` stays horizontal, so a 34 degree camera at 9:19.5 sees about 67 degrees vertically: the court needs a higher, steeper camera, not the landscape one turned. A script that changes camera console variables on a paused game must let it tick before pausing again, or every capture is the previous camera (three identical stills here).
- **A take can still be lost.** One Play In Editor session ended 28 frames into a take with no `StopPIE` in the log. A click into the game window had happened 14 s earlier and another session's read-only poll 3 s earlier; the cause was not established. Tell every session to stay off the editor, reads included, and the owner not to click into it.

A fixed seed makes a recorded match repeat frame for frame: `drivable-game.md`, section 1.
