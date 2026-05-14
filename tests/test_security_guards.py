import pytest

from vigilancia_multiagente.api.security.startup_guard import validate_external_url, validate_stdio_command


def test_validate_external_url_accepts_https_and_rejects_internal():
    validate_external_url("https://example.com")
    with pytest.raises(RuntimeError):
        validate_external_url("ftp://example.com")


def test_validate_stdio_command_rejects_shell_injection():
    validate_stdio_command("python tool.py")
    with pytest.raises(RuntimeError):
        validate_stdio_command("python tool.py; rm -rf /")


