# Importing meshes, characters and clips; sockets; materials

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), from 10 to 17 November 2026, while building two small games: a sports game, then a runner made for a game jam. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

## 1. The shipped import tools

Both shipped import tools worked first time on `.glb` files exported from Blender 5.2:

```bash
python3 scripts/uemcp.py call EditorToolset.SkeletalMeshToolset.ImportFile \
  '{"folderPath":"/Game/MyGame/Characters/CH_Player","assetName":"SK_CH_Player","sourceFile":"/abs/CH_Player.glb","bReplaceExisting":true,"bSave":true}'
python3 scripts/uemcp.py call EditorToolset.StaticMeshToolset.ImportFile \
  '{"folderPath":"/Game/MyGame/Environment","assetName":"ENV_Level","sourceFile":"/abs/ENV_Level.glb","bCombineMeshes":false,"bReplaceExisting":true,"bSave":true}'
```

- **The call returns what it made.** Unlike the 5.8 import task, the result lists every asset: for the character, the skeletal mesh, skeleton, physics asset, one material instance, three textures and five animation sequences; for the environment, 20 static meshes and 18 materials. `bReplaceExisting` and `bSave` default to false.
- **Folders and names.** The importer adds a folder named after the file's scene (`.../CH_Player/CH_Player/`) and under it `SkeletalMeshes`, `StaticMeshes`, `Materials`, `Textures`. Clips are named `<assetName><ClipName>` (`SK_CH_PlayerRun`); static meshes keep their object names.
- **Scale and axes through glTF.** Import scale is 1.0: a 13.4112 m court measured 1341.2 cm. Blender +X arrives as Unreal +X and Blender +Y as Unreal -Y, so a character modelled facing Blender +X faces forward with no yaw fix, and left stays left. (The 5.8 port's -90 degree fix was for its FBX pipeline; FBX was not imported here.)
- **Positions are baked into the meshes.** With `bCombineMeshes` false each object becomes its own static mesh, but its scene position is baked into the vertices and its pivot is the scene origin. Place every actor at 0, 0, 0. Placing a prop at its export position as well put it twice as far out.
- **Everything came in as Nanite.** `nanite_settings.enabled` was true on all 20 meshes, so `get_num_triangles(0)` reports the simplified fallback (19,613 in total for a scene built with 48,842).
- **Clips from Blender:** one NLA track per clip and the glTF exporter's `export_animation_mode="NLA_TRACKS"` gave five separate, correctly named sequences.
- **Reading a skeleton from Python:** `component.get_socket_location(unreal.Name("L_Hand"))` on a placed `SkeletalMeshActor` works for bones in the editor; toe minus foot gives the facing, and which side the left hand is on confirms nothing was mirrored.

## 2. Re-imports and replacing one mesh

- **A re-import's result lists only what it made anew.** The second `SkeletalMeshToolset.ImportFile` of the same file returned the meshes and clips but not the material that already existed, so a script that took the material's path from the result found none. Look assets up by path.
- **An import can leave packages unsaved even with `bSave` true.** After `StaticMeshToolset.ImportFile` of a 26-mesh file, 22 material packages were dirty. Check `EditorLoadingAndSavingUtils.get_dirty_content_packages()` and save your own before anyone relaunches the editor.
- **Replace one mesh of a multi-mesh import.** Export a GLB holding only that object, named like the original file (the folder under `folderPath` comes from the file's name), and import it with `assetName` set to the mesh's own name: a single-mesh file takes the asset name it is given, not the object's. Given the scene's name instead, the importer made a second mesh of that name and left the old one in place. Existing materials are kept as they were, so copy changed colours across from the file's JSON. The other meshes, and material swaps made on them, were untouched.
- **Replacing a mesh marks the open level dirty.** Nothing in the level changed, but the next quit would ask to save it. `LevelEditorSubsystem.load_level(path, unsaved_changes_policy=LevelEditorUnsavedChangesPolicy.DISCARD)` put it back; it refuses, returning False, while PIE runs.

- **A glTF re-import puts the importer's settings back.** Texture filtering and mipmaps return to their defaults and Nanite is switched on again on every mesh, so an import script must set them again after each run, not once by hand.
- **A batch import with `replace_existing` rewrites every asset it touches, changed or not.** A UI import of 57 PNGs, 2 of them new, left all 57 `.uasset` files modified in version control though 55 sources were unchanged (5.9, 2026-11-13). Import only new or changed files, or restore the untouched ones from version control before committing.

## 3. Sockets and attaching

- **Sockets with the shipped tools.** `GetSocketNames {mesh}`, `AddSocket {mesh, socketName, boneName}` and `SetSocketTransform {mesh, socketName, translation{x,y,z}, rotation{pitch,yaw,roll}}` all worked from a script through `await call_tool(...)`, with the mesh passed as `{"refPath": mesh.get_path_name()}`. Save the mesh afterwards.
- **Working out a socket from the skeleton.** Spawn a temporary `SkeletalMeshActor`, read bones with `component.get_socket_transform(unreal.Name("R_Hand"), unreal.RelativeTransformSpace.RTS_COMPONENT)`, build the wanted transform with `unreal.MathLibrary.make_rot_from_xz(along_forearm, palm_normal)`, and convert it with `unreal.MathLibrary.make_relative_transform(wanted, hand_bone)`. The paddle then pointed exactly along the direction the Blender pose had asked for.
- **A re-import replaces the skeletal mesh and its sockets.** Put the socket back in the same script that imports.
- **Attaching a prop:** `AttachToComponent(Character, FAttachmentTransformRules::SnapToTargetNotIncludingScale, TEXT("PaddleSocket"))`.

## 4. Materials

- glTF materials import as instances of `/InterchangeAssets/gltf/MaterialInstances/MI_Default_Opaque_DS`; their colour is the vector `BaseColorFactor`, emission is `EmissiveFactor` and the scalar `EmissiveStrength` (an exported strength of 12 arrived as 4).
- **The glTF importer's material ignored emissive here.** On material instances of `/InterchangeAssets/gltf/M_Default` (the parent of everything a `.glb` import makes), setting `EmissiveFactor` and `EmissiveStrength`, even to 20,000, changed nothing on screen, in or out of PIE, although the values read back as set. Bulbs and lit windows authored with emission in Blender did not glow either.
  - A project material made with `MaterialEditingLibrary` (a colour, a roughness, and a glow colour times a strength into Emissive), instanced per imported material and swapped onto the mesh's slots with `mesh.set_material(index, instance)`, did: at this level's manual exposure a strength of 15 to 70 lifted shaded faraway walls into haze and 500 to 900 read as a lit bulb.
  - Measure a box of the capture before and after; cloud shadow and a drifting sun moved the same box by 10 levels with nothing changed.
- A material graph built with `MaterialEditingLibrary` (`create_material_expression`, `connect_material_expressions`, `connect_material_property`, `recompile_material`) worked on 5.9, including a `MaterialExpressionCustom` node driving World Position Offset. `unreal.CustomInput(input_name=...)` raises; construct it empty and `set_editor_property("input_name", ...)`. Set the world-position node to `WPT_EXCLUDE_ALL_SHADER_OFFSETS` when it feeds an offset.
- **Outfits without new characters.** A material instance whose parent is the imported glTF material and whose `BaseColorTexture` is swapped gave twelve outfits on two bodies; the textures were repainted offline by drawing the mesh's UV triangles into a position map and classifying texels by height on the body and colour. PNGs came in through `unreal.AssetImportTask` as sRGB.

- **Blend colours in linear RGB, not in HSV.** A blend from a warm to a cool colour through HSV went through purple.

## 5. Sky

- `VolumetricCloud` uses `/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst`; duplicate it into the project and set `Cloud_GlobalCoverage`, `Cloud_GlobalDensity` (scalars) on the copy. Its wind is the vector `Layout_WindControls`, default (1, 1, 0.5, 0.333).

## 6. Props that carry game state

- **Numbers on a prop, as meshes.** Ten numerals made from the game's font in Blender (a FONT curve converted with `bpy.data.meshes.new_from_object`, stood up to face +X), imported as ten static meshes and swapped on four components by an actor that reads the score, gave a scoreboard a probe can check (`shown_player`, `shown_rival`, a flip count) with no text rendering, font asset or widget.

## 7. Nanite after import

Every imported static mesh is Nanite (section 1). That is free in the editor and costs something on every other target: materials need a usage flag before a packaged Mac game draws them (`packaging.md`), and iOS and the web draw the coarse fallback mesh unless the fallback is raised or Nanite is turned off (`ios.md`, section 4; `web.md`).

## 8. Effects and a lens made by script

Run on 5.9.0 on a Mac, 12 November 2026, with the game started from the editor binary (`-game -RenderOffScreen`) and every material built by editor Python (`MaterialEditingLibrary`, one `MaterialExpressionCustom` block of shader code per material). Not yet run in a packaged build.

- **A particle effect can be an instanced mesh the game moves itself.** No effect asset is needed and a probe can count what went off.
  - One `UInstancedStaticMeshComponent` per kind of material (light that is added, lit smoke, solid bits), a fixed pool of instances, `SetNumCustomDataFloats(8)`; each frame `SetCustomData(i, ...)` for the live ones and one `BatchUpdateInstancesTransforms(0, All, true, true, true)`. Dead instances are parked below the floor at a tiny scale.
  - The material reads the numbers with `MaterialExpressionPerInstanceCustomData` (`data_index`, `const_default_value`) and needs `used_with_instanced_static_meshes` set by the script: the editor sets usage flags by itself, a cook does not.
  - About 1,000 instances cost nothing that could be measured. The explosion made this way: a flash, 26 noise-eaten fire sprites, a ground ring, 60 velocity-stretched sparks, smoke, debris cubes and one point light.
- **Smoke that is lit by the scene is one material setting.** Translucent with `TLM_VOLUMETRIC_NON_DIRECTIONAL`: a puff drifting through a spot light's cone lights up, and an explosion's own light colours its smoke.
- **Do not trust which way a basic shape's texture coordinates run.** A streak shape written along V drew as a dot on the engine's Plane, stretched along the other axis. Ask the pixel instead: `float2 pace = float2(length(float2(ddx(UV.x), ddy(UV.x))), length(float2(ddx(UV.y), ddy(UV.y))));` and the coordinate that changes more slowly on screen is the long one.
- **With manual exposure and no physical camera, a self-lit value of 1 is already white.** The first explosion was written with sprite colours of 9 to 40 and a 26,000 candela light, against lanterns of 500: three frames of a white screen. One scale for all sprites (0.17) and one for all flashes (0.12) fixed it; the numbers that read as an explosion were sprite colours near 1.5 and a light near 3,000 candelas.
- **A post-process material is made the same way as any other.** `material_domain = MD_POST_PROCESS`, `blendable_location = BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING` (that is the name in 5.9's Python).
  - The graph must contain a `MaterialExpressionSceneTexture` set to `PPI_POST_PROCESS_INPUT0`, wired into the code block even if the code ignores the pin: it is what makes the picture available. The code then samples wherever it likes with `SceneTextureLookup(ViewportUVToSceneTextureUV(uv, 14), 14, false)`; `uv` comes from a `MaterialExpressionScreenPosition` node's `ViewportUV` output and `ResolvedView.ViewSizeAndInvSize.xy` is the size in pixels.
  - It goes on a camera from C++: `Post.WeightedBlendables.Array.Add(FWeightedBlendable(1.f, DynamicInstance))`, and its parameters are set on the dynamic instance each frame.
  - About 40 samples a pixel (a ring for a glow round highlights, a row for a streak, six for a radial smear) ran with no visible cost at 1920x1080 on an M4 Max, on a machine too busy to measure finely.
  - After tone mapping the picture is 0 to 1: thresholds for "highlights" are numbers like 0.86, and a threshold on the brightest channel instead of on brightness also catches a saturated yellow coat.
- **Depth of field needs a big film back to show at a wide angle.** At a 62 degree field of view and 8 m, the default sensor gave no visible blur at any stop; a 70 mm sensor width with an f-stop of 1.2 divided by a 0-to-1 strength did. The same setting 4 m from a face left only a sliver sharp, so the stop is closed as the subject comes nearer than 12 m. Choosing what to focus on by which subject the camera's forward axis points at (a dot product each) held through three different cameras without any of them saying so.
- **A Volume-domain material (fog or steam in a mesh) reads its density from the Subsurface Color pin.** Left unconnected the density is 1, and the screen went white, twice. Inside the fog pass the object-position node returns the world origin, so pass each shape's centre in as a parameter. Steam needed about 400 times the first guess at density (from the record).
- **A soft-particle sprite (one with depth fade) laid flat on a surface fades to almost nothing.** The fade here ran over 25 cm, so a mark drawn 4.5 cm above the street would have shown at about a fifth; it is also why rain rings on the ground were always faint. Give ground marks a variant without the fade.
- **Movement toward or away from the camera does not read; give hung things a sideways component.** Run on 5.9.0, 13 November 2026. Strings of lanterns across a street, swung as whole actors about the line they hang from (8 degrees), looked still from a camera looking down the street, because that swing is along the view axis. A world position offset in their material fixed it: every vertex is displaced by its depth below the actor's pivot (`MaterialExpressionObjectPositionWS`, which the kit exports at the line's height) times the sine of a small angle across the street, with the phase varying along the line, plus a few centimetres of bounce where the line sags. The offset is in a separate material given only to hung pieces at run time, so the rest of the set does not take on world position offset and its shadow-cache cost. Checked from a still camera: frame-to-frame change at the top of the picture went from 0.001 to about 0.006 of full scale.

## 9. Lights made in code

Run on 5.9.0 on a Mac, 12 November 2026, while lighting a night street and a film studio from C++.

- **A light component made in C++ starts in Unitless intensity units. Call `SetIntensityUnits(ELightUnits::Candelas)` before setting a number.** `ULocalLightComponent`'s constructor sets `IntensityUnits = ELightUnits::Unitless`, and a unitless value is 16/10000 of a candela (`LocalLightComponent.cpp`, read in the 5.9 source). Lanterns at 9000 and overhead lights at 30000 were 14 and 48 candelas, about 1 lux at 5 to 12 m: they added almost nothing. In candelas the lanterns needed 500 and the overhead lights 900.
- **Set a spawned spot light's rotation after `SetMobility(EComponentMobility::Movable)`.** `ASpotLight` already points down, and `SpawnActor` adds the spawn rotation to that, so the studio's overhead lights shone sideways. Setting the rotation again did nothing until it came after the mobility change: a light that is not movable ignores a later rotation without a message.
- **Check every new light by switching it off in a capture.** Both faults above were found only because switching the lights off changed nothing. Overhead spots hung inside their own lamp housings, with shadows on, lit nothing until moved below the housing (10.1 m against the housing's lowest point at 10.35 m).
- **Budget dynamic lights by a window around the player.** Lights more than about 24 m behind or 56 m ahead off, shadows only from 7 m behind to 24 m ahead, and no more than about 22 lit at once kept a street of lanterns and work lights playable. The saving was not measured.
- **Hardware ray tracing and hit lighting for Lumen's reflections made no visible difference** on wet paving in four captures, so they were left off (from the record).
