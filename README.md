# MyDramaList MCP

A self-hostable Python MCP server built on [`mydramalist-client`](https://pypi.org/project/mydramalist-client/)
and the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x).
Runs locally over **stdio** or as an authenticated **Streamable HTTP** service at `/mcp`.
It serves **one MyDramaList account**: all authorized clients share that account and its permissions.

**Live API verification is currently blocked:** on October 5, 2026, public title and search
requests using client 0.1.0 returned HTTP `400 Bad Request`. Genre listing succeeded, so
the failure affects specific endpoints rather than every API request. The MCP transports and SDK
adapter can be tested independently, but this project cannot guarantee live reads or writes
until the upstream API accepts requests. Run `mydramalist-mcp doctor` on your host to check.
An MCP connection or passing mocked tests does not establish upstream compatibility.

## What it can do

- Search titles and people; read details, cast, genres, tags, reviews and recommendations.
- Browse trending, top airing, upcoming, recommended and top movie feeds.
- Read watchlists and progress; add/update sync entries and remove entries.
- Create, edit and delete reviews, comments and custom lists; manage list items and votes.
- Read and edit your profile and feed privacy; upload profile/feed images.
- Read/create/edit/delete activity posts, like content, read articles and notifications.
- Read calendars, user statistics, groups, friend requests and leaderboards.

Tools are named `mdl_<resource>_<method>`, such as `mdl_search_titles`,
`mdl_titles_get_title`, `mdl_reviews_submit` and `mdl_custom_lists_add_item`.
Use `mdl_capabilities` or your MCP client's tool listing to inspect available tools and schemas.
`TOOLS.md` lists the full allowlist. Writes are enabled by default; set `MDL_MCP_READ_ONLY=true`
to hide them and enforce read-only behavior in the backend.

### Upstream limits

The [client](https://github.com/danieyal/pymdl) uses an unofficial private API. Some endpoints,
field names and enum values are inferred and can change. This wrapper does not add unsupported
API endpoints. In particular, **adding new dramas/people to the public catalog and editing their
metadata are not supported by client 0.1.0**. "Add/update" here means your watchlist, lists,
reviews, comments, posts and profile.

Watchlist `add(item=...)` accepts the SDK's raw sync object. The package defines **no typed
write model or verified numeric status mapping**. Progress response fields include
`episode_seen`, `rating`, `note`, `date_start` and `date_finish`; this does not prove the
same fields are accepted for writes. Verify the sync payload against current upstream docs
or your own app's requests before using it. This project deliberately does not invent a
watch-status mapping. Read-list statuses are `watching`, `plantowatch`, `completed`,
`onhold`, `dropped`, `undecided` and `notinterested`.

There are no purchase, account-deactivation, password/email-editing or private-message tools.
Tokens are never returned through MCP. No automatic retries are made; after a failed write,
read the current state before retrying, since the upstream may have applied it.

## Local setup (Python 3.11+)

From this project directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps .
.venv/bin/mydramalist-mcp doctor
```

`requirements.lock` pins the runtime dependency versions resolved during verification.
The SDK is pinned to its supported 1.x API so a new major version cannot break the adapter.

### Log in to use your account

```sh
.venv/bin/mydramalist-mcp login
```

Enter your username and password in the terminal (the password is hidden). The library
handles the app's password encoding. Tokens are saved with owner-only permissions to
`~/.mydramalist/token.json`. Override this with `MDL_TOKEN_FILE`.
Authentication is not exposed as an MCP tool, so passwords do not enter model/tool logs.
Do not paste credentials into chat.

You can instead set `MDL_ACCESS_TOKEN` or `MDL_ACCESS_TOKEN_FILE` to an existing **app API**
bearer token. Website cookies and the generated `mdl-api-key` are different values.
An environment token takes precedence over the saved token file. Remove it before switching
to a login-created token file. Tokens do not refresh automatically: after a `401`, log in
again and restart the server. The client clears rejected tokens.

Public tools can run without login, subject to what the upstream permits. Private reads
and all writes require a configured token. Token presence is not a check of token validity.

### Connect a local MCP client (stdio)

Use absolute paths in your client's configuration:

```json
{
  "mcpServers": {
    "mydramalist": {
      "command": "/absolute/path/mydramalist-mcp/.venv/bin/mydramalist-mcp",
      "args": ["serve", "--transport", "stdio"],
      "env": {
        "MDL_TOKEN_FILE": "/absolute/path/to/token.json"
      }
    }
  }
}
```

This is the common `mcpServers` JSON shape; clients that use another format should use the
same executable, arguments and environment. The client starts the subprocess. Application
messages/logs use stderr; stdout is reserved for MCP.

Try: "Find Signal and show the cast", "Show my currently watching list", or
"Create a custom list named Weekend Dramas and add this title".

## Self-host with Docker Compose

Requires Docker Engine/Desktop with Compose. From this directory:

```sh
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Put the generated value in `MDL_MCP_TOKEN` in `.env`. This is the **MCP server** password,
distinct from your MyDramaList bearer token. Then:

```sh
docker compose build
docker compose run --rm mdl login
docker compose up -d
docker compose exec mdl mydramalist-mcp doctor
```

The login stores tokens in the named `mdl-data` volume; restarts preserve them.
Login may fail with the currently observed upstream `400`; see troubleshooting below.
The image runs as a non-root user and the service has a local health check.
The Compose service publishes only `127.0.0.1:8000` by default.

Configure a Streamable HTTP MCP client with:

- URL: `http://127.0.0.1:8000/mcp`
- Header: `Authorization: Bearer <your MDL_MCP_TOKEN>`

For clients with the common JSON configuration shape, see `examples/http-client.json`.
Clients must support a custom bearer header. This is a personal server with static bearer
authentication, **not an OAuth provider**. OAuth-only clients need an authentication gateway.

### Run HTTP without Docker

```sh
export MDL_MCP_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
.venv/bin/mydramalist-mcp serve --transport http
```

HTTP refuses to start without a server token of at least 32 characters. `/health` returns
process health without authentication; it does not expose account details or test the API.

### Hosting behind a proxy

Keep port 8000 private and proxy `/mcp` and `/health` over HTTPS. Set
`MDL_MCP_ALLOWED_HOSTS=mdl.example.com,localhost:*,127.0.0.1:*` and
`MDL_MCP_ALLOWED_ORIGINS=https://mdl.example.com` for your actual domain.
Add any legitimate browser client origins explicitly; native clients usually send no Origin.
Preserve the `Authorization`, `Host`, `Mcp-Session-Id`, `MCP-Protocol-Version` and `Accept`
headers. The service is stateless HTTP and requires no sticky sessions.
There is no browser UI or CORS-enabled web client bundled with this server.

## Configuration

Pass `--env-file /absolute/path/.env` **before** the command to load dotenv configuration;
existing environment variables take precedence. No dotenv file is loaded implicitly.
Docker Compose reads `.env` and passes the variables declared in `compose.yaml`.

| Variable | Default / purpose |
| --- | --- |
| `MDL_MCP_TOKEN` / `MDL_MCP_TOKEN_FILE` | Required server bearer secret for HTTP, 32+ characters |
| `MDL_ACCESS_TOKEN` / `MDL_ACCESS_TOKEN_FILE` | Optional MyDramaList app API bearer token |
| `MDL_TOKEN_FILE` | `~/.mydramalist/token.json`; `/data/token.json` in Docker |
| `MDL_USERNAME` / `MDL_USERNAME_FILE` | Optional username for the login command |
| `MDL_PASSWORD` / `MDL_PASSWORD_FILE` | Optional password for the login command |
| `MDL_MCP_READ_ONLY` | `false`; true hides/disables writes |
| `MDL_MCP_HOST` | `127.0.0.1`; `0.0.0.0` inside Docker |
| `MDL_MCP_PORT` | `8000` |
| `MDL_MCP_ALLOWED_HOSTS` | Comma-separated localhost and 127.0.0.1 host/port patterns |
| `MDL_MCP_ALLOWED_ORIGINS` | Comma-separated localhost and 127.0.0.1 HTTP origins |
| `MDL_TIMEOUT` | `30` seconds per upstream HTTP request |
| `MDL_REQUEST_INTERVAL` | `0.25` seconds minimum between upstream calls |
| `MDL_IMPERSONATE` | SDK transport default `chrome` |
| `MDL_APP_VERSION` / `MDL_DEVICE_ID` / `MDL_API_KEY` | Optional SDK configuration overrides |

Use either a secret value or its `_FILE` variant, not both. `_FILE` supports mounted Docker
secrets; adjust Compose to mount those files and pass the corresponding variable. Keep `.env`
and token files out of source control and backups intended for sharing.

## Development and verification

```sh
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Tests exercise real MCP sessions, typed schemas, the real SDK with a mocked HTTP upstream,
authentication gating, read-only mode, partial profile updates, CRUD payloads, token clearing,
error redaction, and stdio/HTTP transports. They never publish real content or alter an account.
`doctor` performs live reads only and exits nonzero if any check fails. Account read/write
verification requires your credentials; no real account writes have been tested here.

Docker deployment needs verification on a Docker-enabled host; Docker was unavailable in
the build environment. See `VERIFICATION.md` for the recorded results.

## Troubleshooting

- `upstream_400`: the observed compatibility issue. Run `doctor`, check the current upstream
  release/spec and any required app-version headers. Do not assume login fixes this error;
  no authenticated live check has been performed. Changing this wrapper cannot by itself
  repair a rejected upstream API contract.
- `authentication_required`: run `login` on the host or configure an app bearer token.
- `upstream_401`: the client cleared the rejected token; log in again and restart.
- `upstream_403`: upstream access/transport was rejected. The client already uses its curl
  transport; verify the supported configuration with the upstream maintainer.
- `upstream_429`: wait, then increase `MDL_REQUEST_INTERVAL` if necessary.
- HTTP `401`: missing/incorrect MCP server bearer header.
- HTTP `421` or `403` with a valid MCP token: configure the allowed Host/Origin for your domain.
- `upstream_schema_changed`: the API response differs from the SDK models; check package updates.

## License

MIT. This project is not affiliated with MyDramaList. The upstream client is also MIT-licensed.
