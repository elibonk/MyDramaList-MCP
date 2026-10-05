import asyncio
import os
import socket
import subprocess
import sys

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client


def environment(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("MDL_")}
    env["MDL_TOKEN_FILE"] = str(tmp_path / "token.json")
    return env


async def verify_session(session):
    await session.initialize()
    tools = (await session.list_tools()).tools
    assert "mdl_search_titles" in {t.name for t in tools}
    reply = await session.call_tool("mdl_server_status", {})
    assert not reply.isError
    assert reply.structuredContent["data"]["authenticated"] is False
    assert len(tools) == 89


async def test_stdio_subprocess(tmp_path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mydramalist_mcp", "serve", "--transport", "stdio"],
        env=environment(tmp_path),
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await verify_session(session)


async def test_http_subprocess(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = environment(tmp_path)
    env.update(MDL_MCP_PORT=str(port), MDL_MCP_TOKEN="test-mcp-secret-" + "s" * 40)
    logfile = tmp_path / "server.log"
    with logfile.open("wb") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "mydramalist_mcp", "serve", "--transport", "http"],
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            async with httpx.AsyncClient() as probe:
                for _ in range(100):
                    if process.poll() is not None:
                        raise AssertionError(logfile.read_text())
                    try:
                        if (await probe.get(f"http://127.0.0.1:{port}/health")).status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    await asyncio.sleep(0.05)
                else:
                    raise AssertionError("HTTP server did not become ready")
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {env['MDL_MCP_TOKEN']}"}
            ) as http:
                async with streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp", http_client=http
                ) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await verify_session(session)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
