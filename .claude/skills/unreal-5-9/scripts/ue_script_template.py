"""Editor-Python script template for Unreal MCP sessions (UE 5.9).

Run it through the shipped Python tool:
    python3 scripts/uemcp.py py /abs/path/this_script.py

Conventions: `unreal` is already imported; imports stay at the top level; no time.sleep (use
`await asyncio.sleep`); refuse to edit while Play In Editor runs; guard creates; label what you spawn
with a prefix and wipe by it; and END WITH THE RECEIPT, because the last expression is what comes back.
"""
import json

PREFIX = "MY_"
res = {"steps": [], "errors": [], "assets": {}, "actors": {}}

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def get_or_create(name, folder, cls, factory):
    """Load if present: create_asset on an existing asset opens a blocking modal (5.8)."""
    path = f"{folder}/{name}"
    if assets.does_asset_exist(path):
        return unreal.load_asset(path)
    return tools.create_asset(name, folder, cls, factory)


def save(obj_or_path):
    """The default save skips 'clean' assets that Python just made; force it (5.8)."""
    path = obj_or_path if isinstance(obj_or_path, str) else obj_or_path.get_path_name()
    assets.save_asset(path, only_if_is_dirty=False)


def spawn(cls, label, location=(0.0, 0.0, 0.0), yaw=0.0):
    """Rotator by keyword only: positional is (roll, pitch, yaw)."""
    actor = actors.spawn_actor_from_class(cls, unreal.Vector(*location), unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
    if actor is None:
        res["errors"].append(f"spawn returned None for {label}")
        return None
    actor.set_actor_label(label)
    return actor


def component(actor, cls):
    """Light, fog and sky settings live on the component, not the actor."""
    return actor.get_component_by_class(cls) if actor else None


def main():
    if editor.get_game_world():
        res["errors"].append("Play In Editor is running; refusing to edit the level")
        return
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith(PREFIX):
            actors.destroy_actor(actor)
    # ... your work: spawn(...), get_or_create(...), save(...)
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith(PREFIX):
            at = actor.get_actor_location()
            res["actors"][actor.get_actor_label()] = [round(at.x, 1), round(at.y, 1), round(at.z, 1)]
    res["saved"] = bool(levels.save_current_level())
    res["steps"].append("done")


try:
    main()
except Exception as error:  # the receipt must come back even on failure
    res["errors"].append(repr(error))

json.dumps(res)
