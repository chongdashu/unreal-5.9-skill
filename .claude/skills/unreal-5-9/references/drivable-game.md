# C++ an agent can drive, and how to check a build

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), from 10 to 17 November 2026, while building two small games: a sports game, then a runner made for a game jam. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

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
- **A fast-forward testing key is global time dilation, switched on only for the stretch it is for.** Run on 5.9.0, 13 November 2026. `UGameplayStatics::SetGlobalTimeDilation(this, 5.f)` while the run is playing, and back to 1 at the cut, sped the run, its camera and its animation together: a 24.6 s take played in 5.0 s of real time with its fixed-step simulation unchanged, and its replay still matched.
  - A fixed-step loop that caps the time it owes per frame (`Min(Debt + Delta, 0.1f)`) must raise the cap by the same factor, or a slow frame silently slows the fast-forward.
  - A probe that times it must use `get_real_time_seconds`: `get_time_seconds` runs dilated, so a wait measured in game seconds ends five times sooner in real time.
  - Pair it with a no-collision flag on the simulation, carried into the replay of that take, and show it on screen, so a take passed this way is never mistaken for one played. Gate the key to `GIsEditor` (or a console variable) so a packaged build's player cannot hit it by accident.
- **Cache the console variables the game reads every frame.** `IConsoleManager::Get().FindConsoleVariable(TEXT("game.X"))` in a tick is a name lookup each time, and the engine logs it: every packaged run printed "shows many (500) FindConsoleObject() calls" six times. Keep a static `TAutoConsoleVariable` or look the pointer up once.
- **A value the game itself writes every tick cannot be set from outside; drive the input it is computed from.** A step that set an effect's strength was dropped because the effects actor wrote that value every frame. The same goes for a look rig writing the camera's lens and a class hiding its actors every frame (`capture-and-recording.md`, section 5; section 2 below).
- **Send a step file's lines through the player's console.** `PlayerController->ConsoleCommand(Line)` reaches the cheat manager and the player's exec chain (`slomo` worked from a step file); `GEngine->Exec` does not reach the player's HUD, so `showhud` from it did nothing. Fall back to `GEngine->Exec` only when there is no player.
- **A tutorial that stops play is a test hook too.** Stop where a control is first needed and resume on that control; give it a console variable that switches it off, on or resets it (`game.Teach 0/1/2`), and have a probe assert each stop's distance (7, 21, 41.7 and 54.5 m in one level). Probes that switch it off must put it back (`editor-python.md`, section 3).
- **A look lab is one more hook.** Numbered look values set through one console variable (`game.Lab.Set <n> <value>`), slots that override constants without a rebuild (`game.Look.Dev`), a dump to JSON and a toggle between renderers let a step file sweep a look in one `-game` run. On macOS every changed C++ constant otherwise means quit, build, relaunch.
- **A fixed seed gives the same match.** With `game.Seed` set before the restart, two recordings of auto-play about 35 minutes and one engine build apart produced the same event log for their first 746 frames, so shot choices by frame number survived a re-shoot.

## 2. Input, shapes and the game mode, built in code

- Enhanced Input built in code in `SetupInputComponent`: `NewObject<UInputAction>`, `NewObject<UInputMappingContext>`, `Mapping->MapKey(Action, Key)`, `UInputModifierSwizzleAxis` / `UInputModifierNegate` / `UInputModifierDeadZone` on the mapping, `BindActionValue` to poll an axis, `AddMappingContext` in `BeginPlay`.
- Engine basic shapes tinted through `UMaterialInstanceDynamic` on `/Engine/BasicShapes/BasicShapeMaterial`, vector parameter `Color`; flag the instance `RF_Transient` so a placed actor does not save it into the level.
- The game mode spawned the pawns, ball and camera at `BeginPlay`, possessed the pawn and set the view target (`bAutoManageActiveCameraTarget = false`); a camera with a constrained 16:9 aspect letterboxes in a non-16:9 viewport.
- **Spawning everything at `BeginPlay` suits a greybox, not a level people open.** The level file stays empty in the editor; lay a real level out as placed actors from a script (`editor-python.md`, section 5).
- **Assets by path, so the greybox level needs none:** `LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/.../SK_X.SK_X"))` at `BeginPlay`, with a fallback when it returns null.

- **A world subsystem adds actors and test hooks to a level without the level's code asking.** Run on 5.9.0, 12 November 2026. A `UTickableWorldSubsystem` in its own file (`DoesSupportWorldType`: game and PIE) spawned two actors on one map and ran a step list from a console variable (`wait`, `until <state>`, `shot <file>`, a run of numbered screenshots, any console command), which is how frames were taken from `-game` runs with no editor.
  - Its `OnWorldBeginPlay` runs before the game mode's `BeginPlay`, so anything read from the game mode there is not set yet: do the work on the first `Tick` where the game mode's own state is filled in.
  - Two sessions could then work on one level's picture at once with neither editing the other's files.
- **To take another class's actors out of the picture without touching that class, switch off what they draw.** `Component->SetVisibility(false)` on an actor's root primitive is separate from `SetActorHiddenInGame`, which the owning class went on calling every frame; destroying the actors instead leaves the owner holding pointers that are nulled at the next collection.

- **The engine's pause stops everything that does not opt in.** With `UGameplayStatics::SetGamePaused`, set `PrimaryActorTick.bTickEvenWhenPaused` on actors that run the pause screen, return true from `IsTickableWhenPaused()` on tickable subsystems, and set `bShouldPerformFullTickWhenPaused` on the player controller so it keeps reading the pause menu's keys. `PlaySound2D` one-shots play on through a pause, because its `bIsUISound` defaults to true (`GameplayStatics.h`, read in the 5.9 source); looping sounds also kept playing, so pause them yourself (`sound.md`).
- **Hand a stand-in over to the real thing with a console variable.** One session's stand-in effects stayed until another session's real ones arrived: the replacing actor set `game.Stage.ShotStandIns 0` when it started and back to 1 when the level ended, so the two never showed together and never left a gap.

## 3. State that must not repeat

- **Key per-shot state on a serial that never repeats.** State keyed on a number that restarts (here the shot's number within a rally) is silently reused the next time that number comes round.
  - In this game the computer player made one plan per `HitCount`; a plan made for hit 4 was reused for the next rally's hit 4, so a missed return of serve was missed again at the next serve.
  - A scripted test that restarts and replays the same shot saw the first plan forever: a new behaviour passed its unit of logic and measured as absent (32 lobs of 32 returned with no hesitation).
  - A counter of every ball put in flight since the level began (`ShotSerial`) fixed both.

- **Test and computer-player runs never write the player's save.** Count a run only after its first real round ends, so the run behind the title screen does not count; a computer player's or a ghost's run never unlocks anything; ownership granted by a test hook lasts one session; and the reset and grant hooks are compiled out of Shipping. Checked with two headless launches that read the save back: counts 1, then 2, and a grant not saved (from the record).

## 4. Soaks: the computer plays thousands of runs

- **Make the simulation fixed-step and seeded, so one console variable plays N runs with no picture and checks each replay.** `game.Soak 500` played 500 seeded runs (2,500 takes) headless, replayed each take and compared: 0 mismatches. The same soak found 40 losses, all with one hazard on.
- **When a soak's number stalls under repeated rule changes, trace one failing run before changing the rule again.** With a new hazard, wins out of 500 went 452, 110, 40, 49 as the rule was rewritten; a step-by-step trace showed the computer player walking back through the hazard's lane, and the next runs gave 91, 178, 412, 399, 450. On a later level, reading where the failed runs died took 1,000 runs from 877 wins to 996, and the fault was the computer player's planning, not the level. Change only the rule at the spot the failures share: one margin widened everywhere cost another hazard (454, 448, then 423).
- **Write the soak's report to a file.** The 1,000-run figures above exist only in a session's reply; nobody can check them now.

## 5. Building and checking C++

- **Compile-check one file while the editor is running.** `Build.sh <Project>Editor Mac Development -project=<uproject> -waitmutex -SingleFile=<absolute path to the .cpp>` ran the header tool and compiled that file in about 6 s, linked nothing, and left the running editor's library untouched: "[1/1] Compile" then "Result: Succeeded".
  - With a wrong path it prints "Target is up to date" and exits 0 having compiled nothing, so check for the Compile line.
  - It compiles the file outside the unity build, which shows missing includes (`member access into incomplete type 'UWorld'` until `Engine/World.h` is included).
  - Any full build compiles every file in the module folder, another session's untracked files included, so check yours this way before anyone else builds.
- **`-SingleFile` finds includes a unity build hides.** The HUD's source file had built for a day while using `FTextureResource` without including `TextureResource.h`; compiled alone it failed with "cannot convert argument of incomplete type 'const FTextureResource *' to 'const FTexture *'".
- `-Werror` rejected `for (TActorIterator<T> It(World); It; ++It) { X = *It; break; }`. Write `TActorIterator<T> It(World); if (It) { X = *It; }`.
- On macOS's case-insensitive disk, a class file named like the module file but for one capital (`FooBar.cpp`, `Foobar.cpp`) overwrote it. Name the module file `<Module>Module.cpp`.
- **Checking a build without the editor.** With another session using the editor, copying `Source/`, `Config/` and the `.uproject` to a scratch folder and running `Build.sh <Project>Editor Mac Development -project=<copy>` there compiled the module ("Result: Succeeded") without touching the running editor's binaries.
- **A rebuilt game module can be ignored by `-game`.** With an editor open on another checkout, `Build.sh <Project>Editor Mac Development` linked `libUnrealEditor-<Module>-0002.dylib`; after a code change it linked `-0003` and left `Binaries/Mac/UnrealEditor.modules` naming `-0002`, so `UnrealEditor-Cmd <uproject> -game` ran the old code without complaint (seen twice). `rm -rf <Project>/Binaries/Mac` before the build, then check the `InternalLoadLibrary` line in the run's log. It bites the editor too, not only `-game`: on 2026-11-12, with a recording editor open on a worktree, a quit, build, relaunch of the main checkout brought the editor back on the previous dylib (`lsof -p <pid> | grep <Module>` named the plain file from 13 minutes earlier while the build had written `-0002`); a probe then "passed" against old code. `scripts/ue_relaunch.sh --build` now removes `Binaries/Mac` before it builds.
- **A headless game run for a check.** `UnrealEditor-Cmd <uproject> -game -nullrhi -nosound -unattended -ExecCmds="..." -abslog=<file>` loaded the level, ran the game mode and played a match with no window and no sound in about 40 s. Its game clock is not the wall's: a match's summed `DeltaSeconds` came to 35 s where `FPlatformTime::Seconds()` measured 19 to 24 s. Time anything you report by the wall clock.

- **Time a simulated key by frames, not by seconds.** A string hook holds one request a frame, so a probe that sets `"Enter 1"`, sleeps 0.06 s and sets `"Enter 0"` loses the press whenever a frame is longer than the sleep. On 2026-11-12 a merge of effects and post-processing took Play In Editor from 25 ms to 50 ms a frame (another editor was recording on the same GPU) and 18 of 29 checks failed with nothing wrong in the game. Wait until `GameplayStatics.get_time_seconds(world)` has changed twice between press and release.

macOS has no Live Coding, so every C++ change is quit, build, relaunch: `setup-and-lifecycle.md`, section 2.
