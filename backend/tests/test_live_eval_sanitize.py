"""Offline tests for _safe_error sanitization in live_eval.

Verifies that raw exception messages (which may contain credentials,
API keys, or sensitive evidence) are never stored in report output.
"""
import asyncio, json, os, sys
from pathlib import Path

# Ensure backend/ is on sys.path so 'app' and 'scripts' resolve
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from scripts.live_eval import _safe_error


class _CredentialLeakError(Exception):
    """Simulated exception carrying a fake credential in its message."""
    pass


class TestSafeErrorSanitization:
    """Verify _safe_error never returns raw str(e)."""

    def test_key_error_returns_category_not_message(self):
        exc = KeyError("secret-api-key-value")
        result = _safe_error(exc)
        assert result == "key_error"
        assert "secret-api-key-value" not in result

    def test_value_error_returns_category_not_message(self):
        exc = ValueError("Bearer ya29.a0ARrrdM-secret-token data")
        result = _safe_error(exc)
        assert result == "value_error"
        assert "ya29" not in result
        assert "secret-token" not in result

    def test_type_error_returns_category_not_message(self):
        exc = TypeError("password='hunter2' is invalid")
        result = _safe_error(exc)
        assert result == "type_error"
        assert "hunter2" not in result

    def test_timeout_returns_timeout_category(self):
        result = _safe_error(asyncio.TimeoutError())
        assert result == "timeout"

    def test_connection_error_returns_category(self):
        exc = ConnectionError("connecting to https://user:pass@host")
        result = _safe_error(exc)
        assert result == "connection_error"
        assert "pass" not in result

    def test_permission_error_returns_category(self):
        exc = PermissionError("/root/.gcp/service-account-key.json")
        result = _safe_error(exc)
        assert result == "permission_error"
        assert "service-account-key" not in result

    def test_json_decode_error_returns_category(self):
        exc = json.JSONDecodeError("Expecting value", "<doc>", 0)
        result = _safe_error(exc)
        assert result == "json_decode_error"

    def test_custom_exception_returns_class_name_only(self):
        exc = _CredentialLeakError("Credential: AKIAIOSFODNN7EXAMPLE leaked!")
        result = _safe_error(exc)
        # For unknown exception types, only the class name is returned
        assert result == "_CredentialLeakError"
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "leaked" not in result

    def test_no_raw_str_in_result(self):
        """No matter what exception is thrown, the result must never
        contain the raw message text of the exception."""
        sensitive_values = [
            "AKIAIOSFODNN7EXAMPLE",
            "ya29.secret-token",
            "password=hunter2",
            "sk-ant-api03-verylongkey",
            "-----BEGIN PRIVATE KEY-----",
        ]
        for sv in sensitive_values:
            for exc_cls in [KeyError, ValueError, TypeError, RuntimeError, OSError]:
                exc = exc_cls(sv)
                result = _safe_error(exc)
                assert sv not in result, (
                    f"Sensitive value leaked for {exc_cls.__name__}: {result}"
                )
