<div align="center">

<img src=".github/assets/rooftop-rally.jpg" alt="Rooftop Rally: two small toy-like players mid-rally on a rooftop pickleball court at sunset, with a crowd, string lights and a city skyline behind" width="100%">

# Agent Skill for Unreal Engine 5.9 Preview

### Field lessons for building and shipping an Unreal Engine 5.9 game with a coding agent.

An **Agent Skill** in the open `SKILL.md` format, laid out for **Claude Code** (`.claude/skills`) and for **Codex** and other agents that read `.agents/skills`. It was written while Claude Fable 5.2 took a small sports game from a greybox to Mac, iPhone and web builds over Unreal's built-in MCP server.

<br>

[![Brought to you by VibeGameDev](.github/assets/brought-to-you-by-vibegamedev.png)](https://www.vibegamedev.com/?utm_source=github&utm_medium=readme_badge&utm_campaign=unreal-5.9-skill)

[**▶ Watch the video**](https://www.youtube.com/watch?v=0G8air5h3_s) &nbsp;·&nbsp;
[**Read the skill**](.claude/skills/unreal-5-9/SKILL.md) &nbsp;·&nbsp;
[**Install it**](#install-it) &nbsp;·&nbsp;
[**▶ Play the game it built**](https://rooftop-rally.vercel.app) &nbsp;·&nbsp;
[**Learn to build games like this**](https://www.vibegamedev.com/?utm_source=github&utm_medium=readme_links&utm_campaign=unreal-5.9-skill)

![Unreal Engine](https://img.shields.io/badge/Unreal_Engine-5.9_Preview-0e1128?logo=unrealengine&logoColor=white)
![Agent Skills](https://img.shields.io/badge/Agent_Skills-SKILL.md-5b4be0)
![Claude Code](https://img.shields.io/badge/Claude_Code-.claude%2Fskills-d97757?logo=claude&logoColor=white)
![Codex and other agents](https://img.shields.io/badge/Codex_+_other_agents-.agents%2Fskills-10a37f)
![Unreal MCP](https://img.shields.io/badge/Unreal_MCP-built--in_plugin-313131)
![C++](https://img.shields.io/badge/C++-game_code-00599c?logo=cplusplus&logoColor=white)
![Python](https://img.shields.io/badge/Python-editor_scripts-3776ab?logo=python&logoColor=white)
![WebGPU](https://img.shields.io/badge/Wasm_+_WebGPU-web_build-005a9c)

<br>

![Rooftop Rally gameplay: a rally from the game camera, the crowd on the bleachers and the score going up](.github/assets/rooftop-rally.gif)

</div>

---

## The skill

Unreal Engine 5.9 ships an MCP server inside the editor (the `ModelContextProtocol` plugin, shown as "Unreal MCP"). An agent can call editor tools through it and run editor Python. Epic documents the tools. This skill is the part Epic's reference leaves out: what happened when an agent used them to build a whole game, and what to do about it.

- **A game an agent can play.** Console-variable twins for every input, simulated keys, pads and fingers through the real input stack, and probes that read the result back, so play can be scripted and asserted on.
- **Measured, not guessed.** Each lesson gives the rule first and the number that was measured second, and says whether it was run on 5.9, read in the engine source, or carried over from 5.8.
- **From an empty project to three platforms.** Setup and the editor lifecycle, importing glTF characters and environments, animation driven from C++, a canvas HUD, sound, captures and frame-exact footage, then packaging for Mac, iOS and the web.
- **The traps.** An editor that answers while it is frozen, a port that stays unbindable after a quit, return values that report success for work that did not happen, and a packaged build that draws a different picture from the editor.

## Install it

Clone the repository, then copy the skill folder to where your agent looks for skills.

```sh
git clone https://github.com/chongdashu/unreal-5.9-skill.git

# Claude Code, for one project
mkdir -p /path/to/your-project/.claude/skills
cp -R unreal-5.9-skill/.claude/skills/unreal-5-9 /path/to/your-project/.claude/skills/

# Claude Code, for every project on this machine
mkdir -p ~/.claude/skills
cp -R unreal-5.9-skill/.claude/skills/unreal-5-9 ~/.claude/skills/

# Codex and other agents that read .agents/skills
mkdir -p /path/to/your-project/.agents/skills
cp -R unreal-5.9-skill/.agents/skills/unreal-5-9 /path/to/your-project/.agents/skills/
```

Start a new session in the project. The agent loads the skill by itself when the work is about Unreal. You can also call it by name: `/unreal-5-9` in Claude Code, `$unreal-5-9` in Codex.

## What you need

- Unreal Engine 5.9 Preview with the `ModelContextProtocol`, `AllToolsets` and `PythonScriptPlugin` plugins enabled in the project.
- Python 3 for the helper scripts. The MCP client uses the standard library only; the capture cropper needs Pillow.
- A coding agent that loads Agent Skills, such as Claude Code or Codex.
- macOS for the shell helpers (`ue_wait.sh`, `ue_relaunch.sh`). Everything was run on macOS 26.6 on Apple Silicon; nothing here was run on Windows or Linux.
- For the web build, an engine source checkout and Emscripten. The launcher's install refuses the Wasm platform.

## What's here

| Path | What it is |
| --- | --- |
| [`.claude/skills/unreal-5-9/`](.claude/skills/unreal-5-9) | The skill, where Claude Code finds it |
| [`.agents/skills/unreal-5-9/`](.agents/skills/unreal-5-9) | The same files, byte for byte, where Codex and other agents find it |
| [`SKILL.md`](.claude/skills/unreal-5-9/SKILL.md) | The method, the order that worked, the verification ladder and the anti-patterns |
| [`references/`](.claude/skills/unreal-5-9/references) | One file per job, with the measured detail |
| [`scripts/`](.claude/skills/unreal-5-9/scripts) | A small MCP client (`uemcp.py`), wait and relaunch helpers, a capture cropper and an editor script template |

The reference files, by job:

| Job | File |
| --- | --- |
| A new project, launching, the log, the handshake, `.mcp.json` | [`setup-and-lifecycle.md`](.claude/skills/unreal-5-9/references/setup-and-lifecycle.md) |
| Editor scripts: levels, Play In Editor, readbacks, what Python refuses | [`editor-python.md`](.claude/skills/unreal-5-9/references/editor-python.md) |
| Test hooks in C++, probes, compile checks, headless runs | [`drivable-game.md`](.claude/skills/unreal-5-9/references/drivable-game.md) |
| Importing `.glb` meshes, characters and clips; sockets; materials; sky | [`import-and-materials.md`](.claude/skills/unreal-5-9/references/import-and-materials.md) |
| Animation from C++: cross-fades, legs under a swing, hit timing | [`animation.md`](.claude/skills/unreal-5-9/references/animation.md) |
| A menu and HUD on the canvas; keys, pads, touch, a phone's safe area | [`hud-and-input.md`](.claude/skills/unreal-5-9/references/hud-and-input.md) |
| Importing sound and checking it from a recording | [`sound.md`](.claude/skills/unreal-5-9/references/sound.md) |
| Captures, exposure, framing, frame-exact footage | [`capture-and-recording.md`](.claude/skills/unreal-5-9/references/capture-and-recording.md) |
| Several agent sessions on one editor | [`sharing-an-editor.md`](.claude/skills/unreal-5-9/references/sharing-an-editor.md) |
| A standalone Mac app; building, signing and running on an iPhone | [`packaging.md`](.claude/skills/unreal-5-9/references/packaging.md) |
| A web build (Wasm, WebGPU), hosting it, play stats from it | [`web.md`](.claude/skills/unreal-5-9/references/web.md) |
| Arriving from 5.8 | [`from-5.8.md`](.claude/skills/unreal-5-9/references/from-5.8.md) |

The skill points to a companion `unreal-5-8` skill for the older engine in a few places. That one is not in this repository.

## The game it built

**Rooftop Rally** is a pickleball match on a rooftop at sunset: one player against the computer, first to five. It runs as a Mac app, on an iPhone and [in a browser](https://rooftop-rally.vercel.app) through Unreal 5.9's Wasm and WebGPU platform. Its console variables, classes and folders appear in the skill under stand-in names (`game.`, `MyGame`), so the lessons read the same for your project.

The build is shown in [this video](https://www.youtube.com/watch?v=0G8air5h3_s).

This repository holds the skill only. The game's source is not here.

<div align="center">

<br>

## Build games like this with AI

This repository is one agent skill. **VibeGameDev** teaches the whole method: how to direct a coding agent through mockups, models, animation and launch, with the project templates, skills and source of games like this one.

[![VibeGameDev - The #1 AI Toolkit To Build Games Like This](.github/assets/vibegamedev-banner.png)](https://www.vibegamedev.com/?utm_source=github&utm_medium=readme_footer&utm_campaign=unreal-5.9-skill)

**[vibegamedev.com](https://www.vibegamedev.com/?utm_source=github&utm_medium=readme_footer&utm_campaign=unreal-5.9-skill)**

<br>

Made by **Chong-U** &nbsp;·&nbsp;
[𝕏 @chongdashu](https://x.com/chongdashu) &nbsp;·&nbsp;
[YouTube @AIOriented](https://youtube.com/@AIOriented) &nbsp;·&nbsp;
[GitHub @chongdashu](https://github.com/chongdashu)

<sub>Brought to you by [vibegamedev.com](https://www.vibegamedev.com/?utm_source=github&utm_medium=readme_footer&utm_campaign=unreal-5.9-skill)</sub>

</div>

## Licence

The skill, its notes and its scripts: [MIT](LICENSE). The game images and the VibeGameDev artwork in `.github/assets`: [CC BY-NC 4.0](CONTENT-LICENSE.md).
