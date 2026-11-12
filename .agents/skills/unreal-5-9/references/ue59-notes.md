# This file was split (skill 3.0.0, 2026-11-11)

The notes that lived here are now one file per job, with every entry carried across. Do not add notes here.

On 2026-11-12 the skill was also renamed: `.claude/skills/unreal-mcp/` is now `.claude/skills/unreal-5-9/`, and the 5.8 original is back as `.claude/skills/unreal-5-8/`.

| Old section | Now in |
|---|---|
| 1. Project setup · 2. Launch timings and the log · 3. The wire protocol · 7. Epic's own agent skills | `setup-and-lifecycle.md` |
| 4. `execute_python` (and the Python traps that were scattered through sections 6, 10 and 11) | `editor-python.md` |
| 5. Play, capture, exposure · 12. Recording footage | `capture-and-recording.md` |
| 6. Importing meshes, characters and clips (import, sockets, materials, sky) | `import-and-materials.md` |
| 6. The code-driven animation instance, running legs, "making a hit look like a hit" · 11. Turning a head | `animation.md` |
| 8. C++ that an agent can drive, and every compile-check and build note | `drivable-game.md` |
| 9. Sound | `sound.md` |
| 10. A menu and HUD on the canvas; pads, touch, the safe area | `hud-and-input.md` |
| 11. Spectators and props (the import and material entries) | `import-and-materials.md` |
| 6 and 11. Several sessions on one editor | `sharing-an-editor.md` |
| 13. Packaging: a Mac app and an iOS build (from the `ios` branch) | `packaging.md` |
| 14. A web build · 15. Play stats (from the `web` and `analytics-web` branches) | `web.md` |
| "Not re-tested on 5.9" | `from-5.8.md` |

## If you are merging a branch that edited this file

The branch copies as of 2026-11-11 were already carried over: `ios` at `c390507`, `web` at `8bdd197`, `analytics-web` at `e491639`. Anything a branch added to this file after those commits is not in the new files yet.

Git reports the old file as "deleted in main, modified in your branch" and leaves your branch's copy at the old path, `.claude/skills/unreal-mcp/references/ue59-notes.md` (checked by dry run against all three branches on 2026-11-12).

1. Move each entry your branch added since those commits into the file for its job in `.claude/skills/unreal-5-9/references/`, under the section it belongs to.
2. Then remove the old-path copy (`git rm`), so that no `.claude/skills/unreal-mcp/` folder is left behind.
3. Point any "section N" reference at the new file.
4. If `SKILL.md` conflicts too (it does for `web` and `analytics-web`), keep main's: the web paragraph those branches added is already in its "Shipping it" section.
5. Repoint anything your branch added that calls the helpers by the old path: `git grep -l 'skills/unreal-mcp'` should print nothing afterwards.

A new lesson goes in the file for its job; `SKILL.md` ("Keeping these notes") says how to write it.
