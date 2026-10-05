import base64
import json
from dataclasses import replace

import httpx
import pytest
import pytest_asyncio
from jsonschema import Draft202012Validator
from mcp.shared.memory import create_connected_server_and_client_session
from mdl import AsyncMDLClient, InMemoryTokenStore
from starlette.testclient import TestClient

from mydramalist_mcp.backend import Backend, BackendError
from mydramalist_mcp.catalog import Operation, operations
from mydramalist_mcp.config import Settings
from mydramalist_mcp.server import create_server, http_app


@pytest_asyncio.fixture
async def harness():
    requests = []
    response = {"status": 200, "body": {"id": 686, "title": "Example Drama"}}

    def handler(request):
        requests.append(request)
        return httpx.Response(response["status"], json=response["body"])

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = AsyncMDLClient(http_client=http, token_store=InMemoryTokenStore("test-mdl-token"))
    settings = Settings(request_interval=0, server_token="s" * 40)
    backend = Backend(settings, client)
    yield settings, backend, requests, response
    await http.aclose()


def payload(reply):
    assert reply.structuredContent == json.loads(reply.content[0].text)
    return reply.structuredContent


async def test_schema_allowlist(harness):
    settings, backend, _, _ = harness
    server = create_server(settings, backend)
    async with create_connected_server_and_client_session(server) as session:
        tools = (await session.list_tools()).tools
        names = {t.name for t in tools}
        assert names == {op.name for op in operations()} | {
            "mdl_server_status",
            "mdl_capabilities",
            "mdl_upload_image",
        }
        for tool in tools:
            Draft202012Validator.check_schema(tool.inputSchema)
            assert tool.annotations.openWorldHint is not None
        assert not any("password" in name or "deactivate" in name for name in names)
        review = next(t for t in tools if t.name == "mdl_reviews_submit")
        assert "parent_id" in review.inputSchema["required"]
        assert review.annotations.readOnlyHint is False
        delete = next(t for t in tools if t.name == "mdl_reviews_delete")
        assert delete.annotations.destructiveHint is True


async def test_public_read_and_status_never_expose_tokens(harness):
    settings, backend, requests, response = harness
    response["body"]["access_token"] = "upstream-secret"
    response["body"]["nested"] = {"refresh_token": "another-secret", "value": 1}
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        reply = await s.call_tool("mdl_titles_get_title", {"title_id": 686})
        assert not reply.isError
        assert payload(reply)["data"]["title"] == "Example Drama"
        assert "upstream-secret" not in json.dumps(payload(reply))
        assert "another-secret" not in json.dumps(payload(reply))
        status = payload(await s.call_tool("mdl_server_status", {}))
        assert status["data"]["authenticated"] is True
        assert "test-mdl-token" not in json.dumps(status)
    assert requests[0].url.path == "/v1/titles/686"
    assert requests[0].url.params["expand"] == "1"
    # The upstream SDK explicitly leaves the public title endpoint unauthenticated.
    assert "authorization" not in requests[0].headers


async def test_search_filters_and_pagination(harness):
    settings, backend, requests, response = harness
    response["body"] = [{"id": 1, "title": "Signal"}]
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        reply = await s.call_tool(
            "mdl_search_titles",
            {"query": "Signal", "page": 2, "synopsis": True, "filters": {"sort": "top"}},
        )
        assert payload(reply)["data"][0]["title"] == "Signal"
        bad = await s.call_tool(
            "mdl_search_titles", {"query": "Signal", "filters": {"q": "X", "page": 3}}
        )
        assert bad.isError
    request = requests[0]
    assert request.method == "POST"
    assert dict(request.url.params) == {
        "edge": "1",
        "q": "Signal",
        "page": "2",
        "sort": "top",
        "synopsis": "1",
    }
    assert len(requests) == 1


@pytest.mark.parametrize(
    "tool,arguments",
    [
        ("mdl_titles_get_title", {"title_id": "../../users/settings"}),
        ("mdl_titles_get_title", {"title_id": -1}),
        ("mdl_titles_get_title", {"title_id": True}),
        ("mdl_watchlist_fetch", {"status": "../../users/settings"}),
        ("mdl_reviews_submit", {"headline": "H", "review": "R"}),
        ("mdl_reviews_submit", {"parent_id": 1, "headline": "H", "review": "R", "overall": 11}),
        ("mdl_watchlist_remove", {"ids": []}),
        ("mdl_comments_post", {"pid": 1, "ptype": "title", "message": ""}),
    ],
)
async def test_invalid_arguments_do_not_call_upstream(harness, tool, arguments):
    settings, backend, requests, _ = harness
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        assert (await s.call_tool(tool, arguments)).isError
    assert not requests


async def test_missing_auth_blocks_writes_but_allows_public_reads(harness):
    settings, backend, requests, _ = harness
    backend.client.tokens.clear()
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        reply = await s.call_tool("mdl_custom_lists_create", {"name": "Weekend"})
        assert reply.isError
        assert payload(reply)["error"]["code"] == "authentication_required"
        assert not (await s.call_tool("mdl_titles_get_title", {"title_id": 686})).isError
    assert len(requests) == 1


async def test_read_only_hides_and_enforces_writes(harness):
    settings, original, requests, _ = harness
    settings = replace(settings, read_only=True)
    backend = Backend(settings, original.client)
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        names = {t.name for t in (await s.list_tools()).tools}
        assert "mdl_custom_lists_create" not in names
        assert "mdl_upload_image" not in names
        assert "mdl_watchlist_fetch" in names
    with pytest.raises(BackendError, match="Writes are disabled"):
        await backend.call(Operation("watchlist", "remove", write=True, private=True), {"ids": [1]})
    assert not requests


@pytest.mark.parametrize(
    "tool,arguments,path,method,expected_body,response_body",
    [
        (
            "mdl_watchlist_add",
            {"item": {"id": 686, "episode_seen": 2}},
            "/v1/sync/mylist",
            "POST",
            {"id": 686, "episode_seen": 2},
            {"success": {"titles": 1}},
        ),
        (
            "mdl_watchlist_remove",
            {"ids": [686, 123]},
            "/v1/sync/mylist",
            "DELETE",
            [{"id": 686}, {"id": 123}],
            {"success": {"titles": 2}},
        ),
        (
            "mdl_custom_lists_add_item",
            {"list_id": 4, "entry_id": 686},
            "/v1/lists/4/add",
            "POST",
            {"entry_id": 686},
            True,
        ),
        (
            "mdl_custom_lists_edit",
            {"list_id": 4, "fields": {"name": "Weekend"}},
            "/v1/lists/4",
            "PATCH",
            {"name": "Weekend"},
            {"id": 4, "name": "Weekend"},
        ),
        (
            "mdl_comments_post",
            {"pid": 4, "ptype": "clist", "message": "Hello"},
            "/v1/comments",
            "POST",
            {"pid": 4, "ptype": "clist", "message": "Hello"},
            {},
        ),
        (
            "mdl_reviews_edit",
            {"review_id": 7, "fields": {"ratings": {"overall": 8}}},
            "/v1/reviews/7",
            "PATCH",
            {"ratings": {"overall": 8}},
            "updated",
        ),
        (
            "mdl_account_update_profile_info",
            {"location": "Seoul"},
            "/v1/users/settings",
            "PATCH",
            {"location": "Seoul"},
            "updated",
        ),
        (
            "mdl_feeds_create",
            {"message": "Watching Signal", "privacy": "friends"},
            "/v1/feeds",
            "POST",
            {"message": "Watching Signal", "privacy": "friends", "spoiler": False},
            {},
        ),
    ],
)
async def test_write_payloads(harness, tool, arguments, path, method, expected_body, response_body):
    # These verify SDK forwarding, not that the private upstream accepts every field.
    settings, backend, requests, response = harness
    response["body"] = response_body
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        reply = await s.call_tool(tool, arguments)
        assert not reply.isError, payload(reply)
    request = requests[0]
    assert request.method == method
    assert request.url.path == path
    assert json.loads(request.content) == expected_body
    assert request.headers["authorization"] == "Bearer test-mdl-token"
    assert len(requests) == 1


async def test_review_submit_ratings_nested_correctly(harness):
    settings, backend, requests, response = harness
    response["body"] = "created"
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        reply = await s.call_tool(
            "mdl_reviews_submit",
            {
                "parent_id": 686,
                "headline": "Thoughts",
                "review": "Great cast",
                "overall": 8.5,
                "completed": True,
                "episodes_seen": 16,
            },
        )
        assert not reply.isError
    body = json.loads(requests[0].content)
    assert body["parent_id"] == 686
    assert body["ratings"]["overall"] == 8.5
    assert body["episodes_seen"] == 16
    assert "overall" not in {k: v for k, v in body.items() if k != "ratings"}


async def test_raw_profile_response_secrets_are_removed_recursively(harness):
    settings, backend, _, response = harness
    response["body"] = {"access_token": "private", "nested": {"password": "private", "ok": True}}
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        reply = await s.call_tool("mdl_account_update_profile_info", {"location": "Seoul"})
        assert not reply.isError
        assert payload(reply)["data"] == {"nested": {"ok": True}}


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500])
async def test_upstream_error_is_flagged_redacted_and_never_retried(harness, status):
    settings, backend, requests, response = harness
    response.update(status=status, body={"message": "SECRET upstream body"})
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        reply = await s.call_tool("mdl_watchlist_remove", {"ids": [686]})
        assert reply.isError
        assert payload(reply)["error"]["code"] == f"upstream_{status}"
        assert "SECRET" not in json.dumps(payload(reply))
        if status == 401:
            assert not payload(await s.call_tool("mdl_server_status", {}))["data"]["authenticated"]
    assert len(requests) == 1


async def test_schema_change_is_not_success(harness):
    settings, backend, requests, response = harness
    response["body"] = {"renamed_id": 1}
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        reply = await s.call_tool("mdl_titles_get_title", {"title_id": 1})
        assert reply.isError
        assert payload(reply)["error"]["code"] == "upstream_schema_changed"
    assert len(requests) == 1


async def test_upload_rejects_invalid_data_without_io(harness):
    settings, backend, requests, _ = harness
    async with create_connected_server_and_client_session(create_server(settings, backend)) as s:
        for data in ["not base64!", base64.b64encode(b"not an image").decode()]:
            reply = await s.call_tool(
                "mdl_upload_image", {"target": "profile", "image_base64": data}
            )
            assert reply.isError
    assert not requests


async def test_http_auth_host_origin_and_protocol(harness):
    settings, backend, _, _ = harness
    server = create_server(settings, backend)
    with TestClient(http_app(server, settings), base_url="http://localhost:8000") as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.post("/mcp", json={}).status_code == 401
        assert client.get("/mcp", headers={"Authorization": "Bearer wrong"}).status_code == 401
        headers = {
            "Authorization": f"Bearer {settings.server_token}",
            "Accept": "application/json, text/event-stream",
        }
        init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        }
        reply = client.post("/mcp", headers=headers, json=init)
        assert reply.status_code == 200, reply.text
        assert reply.json()["result"]["serverInfo"]["name"] == "MyDramaList"
        assert (
            client.post("/mcp", headers={**headers, "Host": "evil.example"}, json=init).status_code
            == 421
        )
        assert (
            client.post(
                "/mcp", headers={**headers, "Origin": "https://evil.example"}, json=init
            ).status_code
            == 403
        )
