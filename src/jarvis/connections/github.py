"""GitHub connection inspection adapter for TB-04.

No repository/issues tool execution lives here. This adapter only validates
the connection and observes identity/permission metadata available from GitHub.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


_MAX_RESPONSE_BYTES = 65_536
_TIMEOUT_SECONDS = 10.0
_API_VERSION = "2026-03-10"


class GitHubConnectionError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubConnectionAdapter:
    provider_id = "github"

    def __init__(self, *, opener: Any = None):
        self._opener = opener if opener is not None else build_opener(_NoRedirect())

    def inspect(self, token: str) -> dict:
        if not isinstance(token, str) or not token.strip():
            raise GitHubConnectionError("AUTHENTICATION_REQUIRED")
        request = Request(
            "https://api.github.com/user",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token.strip()}",
                "X-GitHub-Api-Version": _API_VERSION,
                "User-Agent": "sofias-jarvis",
            },
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=_TIMEOUT_SECONDS) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
                headers = response.headers
        except HTTPError as exc:
            if exc.code == 401:
                raise GitHubConnectionError("AUTHENTICATION_FAILED") from None
            if exc.code in (403, 404):
                raise GitHubConnectionError("EXTERNAL_PERMISSION_INSUFFICIENT") from None
            if exc.code in (429, 500, 502, 503, 504):
                raise GitHubConnectionError("PROVIDER_UNAVAILABLE") from None
            raise GitHubConnectionError("CONNECTION_UNAVAILABLE") from None
        except (OSError, URLError, TimeoutError):
            raise GitHubConnectionError("PROVIDER_UNAVAILABLE") from None
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise GitHubConnectionError("INVALID_RESPONSE")
        try:
            data = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GitHubConnectionError("INVALID_RESPONSE") from None
        if not isinstance(data, dict):
            raise GitHubConnectionError("INVALID_RESPONSE")
        login, account_id = data.get("login"), data.get("id")
        if not isinstance(login, str) or not login or not isinstance(account_id, int):
            raise GitHubConnectionError("INVALID_RESPONSE")
        scopes = []
        raw_scopes = headers.get("X-OAuth-Scopes") if headers is not None else None
        if isinstance(raw_scopes, str):
            scopes = [x.strip() for x in raw_scopes.split(",") if x.strip()]
        return {
            "display_identity": login,
            "external_account_ref": str(account_id),
            "observed_permissions": sorted(set(scopes)),
            "availability": "available",
        }
