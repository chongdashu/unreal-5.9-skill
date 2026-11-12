# Animation driven from code

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), on 10 and 11 November 2026, while building a small sports game. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

No animation blueprint was used. Clips are chosen and blended in a small C++ animation instance, which an agent can read, diff and probe.

## 1. One clip at a time, with a cross-fade

- **A code-driven animation instance compiled and ran first time on 5.9.** A `UAnimInstance` subclass (`UCLASS(Transient, NotBlueprintable)`) overrides `CreateAnimInstanceProxy` and `NativeUpdateAnimation`; its `FAnimInstanceProxy` subclass copies clip pointers and times in `PreUpdate` and, in `Evaluate(FPoseContext&)`, calls `Sequence->GetAnimationPose(FAnimationPoseData, FAnimExtractContext(double Time, false))` for the current clip, the same into a second `FCompactPose` (`SetBoneContainer(&Output.Pose.GetBoneContainer())`, `FBlendedCurve::InitFrom(Output.Curve)`, `UE::Anim::FStackAttributeContainer`) for the previous one, then `FAnimationRuntime::BlendTwoPosesTogetherInPlace` and `NormalizeRotations`.
  - On the component: `SetAnimationMode(EAnimationMode::AnimationBlueprint)` and `SetAnimInstanceClass(...)`.
  - Includes: `Animation/AnimInstanceProxy.h`, `Animation/AnimationPoseData.h`, `Animation/AttributesRuntime.h`, `AnimationRuntime.h`, and `Animation/AnimNodeBase.h` for `FPoseContext` (a unity build hid its absence; a `-SingleFile` compile reported "member access into incomplete type 'FPoseContext'").
- **Probe which clips play.** Give the pawn a `VisibleAnywhere FString CurrentClip` and poll it in a Python loop over 30 seconds of auto-play: every clip the game should call for showed up, on both sides.

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

- **The legs do not bend at the knee.** Each leg's skin is weighted to its foot bone only; the thigh and calf bones move nothing. Unreal's import warning "Unable to update hull for L_Calf" comes from the same cause.
- **The paddle cannot bend at the wrist.**
- **One forward run clip serves every direction**, on a body turned toward the movement, with the hips turned the rest of the way (section 2). There is no side-step or backpedal clip.
- **A preset clip and a scripted clip can disagree about where the body is** (section 2: the hips 36 cm apart). Read bone positions per clip before mixing sources.
