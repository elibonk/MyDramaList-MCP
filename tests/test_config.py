import pytest

from mydramalist_mcp.config import Settings, secret
from mydramalist_mcp.server import BearerAuth


def test_secret_file_and_conflicting_values(tmp_path, monkeypatch):
    path = tmp_path / "secret"
    path.write_text("test-secret\n")
    monkeypatch.setenv("TEST_SECRET_FILE", str(path))
    assert secret("TEST_SECRET") == "test-secret"
    monkeypatch.setenv("TEST_SECRET", "value")
    with pytest.raises(ValueError, match="not both"):
        secret("TEST_SECRET")


def test_short_http_token_rejected():
    with pytest.raises(ValueError, match="at least 32"):
        BearerAuth(None, "short")


def test_settings_repr_does_not_expose_secrets():
    settings = Settings(access_token="mdl-secret", server_token="mcp-secret")
    assert "mdl-secret" not in repr(settings)
    assert "mcp-secret" not in repr(settings)


def test_invalid_boolean(monkeypatch):
    monkeypatch.setenv("MDL_MCP_READ_ONLY", "yesplease")
    with pytest.raises(ValueError, match="true or false"):
        Settings.from_env()
