# C++ an agent can drive, and how to check a build

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), on 10 and 11 November 2026, while building a small sports game. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

An agent cannot press keys or watch a match. These are the hooks that let scripts play the game and read what happened, all compiled and run on 5.9.

## 1. Console-variable hooks

```cpp
// A consumed test hook. Reset with SetByConsole priority, or the reset is ignored after a console set.
static TAutoConsoleVariable<int32> CVarAutoSwing(TEXT("game.Auto.Swing"), 0, TEXT("1 = drive, 2 = dink. Consumed."));
if (const int32 Swing = CVarAutoSwing.GetValueOnGameThread())
{
    CVarAutoSwing.AsVariable()->Set(0, ECVF_SetByConsole);
    // ... act
}

// A key event through the real input stack, from a string cvar "W 1" / "W 0".
InputKey(FInputKeyEventArgs::CreateSimulated(FKey(FName(*KeyName)), bDown ? IE_Pressed : IE_Released, bDown ? 1.f : 0.f));
```

- **A consumed string hook holds one request.** A hook that is read and cleared once a frame keeps only the last value set in that frame. Two sets of `game.Test.Place` in one frame (the player, then the rival) left the player unmoved, and four checks failed for a reason that had nothing to do with what they tested. Wait a frame (`await asyncio.sleep(0.05)`) between sets of the same hook, or give the hook a list.
- **A reaction every actor shares, from one console variable.** Each actor polls a string variable; whichever ticks first copies it into a file-level value with a serial number and clears the variable, and every actor compares the serial with the one it last acted on. Set an actor's serial to the current one in `BeginPlay`, or a reaction forced in one play session fires again at the start of the next (the statics outlive PIE).
- **A fixed seed gives the same match.** With `game.Seed` set before the restart, two recordings of auto-play about 35 minutes and one engine build apart produced the same event log for their first 746 frames, so shot choices by frame number survived a re-shoot.

## 2. Input, shapes and the game mode, built in code

- Enhanced Input built in code in `SetupInputComponent`: `NewObject<UInputAction>`, `NewObject<UInputMappingContext>`, `Mapping->MapKey(Action, Key)`, `UInputModifierSwizzleAxis` / `UInputModifierNegate` / `UInputModifierDeadZone` on the mapping, `BindActionValue` to poll an axis, `AddMappingContext` in `BeginPlay`.
- Engine basic shapes tinted through `UMaterialInstanceDynamic` on `/Engine/BasicShapes/BasicShapeMaterial`, vector parameter `Color`; flag the instance `RF_Transient` so a placed actor does not save it into the level.
- The game mode spawned the pawns, ball and camera at `BeginPlay`, possessed the pawn and set the view target (`bAutoManageActiveCameraTarget = false`); a camera with a constrained 16:9 aspect letterboxes in a non-16:9 viewport.
- **Assets by path, so the greybox level needs none:** `LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/.../SK_X.SK_X"))` at `BeginPlay`, with a fallback when it returns null.

## 3. State that must not repeat

- **Key per-shot state on a serial that never repeats.** State keyed on a number that restarts (here the shot's number within a rally) is silently reused the next time that number comes round.
  - In this game the computer player made one plan per `HitCount`; a plan made for hit 4 was reused for the next rally's hit 4, so a missed return of serve was missed again at the next serve.
  - A scripted test that restarts and replays the same shot saw the first plan forever: a new behaviour passed its unit of logic and measured as absent (32 lobs of 32 returned with no hesitation).
  - A counter of every ball put in flight since the level began (`ShotSerial`) fixed both.

## 4. Building and checking C++

- **Compile-check one file while the editor is running.** `Build.sh <Project>Editor Mac Development -project=<uproject> -waitmutex -SingleFile=<absolute path to the .cpp>` ran the header tool and compiled that file in about 6 s, linked nothing, and left the running editor's library untouched: "[1/1] Compile" then "Result: Succeeded".
  - With a wrong path it prints "Target is up to date" and exits 0 having compiled nothing, so check for the Compile line.
  - It compiles the file outside the unity build, which shows missing includes (`member access into incomplete type 'UWorld'` until `Engine/World.h` is included).
  - Any full build compiles every file in the module folder, another session's untracked files included, so check yours this way before anyone else builds.
- **`-SingleFile` finds includes a unity build hides.** The HUD's source file had built for a day while using `FTextureResource` without including `TextureResource.h`; compiled alone it failed with "cannot convert argument of incomplete type 'const FTextureResource *' to 'const FTexture *'".
- `-Werror` rejected `for (TActorIterator<T> It(World); It; ++It) { X = *It; break; }`. Write `TActorIterator<T> It(World); if (It) { X = *It; }`.
- On macOS's case-insensitive disk, a class file named like the module file but for one capital (`FooBar.cpp`, `Foobar.cpp`) overwrote it. Name the module file `<Module>Module.cpp`.
- **Checking a build without the editor.** With another session using the editor, copying `Source/`, `Config/` and the `.uproject` to a scratch folder and running `Build.sh <Project>Editor Mac Development -project=<copy>` there compiled the module ("Result: Succeeded") without touching the running editor's binaries.
- **A rebuilt game module can be ignored by `-game`.** With an editor open on another checkout, `Build.sh <Project>Editor Mac Development` linked `libUnrealEditor-<Module>-0002.dylib`; after a code change it linked `-0003` and left `Binaries/Mac/UnrealEditor.modules` naming `-0002`, so `UnrealEditor-Cmd <uproject> -game` ran the old code without complaint (seen twice). `rm -rf <Project>/Binaries/Mac` before the build, then check the `InternalLoadLibrary` line in the run's log.
- **A headless game run for a check.** `UnrealEditor-Cmd <uproject> -game -nullrhi -nosound -unattended -ExecCmds="..." -abslog=<file>` loaded the level, ran the game mode and played a match with no window and no sound in about 40 s. Its game clock is not the wall's: a match's summed `DeltaSeconds` came to 35 s where `FPlatformTime::Seconds()` measured 19 to 24 s. Time anything you report by the wall clock.

macOS has no Live Coding, so every C++ change is quit, build, relaunch: `setup-and-lifecycle.md`, section 2.
