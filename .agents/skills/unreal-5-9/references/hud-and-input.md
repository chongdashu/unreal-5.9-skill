# A menu and HUD on the canvas; keys, pads and touch

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), on 10 and 11 November 2026, while building a small sports game. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

## 1. Drawing on the canvas

A title screen, score plate, call-outs, pause menu and result were drawn from 45 sprites in one `AHUD::DrawHUD`, with no widget assets, and checked without a keyboard (2026-11-10).

- **The HUD canvas is the camera's view, not the viewport.** With a camera constrained to 16:9 in a taller editor viewport, `Canvas->ClipX/ClipY` were the letterboxed 16:9 rectangle, so a layout in a fixed 1920 × 1080 frame scaled by `ClipY / 1080` landed where intended. The mouse is the exception: `GetMousePosition` is in viewport pixels, so subtract `Canvas->SceneView->UnscaledViewRect.Min` before hit-testing.
- **Sprites.** `FCanvasTileItem(TopLeft, Texture->GetResource(), Size, Colour)` with `BlendMode = SE_BLEND_Translucent`, `Rotation = FRotator(0, Degrees, 0)` and `PivotPoint = (0.5, 0.5)` drew straight-alpha sRGB PNGs with the colours of the source. Import them through `unreal.AssetImportTask` (`automated`, `replace_existing`, `save`), then set `compression_settings` to `TC_EDITOR_ICON`, `lod_group` to `TEXTUREGROUP_UI`, `mip_gen_settings` to `TMGS_NO_MIPMAPS` and `never_stream`, and force-save. Stored at twice their 1080p size, they stayed clean at the 1600-wide capture.
- **Text in a real font.** `FCanvasTextItem(Position, Text, FSlateFontInfo, Colour)` only draws when the font info's `FontObject` is a `UFont` (the item casts it; a `UFontFace` or a bare composite font draws nothing).
  - A `.ttf` imports as a `UFontFace` through the same `AssetImportTask`; at run time build a transient `UFont` around it: `FontCacheType = EFontCacheType::Runtime`, then add an `FTypefaceEntry` whose `Font = FFontData(Face)` to `GetMutableInternalCompositeFont().DefaultTypeface.Fonts`.
  - The module needs `SlateCore`. Slate sizes are points at 96 dpi (pixels × 0.75).
  - The canvas ignores a Slate font's outline settings, so draw the words eight times around the fill for a rim.
- **A world position on the HUD.** `Canvas->Project(World)` returns canvas pixels; its `Z` is 0 behind the camera.

## 2. A HUD and menus a probe can read and drive

- **Make the HUD readable by a probe.** Append every sprite's name to a `Showing` string and every plain-text string to a `Written` string as they are drawn, both `VisibleAnywhere`. A probe then asserts "the score plate is up", "the Out call showed" and "nothing was written on screen" from `controller.get_hud().get_editor_property(...)`, and a missing sprite (drawn as a labelled box) fails the same check.
- **Drive menus through the input stack.** Menu navigation was put on the player controller (stick edges step the selection, the game's own buttons choose and back out), so `game.Test.Key "S 1"` exercised it. A string console variable (`game.Test.Mouse "x y"`) stood in for the pointer.
- **Trap: the real mouse joins the probe.** A re-run failed 7 of 16 checks because the pointer was resting on a button in the PIE viewport and kept re-selecting it. Park the stand-in pointer in a corner for the whole run.
- **A pause that keeps the HUD alive.** The game's own pause disables actor tick and sets `CustomTimeDilation = 0` on the ball and the two pawns (so skeletal animation gets no time either) and skips the referee's logic; music, camera and menu animation carry on. Read back: the ball moved 0.00 cm in half a second.

Catching a call-out that lasts under a second in a capture: `capture-and-recording.md`, section 2.

## 3. Gamepads

- **Test a gamepad without one.** `APlayerController::InputKey(FInputKeyEventArgs::CreateSimulated(Key, IE_Axis, Amount, 1))` feeds an analog axis (`Gamepad_LeftX`, `Gamepad_LeftY`, `Gamepad_RightTriggerAxis`) through the same stack as a real pad, and Enhanced Input's `Gamepad_Left2D` mapping, with its dead-zone modifier, sees it: half tilt with a 0.2 dead zone gave 150 of 400 cm/s. Send axis events every frame, as a pad does; buttons are `IE_Pressed` / `IE_Released`. `GetInputAnalogKeyState` and `IsInputKeyDown` read the simulated values too. This proves the game's handling, not that the OS sees a device.
- **Mac controllers in 5.9** go through `AppleControllerInterface` (GameController framework), with `CHHapticEngine` rumble behind `PlayDynamicForceFeedback`. Not tried with hardware here.
- **Asking a pad what it is (Apple systems).** The engine's `FAppleControllerInterface` knows Xbox, DualShock and DualSense but keeps it private, and reports everything as hardware id "Gamepad". Game code can ask the GameController framework itself: a game module's `.cpp` is compiled as Objective-C++ on Mac and iOS, and `ApplicationCore` already links the framework.
  - `[GCController controllers]` gives what is connected with no button pressed; `productCategory` reads "Xbox One", "DualShock 4", "DualSense", "Switch Pro Controller"; `extendedGamepad.buttonA.sfSymbolsName` is the picture the system gives the lower face button.
  - On Mac, `#include "Mac/MacSystemIncludes.h"` before `<GameController/GameController.h>`, or the system's own `FVector` (CarbonCore `NumberFormatting.h`) collides with the engine's: "definition of type 'FVector' conflicts with type alias of the same name".
  - This compiled and ran with no pad connected (count 0); it has not yet had a pad to name.
- **Face buttons are positions, not letters.** `Gamepad_FaceButton_Bottom` is A on Xbox, the cross on PlayStation and B on a Nintendo pad. Bind by position and choose the glyph by pad.
- **Draw prompts as glyph over blank.** One sprite per button per device and a blank chip or card with an empty slot, composed at draw time from a small table, replaced a full set of baked prompt images per device. A debug string of the current glyph for each prompt lets a probe assert "PlayStation shows the cross" without a capture.

Pads in a web build come through the browser and have their own limits: `web.md`, section 4.

## 4. Touch

The owner played an iPhone build and saw keyboard prompts and no way to swing. Fixed in the game's C++ and checked in Play In Editor with simulated fingers. The owner then played that build on an iPhone; what that showed is the safe-area entry below.

- **A phone gets the engine's own touch joysticks unless you turn them off.** `BaseInput.ini` sets `DefaultTouchInterface=/Engine/MobileResources/HUD/DefaultVirtualJoysticks`. On a touch device `APlayerController::CreateTouchInterface` adds that Slate widget over the game; its left stick sends `Gamepad_LeftX/LeftY`, so a game that switches prompts on "pad input arrived" thinks a gamepad is in use. Set `DefaultTouchInterface=None` under `[/Script/Engine.InputSettings]` in `DefaultInput.ini` and call `ActivateTouchInterface(nullptr)` in the controller's `BeginPlay`.
- **Reading fingers without Slate.** `GetInputTouchState(ETouchIndex::Touch1 + n, X, Y, bDown)` each tick, for ten fingers, is enough for a stick and buttons: track which fingers were down last frame to get "landed", give each finger a role when it lands (stick or buttons, by which side of the screen) and keep it until it lifts. Positions are viewport pixels, like the mouse: subtract `Canvas->SceneView->UnscaledViewRect.Min` to get to the HUD canvas.
- **Simulating fingers.** `APlayerController::InputTouch(FTouchId(FInputDeviceId::CreateFromInternalId(0), ETouchIndex::Touch1), ETouchType::Began, ViewportPosition, 1.f, 0)` goes through the same path as a screen (`Moved` and `Ended` likewise), and `GetInputTouchState` then reports it. 5.9 deprecates the overload that takes a device id, a handle and a touchpad index. A string cvar (`game.Test.Touch "finger x y down"`) on top of it let a probe run 23 checks: taps on menu buttons, a dragged stick, two fingers at once, a thumb sliding from one button to another.

## 5. A phone's safe area

- **On a phone the HUD canvas is not the picture.** `UGameViewportClient::Draw` calls `UCanvas::ApplySafeZoneTransform` after setting the canvas up: when the screen has safe-area insets it shrinks `SizeX/SizeY` and `ClipX/ClipY` by whatever part of the insets the picture reaches into and pushes a translation.
  - On an iPhone 15 Pro Max in landscape with a 16:9 picture, only the bottom inset (the home indicator, 42 of 860 pixels) applied: `ClipX x ClipY` was 1529 x 818. A HUD that fits its layout to `ClipX/ClipY` came out 5 percent smaller, pinned to the top, and its full-screen shade and dimming no longer reached the picture's edges, which the owner saw as "a strange dark filter" with the lit scene peeking through.
  - None of it shows on a desktop, where the pads are 0 and the function returns early.
  - Take the picture from `Canvas->SceneView->UnscaledViewRect` and the canvas's real corner from `Canvas->Canvas->GetTransform()` (translation in `M[3][0]`, `M[3][1]`; this accessor already removes the projection, so do not multiply by the inverse of `GetBottomTransform()`, which gave a corner of (902, -237984)).
  - Decide by hand what must stay clear of the inset.
  - `PopSafeZoneTransform` returns early when only the bottom or right pad is set, so popping it inside `DrawHUD` is not safe.
- **Faking a safe-area inset in Play In Editor.** `SafeZone.EnableOverrides 1` with `SafeZone.Ratio.Left 0.9` (also `.Top`, `.Right`, `.Bottom`) insets the HUD canvas, but only when `r.DebugSafeZone.TitleRatio` changes, and the canvas was one change behind: it showed the settings as they were at the change before. Change the ratio two or three times after each edit, and go back through "override on, all ratios 1" before switching the override off, or a stale inset stays. With that, a probe checks "the canvas shrank and the frame is still the whole picture". A bottom inset could not be faked in an editor viewport whose picture does not reach the bottom of the display.
- **The HUD canvas is translated to the letterboxed picture, not clipped to it** (`UGameViewportClient::Draw` pushes a translation by `UnscaledViewRect.Min` before `MyHUD->PostRender`). Read from the engine source, not yet seen: drawing at negative or beyond-`ClipX` positions should land in the black bars, which is where touch buttons can sit on a phone wider than 16:9.
