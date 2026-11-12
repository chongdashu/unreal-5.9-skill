#!/usr/bin/env python3
"""Talk to the Unreal Editor's built-in MCP server from a shell (UE 5.9, tool-search mode).

Standard library only. Each run opens its own session: initialize, notifications/initialized, one request.

    uemcp.py tools                               # what tools/list returns (the meta-tools)
    uemcp.py toolsets                            # list_toolsets
    uemcp.py describe <Toolset> [<Toolset>...]   # describe_toolsets
    uemcp.py call <Toolset.Tool> '<json args>'   # call_tool; or --args-file args.json
    uemcp.py py <script.py>                      # execute_python with the file's source
    uemcp.py py -c '<python source>'
    uemcp.py raw <method> '<json params>'        # any JSON-RPC method

Environment: UE_MCP_URL (default http://127.0.0.1:8000/mcp), UE_MCP_TIMEOUT seconds (default 300).
Images and audio in a result are written to --media-dir (default: the current directory) and
reported by path, so base64 never lands in the conversation.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("UE_MCP_URL", "http://127.0.0.1:8000/mcp")
TIMEOUT = float(os.environ.get("UE_MCP_TIMEOUT", "300"))
PROTOCOL = os.environ.get("UE_MCP_PROTOCOL", "2025-06-18")
PYTHON_TOOL = os.environ.get(
    "UE_MCP_PYTHON_TOOL", "editor_toolset.toolsets.python_scripting.PythonScriptingTools.execute_python")

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Origin": "http://127.0.0.1",
}


class McpError(RuntimeError):
    pass


def _post(body: dict, session: str | None, want_id: int | None):
    headers = dict(HEADERS)
    if session:
        headers["Mcp-Session-Id"] = session
        headers["MCP-Protocol-Version"] = PROTOCOL
    request = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        response = urllib.request.urlopen(request, timeout=TIMEOUT)
    except urllib.error.HTTPError as error:
        raise McpError(f"HTTP {error.code}: {error.read().decode(errors='replace')[:500]}") from error
    except urllib.error.URLError as error:
        raise McpError(
            f"cannot reach {URL}: {error.reason}. Is the editor up and the MCP server started? "
            "Mac log: ~/Library/Logs/Unreal Engine/<Project>Editor/<Project>.log") from error
    with response:
        session_out = response.headers.get("Mcp-Session-Id")
        content_type = response.headers.get("Content-Type", "")
        if want_id is None:
            response.read()
            return None, session_out
        if "text/event-stream" in content_type:
            # Server-sent events: skip progress notifications until the reply with our id arrives.
            for raw in response:
                line = raw.decode(errors="replace").rstrip("\r\n")
                if not line.startswith("data:"):
                    continue
                try:
                    message = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if message.get("id") == want_id:
                    return message, session_out
            raise McpError("event stream ended without a reply")
        return json.loads(response.read().decode()), session_out


def open_session() -> tuple[str | None, dict]:
    reply, session = _post({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                   "clientInfo": {"name": "uemcp.py", "version": "1"}},
    }, None, 1)
    if "error" in reply:
        raise McpError(f"initialize failed: {json.dumps(reply['error'])}")
    _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, session, None)
    return session, reply.get("result", {})


def request(method: str, params: dict | None = None) -> dict:
    session, _ = open_session()
    reply, _ = _post({"jsonrpc": "2.0", "id": 2, "method": method, "params": params or {}}, session, 2)
    if "error" in reply:
        raise McpError(json.dumps(reply["error"]))
    return reply.get("result", {})


def call_meta(name: str, arguments: dict) -> dict:
    return request("tools/call", {"name": name, "arguments": arguments})


def call_tool(full_name: str, arguments: dict) -> dict:
    """call_tool takes the toolset and the tool separately; split Toolset.Tool at the last dot."""
    toolset, _, tool = full_name.rpartition(".")
    payload = {"tool_name": tool, "arguments": arguments}
    if toolset:
        payload["toolset_name"] = toolset
    return call_meta("call_tool", payload)


def show_result(result: dict, media_dir: str, max_chars: int) -> int:
    """Print text blocks, save media blocks, and return a shell exit code."""
    count = 0
    for block in result.get("content", []):
        kind = block.get("type")
        if kind == "text":
            text = block.get("text", "")
            # Tool results arrive as {"returnValue": ...}; unwrap a plain string so scripts print cleanly.
            try:
                wrapped = json.loads(text)
                if isinstance(wrapped, dict) and set(wrapped) == {"returnValue"} and isinstance(wrapped["returnValue"], str):
                    text = wrapped["returnValue"]
            except (json.JSONDecodeError, TypeError):
                pass
            print(text if max_chars <= 0 else text[:max_chars])
            if 0 < max_chars < len(text):
                print(f"... [{len(text) - max_chars} more characters; raise --max]", file=sys.stderr)
        elif kind in ("image", "audio"):
            count += 1
            mime = block.get("mimeType", "application/octet-stream")
            extension = {"image/png": "png", "image/jpeg": "jpg", "audio/wav": "wav", "audio/ogg": "ogg"}.get(mime, "bin")
            os.makedirs(media_dir, exist_ok=True)
            path = os.path.abspath(os.path.join(media_dir, f"mcp-{os.getpid()}-{count}.{extension}"))
            with open(path, "wb") as handle:
                handle.write(base64.b64decode(block.get("data", "")))
            print(f"[{kind} saved: {path}]")
        else:
            print(json.dumps(block)[:max_chars if max_chars > 0 else None])
    if not result.get("content") and "structuredContent" in result:
        print(json.dumps(result["structuredContent"], indent=1)[:max_chars if max_chars > 0 else None])
    return 1 if result.get("isError") else 0


def main() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--max", type=int, default=6000, help="maximum characters of text to print (0 = no limit)")
    common.add_argument("--media-dir", default=".", help="where image and audio results are written")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("info", parents=[common], help="server and instance information from initialize")
    sub.add_parser("tools", parents=[common], help="tools/list")
    sub.add_parser("toolsets", parents=[common], help="list_toolsets")
    describe = sub.add_parser("describe", parents=[common], help="describe_toolsets")
    describe.add_argument("toolsets", nargs="+")
    describe.add_argument("--schemas", action="store_true", help="include input and output schemas")
    call = sub.add_parser("call", parents=[common], help="call_tool")
    call.add_argument("tool", help="Toolset.Tool: everything before the last dot is the toolset name")
    call.add_argument("arguments", nargs="?", default="{}")
    call.add_argument("--args-file")
    py = sub.add_parser("py", parents=[common], help="run Python in the editor through the execute_python tool")
    py.add_argument("script", nargs="?")
    py.add_argument("-c", dest="source")
    raw = sub.add_parser("raw", parents=[common], help="any JSON-RPC method")
    raw.add_argument("method")
    raw.add_argument("params", nargs="?", default="{}")
    args = parser.parse_args()

    try:
        if args.command == "info":
            _, result = open_session()
            print(json.dumps(result, indent=1)[:args.max if args.max > 0 else None])
            return 0
        if args.command == "tools":
            for tool in request("tools/list").get("tools", []):
                print(f"{tool['name']}: {json.dumps(tool.get('inputSchema', {}).get('properties', {}))[:400]}")
            return 0
        if args.command == "raw":
            print(json.dumps(request(args.method, json.loads(args.params)), indent=1)[:args.max if args.max > 0 else None])
            return 0
        if args.command == "toolsets":
            return show_result(call_meta("list_toolsets", {}), args.media_dir, args.max)
        if args.command == "describe":
            return show_result(call_meta("describe_toolsets", {"toolset_names": args.toolsets, "include_schemas": args.schemas}),
                               args.media_dir, args.max)
        if args.command == "call":
            arguments = json.load(open(args.args_file)) if args.args_file else json.loads(args.arguments)
            return show_result(call_tool(args.tool, arguments), args.media_dir, args.max)
        if args.command == "py":
            source = args.source if args.source is not None else open(args.script).read()
            return show_result(call_tool(PYTHON_TOOL, {"script": {"content": source}}), args.media_dir, args.max)
    except McpError as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
