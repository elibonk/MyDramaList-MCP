"""Configuration stays on the host; credentials are never MCP tool arguments."""

import os
from dataclasses import dataclass, field
from pathlib import Path


def secret(name: str) -> str | None:
    value = os.getenv(name)
    filename = os.getenv(f"{name}_FILE")
    if value and filename:
        raise ValueError(f"Set either {name} or {name}_FILE, not both")
    return Path(filename).read_text().strip() if filename else value or None


@dataclass(frozen=True)
class Settings:
    token_file: Path = field(default_factory=lambda: Path.home() / ".mydramalist/token.json")
    access_token: str | None = field(default=None, repr=False)
    server_token: str | None = field(default=None, repr=False)
    read_only: bool = False
    timeout: float = 30.0
    request_interval: float = 0.25
    host: str = "127.0.0.1"
    port: int = 8000
    allowed_hosts: tuple[str, ...] = ("localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*")
    allowed_origins: tuple[str, ...] = ("http://localhost:*", "http://127.0.0.1:*")

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        readonly = os.getenv("MDL_MCP_READ_ONLY", "false").lower()
        if readonly not in {"true", "false", "1", "0"}:
            raise ValueError("MDL_MCP_READ_ONLY must be true or false")
        settings = cls(
            token_file=Path(os.getenv("MDL_TOKEN_FILE", str(defaults.token_file))).expanduser(),
            access_token=secret("MDL_ACCESS_TOKEN"),
            server_token=secret("MDL_MCP_TOKEN"),
            read_only=readonly in {"true", "1"},
            timeout=float(os.getenv("MDL_TIMEOUT", "30")),
            request_interval=float(os.getenv("MDL_REQUEST_INTERVAL", "0.25")),
            host=os.getenv("MDL_MCP_HOST", defaults.host),
            port=int(os.getenv("MDL_MCP_PORT", "8000")),
            allowed_hosts=tuple(
                filter(
                    None,
                    os.getenv("MDL_MCP_ALLOWED_HOSTS", ",".join(defaults.allowed_hosts)).split(","),
                )
            ),
            allowed_origins=tuple(
                filter(
                    None,
                    os.getenv("MDL_MCP_ALLOWED_ORIGINS", ",".join(defaults.allowed_origins)).split(
                        ","
                    ),
                )
            ),
        )
        if settings.timeout <= 0 or settings.request_interval < 0:
            raise ValueError(
                "MDL_TIMEOUT must be positive; MDL_REQUEST_INTERVAL cannot be negative"
            )
        if not 1 <= settings.port <= 65535:
            raise ValueError("MDL_MCP_PORT must be between 1 and 65535")
        return settings
