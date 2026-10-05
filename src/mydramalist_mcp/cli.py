"""Run either transport, log in interactively, or check the live upstream API."""

import argparse
import asyncio
import getpass
import json
import sys

import uvicorn
from dotenv import load_dotenv
from mdl import AsyncMDLClient, FileTokenStore

from .backend import Backend, BackendError
from .catalog import Operation
from .config import Settings, secret
from .server import create_server, http_app


async def login(settings: Settings) -> int:
    username = secret("MDL_USERNAME") or input("MyDramaList username: ").strip()
    password = secret("MDL_PASSWORD") or getpass.getpass("MyDramaList password: ")
    if not username or not password:
        print("Username and password are required.", file=sys.stderr)
        return 1
    async with AsyncMDLClient(
        token_store=FileTokenStore(settings.token_file), timeout=settings.timeout
    ) as client:
        try:
            await client.auth.login(username, password)
        except Exception as exc:
            code = getattr(exc, "status_code", None)
            print(
                f"Login failed{' (HTTP ' + str(code) + ')' if code else ''}. "
                "Check credentials and upstream compatibility.",
                file=sys.stderr,
            )
            return 1
    print(f"Login succeeded. Tokens saved to {settings.token_file}. Restart the MCP server.")
    return 0


async def doctor(settings: Settings) -> int:
    backend = Backend(settings)
    report = {"server": backend.status(), "checks": {}}
    checks = [
        Operation("titles", "get_genres"),
        Operation("titles", "get_title"),
        Operation("search", "titles"),
    ]
    if backend.client.tokens.get_token():
        checks.append(Operation("account", "get_profile", private=True))
    failed = False
    try:
        for op in checks:
            arguments = (
                {"title_id": 686}
                if op.method == "get_title"
                else ({"query": "signal"} if op.group == "search" else {})
            )
            try:
                await backend.call(op, arguments)
                report["checks"][op.name] = {"ok": True}
            except BackendError as exc:
                failed = True
                report["checks"][op.name] = {"ok": False, "code": exc.code, "message": str(exc)}
            except Exception:
                failed = True
                report["checks"][op.name] = {"ok": False, "code": "unexpected_error"}
    finally:
        await backend.close()
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Self-hostable MyDramaList MCP server")
    parser.add_argument("--env-file", help="Load configuration from this dotenv file")
    commands = parser.add_subparsers(dest="command")
    serve = commands.add_parser("serve", help="Start the MCP server")
    serve.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    commands.add_parser("login", help="Log in on the host and save tokens (never prints tokens)")
    commands.add_parser("doctor", help="Check live upstream reads; nonzero on failure")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    try:
        settings = Settings.from_env()
        if args.command == "login":
            raise SystemExit(asyncio.run(login(settings)))
        if args.command == "doctor":
            raise SystemExit(asyncio.run(doctor(settings)))
        if args.command == "serve" and args.transport == "http":
            if not settings.server_token or len(settings.server_token) < 32:
                parser.error("HTTP requires MDL_MCP_TOKEN (at least 32 characters)")
            server = create_server(settings)
            uvicorn.run(
                http_app(server, settings),
                host=settings.host,
                port=settings.port,
                log_level="info",
                access_log=False,
            )
        else:
            create_server(settings).run(transport="stdio")
    except (ValueError, OSError):
        parser.error(
            "Invalid configuration or unreadable secret file. Check environment and file paths."
        )


if __name__ == "__main__":
    main()
