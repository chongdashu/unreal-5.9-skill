# Importing meshes, characters and clips; sockets; materials

Verified on Unreal Engine 5.9.0 (changelist 60351404, the launcher's install) on macOS 26.6, Apple Silicon (M4 Max), on 10 and 11 November 2026, while building a small sports game. Where a line comes from reading the engine source rather than from a run, it says so. Names starting `game.` or `GAME_` stand in for that game's console variables and actor labels: choose your own.

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

## 5. Sky

- `VolumetricCloud` uses `/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst`; duplicate it into the project and set `Cloud_GlobalCoverage`, `Cloud_GlobalDensity` (scalars) on the copy. Its wind is the vector `Layout_WindControls`, default (1, 1, 0.5, 0.333).

## 6. Props that carry game state

- **Numbers on a prop, as meshes.** Ten numerals made from the game's font in Blender (a FONT curve converted with `bpy.data.meshes.new_from_object`, stood up to face +X), imported as ten static meshes and swapped on four components by an actor that reads the score, gave a scoreboard a probe can check (`shown_player`, `shown_rival`, a flip count) with no text rendering, font asset or widget.

## 7. Nanite after import

Every imported static mesh is Nanite (section 1). That is free in the editor and costs something on every other target: materials need a usage flag before a packaged Mac game draws them (`packaging.md`), and iOS and the web draw the coarse fallback mesh unless the fallback is raised or Nanite is turned off (`packaging.md`, `web.md`).
