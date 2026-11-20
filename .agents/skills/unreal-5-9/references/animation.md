# Animation driven from code

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), from 10 to 17 November 2026, while building two small games: a sports game, then a runner made for a game jam. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

No animation blueprint was used. Clips are chosen and blended in a small C++ animation instance, which an agent can read, diff and probe.

## 1. One clip at a time, with a cross-fade

- **A code-driven animation instance compiled and ran first time on 5.9.** A `UAnimInstance` subclass (`UCLASS(Transient, NotBlueprintable)`) overrides `CreateAnimInstanceProxy` and `NativeUpdateAnimation`; its `FAnimInstanceProxy` subclass copies clip pointers and times in `PreUpdate` and, in `Evaluate(FPoseContext&)`, calls `Sequence->GetAnimationPose(FAnimationPoseData, FAnimExtractContext(double Time, false))` for the current clip, the same into a second `FCompactPose` (`SetBoneContainer(&Output.Pose.GetBoneContainer())`, `FBlendedCurve::InitFrom(Output.Curve)`, `UE::Anim::FStackAttributeContainer`) for the previous one, then `FAnimationRuntime::BlendTwoPosesTogetherInPlace` and `NormalizeRotations`.
  - On the component: `SetAnimationMode(EAnimationMode::AnimationBlueprint)` and `SetAnimInstanceClass(...)`.
  - Includes: `Animation/AnimInstanceProxy.h`, `Animation/AnimationPoseData.h`, `Animation/AttributesRuntime.h`, `AnimationRuntime.h`, and `Animation/AnimNodeBase.h` for `FPoseContext` (a unity build hid its absence; a `-SingleFile` compile reported "member access into incomplete type 'FPoseContext'").
- **Keep part of a one-shot clip going round, without a new clip.** A "shout" clip raised a megaphone by frame 9, bellowed three times to frame 32 and dropped it; the speech bubble it went with stayed up for as long as the player read it.
  - A `Hold(From, To)` on the same instance wraps the clip's time back to `From` whenever it passes `To`, after the usual advance; playing a new clip clears it. Run on 5.9, 2026-11-13.
  - Pick the two ends a whole number of the clip's own cycles apart and inside a held pose: the bellow was a sine of 7.5 frames, so frames 11 and 26 (two cycles) joined with no seam.
- **A prop held in a hand: a static mesh component on the hand bone, its offset worked out from the clip without playing it.**
  - `unreal.AnimPoseExtensions.get_anim_pose_at_time(sequence, seconds, unreal.AnimPoseEvaluationOptions())`, then `get_bone_pose(pose, "R_Hand", unreal.AnimPoseSpaces.WORLD)`, gives the bone's component-space transform. It matched Blender's posed bone head for the same frame to 0.1 cm (Unreal's y is Blender's -y). Read-only: safe while someone plays.
  - Choose where the prop should be in component space at that frame, then `unreal.MathLibrary.make_relative_transform(desired, hand)` is its offset from the bone; `compose_transforms(offset, hand)` puts it back as a check.
  - In C++: `NewObject<UStaticMeshComponent>(Actor)`, `SetupAttachment(Actor->GetSkeletalMeshComponent(), TEXT("R_Hand"))` (a bone name works as a socket name; no socket asset, so a re-import cannot remove it), `SetRelativeTransform`, `RegisterComponent`. It hides with its actor. Run on 5.9, 2026-11-13.
  - One offset fits one pose. The megaphone sat right at the mouth on the shout and pointed at the camera when the hand rested on the knee.
- **Probe which clips play.** Give the pawn a `VisibleAnywhere FString CurrentClip` and poll it in a Python loop over 30 seconds of auto-play: every clip the game should call for showed up, on both sides.
- **Probe where a one-shot clip leaves the body, not only its name.** A clip-name check passed for weeks while the knock-down clip laid the character across the obstacle that knocked him down.
  - During Play In Editor, `component.get_socket_location(unreal.Name("Head"))` on the spawned `SkeletalMeshActor` returns the animated bone. Wait in game time (`GameplayStatics.get_time_seconds`) until the clip has played, then compare the head, hips, hands and toes with the obstacle's `get_actor_bounds(False)`. Run on 5.9, 2026-11-13: the replacement clip left the frontmost bone 57 cm short of the obstacle's near face.
  - A knock-back clip can carry its own travel in the hip key, and the actor stays where the game put it. A 0.95 m carry kept the body clear, and nothing popped when the get-up clip started from the same offset.

- **Give each kind of clip its own cross-fade time, and check a fade by a bone's height per frame.** In a runner: 0.06 s into a fall or a shot, 0.08 into a jump, 0.12 into a slide, 0.16 into the run, 0.2 into a get-up and 0.3 into poses and idle; the first clip of a level is not faded. Short into moves that answer a key, longer into poses. The head's height going from 81 to 33 cm over 5 frames as a slide began showed the fade working. A fade that starts in the middle of a fade leaves from whichever clip shows more, so only two poses ever blend; `DeltaSeconds` carries `GlobalAnimRateScale`, so a frozen character holds its fade.
- **Set a knock-down probe's thresholds from the measured pose.** On its back, a big-headed rig's hips sat 33.4 cm up against 21 cm after a forward fall, so the "lying down" guard went from 35 to 50 cm (from the record).
- **When the simulation freezes the player mid-air, let the picture finish the fall.** A fixed-step simulation stopped the player where the fail or the finish happened, and the owner saw him left floating in the air. The presentation now drops him under the same gravity, in the jump pose, until he lands; two new mid-air guards brought the probe to 49 of 49.
- **Play a walking clip at the actor's speed divided by that clip's own foot speed, per clip and per character.** Measured foot speeds differed by clip and by body: 0.69 and 0.474 m/s for a tall extra's walk and walk-carrying, 0.336 and 0.231 for a short one's, so the game plays them 1.7 to 2.1 times as fast. On a short-legged runner, also compare the planted foot's speed with the ground speed: 4.76 m/s against 6.5 (73%) at 30 frames a second shows as sliding.

## 2. Legs that keep stepping under another clip

- **Running legs under any other clip, in that same proxy, without an animation blueprint (2026-11-11).** A swing clip on the whole body planted the feet while the game moved the actor.
  - The fix that ran on 5.9 is a hand-written "layered blend per bone" at the end of `Evaluate`: read the run clip into a second `FCompactPose`; record the upper body's first bone's rotation in component space (multiply local rotations up the chain with `Pose.GetParentBoneIndex`, parent on the left: `Parent * Local`); blend the hip bone's rotation and every bone under it except the upper-body branch toward the run pose (`FTransform::Blend`, walking `Pose.ForEachBoneIndex()`, which visits parents before children, with a flag per bone); then set the upper body's first bone to `ParentComponentRotation.Inverse() * Recorded`.
  - Leave the hip's translation alone. The upper body then keeps the direction and position the top clip gave it, so a paddle still meets the ball, while the legs step.
  - Turning the hips toward the direction of travel is one more quaternion on the hip in component space (`FQuat(FVector::UpVector, Radians) * HipComponentRotation`).
  - Bone lookup in a proxy: `Bones.GetPoseBoneIndexForBoneName(Name)` then `Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Index))`; compare `GetInt()` with `INDEX_NONE` for a missing bone or the root's parent.
  - Drive the weight from the actor's measured speed, not from "a swing is playing", so the legs are continuous across the change of clip.
- **Measure where each clip puts the hips before blending clips from different sources.** The Tripo run preset held the hips 36 cm ahead of the origin while the Blender-made clips sat over it, which no one had seen as a number: it showed as a lurch on starting to run and a snap back when a swing began.
  - `unreal.AnimationLibrary.get_bone_pose_for_time(sequence, bone, seconds, False)` returns a bone's local transform and `find_bone_path_to_root(sequence, bone)` its chain, so composing them (`unreal.MathLibrary.compose_transforms(child, parent)` up the chain) gives component-space positions per clip from Python without playing anything.
  - The game corrects the run clip at read time (add a fixed offset to the hip's translation, measured once in the proxy from the two clips' first frames, with the vertical part removed) and the asset is untouched.

## 3. Turning a head on top of a clip

- **Turn a head on top of a code-driven clip.** Subclass the one-clip proxy and, after the clip is evaluated, rotate the neck and head in the character's own frame: walk `FBoneContainer::GetParentBoneIndex` up from the bone, multiply the parents' local rotations from the root down to get the parent's component-space rotation `P`, then set the bone's local rotation to `P.Inverse() * Delta * P * Local`, where `Delta` is `FRotator(Pitch, Yaw, 0).Quaternion()`. Bone lookup on the animation thread: `Bones.GetPoseBoneIndexForBoneName(Name)`, then `Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Index))`. Half the angle on the neck and half on the head read well; a probe saw every head sweep 53 to 125 degrees over a rally. `USkeletalMeshComponent::GlobalAnimRateScale = 0` freezes such a character (hands moved 0.0 cm while paused).

## 4. Making a hit look like a hit

The owner called them "phantom hits": the ball turned around some way from the paddle.

- **Measure the complaint.** Two debug numbers per hit, written into the event log: how far the ball was from the planned strike point, and how far the drawn paddle face was from it. Before: ball 35 to 77 cm from the paddle. After: paddle 9 cm from the strike point on average.
- **Strike at the clip's contact frame, not at the press.** On the press, predict where the ball will be when the swing gets there (simulate the ball that far ahead), judge timing against that, start the clip, and resolve the hit when the contact frame arrives.
- **The drawn pose trails the game by a frame.** A component transform read during a game-mode tick is last frame's pose. At 42 frames a second and a fast swing that was 40 cm. Strike from the planned point, not the paddle's current transform, and start the clip one frame in.
- **Slow the paddle through contact.** Authoring the swing to whip to just short of the ball in one frame and push through it over two cut the paddle's speed at contact to 6 to 8 cm a frame, so a frame of lag barely shows.
- **Hold the mover still during the swing.** The largest single error was the character still walking for the 0.13 s of the wind-up: up to 60 cm. Holding its own movement and applying only a planned step halved the gap at once.
- **Blend clips to the ball's height.** Three versions of a swing (paddle face at 25, 56 and 109 cm), mixed two at a time by weight in the animation proxy, reach any height between.
- **Carry the ball the last few centimetres** with a visual offset that grows through the wind-up, leaving the simulated ball untouched.

## 5. What the rig allows

Measure what a generated rig can do before authoring clips for it. On the two Tripo characters used here:

- **Count the twist bones before deciding a leg cannot bend.** On Tripo's rig v1.0 the main thigh and calf bones carry no vertices, and Unreal's import warns "Unable to update hull for L_Calf"; that first read here as legs weighted to the foot only. They are not: the twist bones under each limb bone carry the skin (149 to 1,565 vertices each across seven rigs from both games; `L_ThighTwist01` alone had 1,019 on one), and bending `L_Calf` 60 degrees in Blender moved 452 to 971 vertices by more than 1 cm. Knees and elbows bend; author clips that bend them. (Read from the rig files in Blender, 2026-11-17.)
- **The paddle cannot bend at the wrist.**
- **A big-headed figure's arms may not reach its own face; turn the body before changing the prop.** Measure before planning a prop at the mouth: on a 1.2 m Tripo director with a 60 cm head, the arm was 25 cm from shoulder to wrist and the mouth 43 cm from the shoulder (measured on the skinned mesh in Blender).
  - With the torso square on, the hand reached a megaphone's grip only with the megaphone pointing out to his side, which looked odd to the owner.
  - A search over spine twist, lean, head pitch and prop size found the reach in the torso: turning it 42 degrees to bring the right shoulder forward, with the head turned back, put the hand 2.5 cm from the grip of a 0.6-size megaphone held properly at the mouth. Pinning the wrist to the head bone (`r_hand_on`) through the shout kept it there. Run on 5.9, 2026-11-13.
- **Two hands on one prop, on a toy-proportioned rig, need the body turned.** With shoulders 0.59 m apart and arms 0.31 m long, holding a drum gun in both mittens took the body turned 14 degrees, the chest 22 more and the left collarbone swung 30 degrees forward; the left mitten then sat within 1.1 cm of its spot. Compare shoulder width with arm length before promising a two-handed hold.
- **Measure crouch and prone heights before sizing cover.** The same 1.24 m figure crouched to 1.10 to 1.13 m and lay prone at 0.86 m: a big head keeps a crouch tall.
- **Judge a clip preview made outside the engine from the side the game camera is on.** A fall's twist was judged from a preview camera on the hero's left while the game's camera sat 2.6 m to his right, so the twist seemed to do nothing; a fall straight back was hidden behind his hat from the game's view. Author one-shot clips to read from that camera.
- **One forward run clip serves every direction**, on a body turned toward the movement, with the hips turned the rest of the way (section 2). There is no side-step or backpedal clip.
- **A preset clip and a scripted clip can disagree about where the body is** (section 2: the hips 36 cm apart). Read bone positions per clip before mixing sources.
