# SPDX-License-Identifier: Apache-2.0
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlsplit

from starlette.responses import JSONResponse

SESSION_MAX_AGE = 28800


class BodyLimit:
    def __init__(self, app, max_bytes=170 * 1024 * 1024):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        count = 0
        limit = self.max_bytes if scope["path"] == "/api/ingest" else 21 * 1024 * 1024

        class TooLarge(Exception):
            pass

        async def bounded():
            nonlocal count
            message = await receive()
            if message["type"] == "http.request":
                count += len(message.get("body", b""))
                if count > limit:
                    raise TooLarge()
            return message

        try:
            await self.app(scope, bounded, send)
        except TooLarge:
            await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)


def secure_equal(a, b):
    """Compare UTF-8 credentials without failing on non-ASCII input."""
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    try:
        return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
    except UnicodeEncodeError:
        return False


def boolean_env(name, default=False):
    import os

    value = os.environ.get(name)
    if value is None:
        return default
    if value.lower() in ("1", "true", "yes"):
        return True
    if value.lower() in ("0", "false", "no"):
        return False
    raise ValueError(name + " must be true or false")


def session_value(token, timestamp=None):
    issued = int(time.time() if timestamp is None else timestamp)
    payload = f"v1.{issued}.{issued + SESSION_MAX_AGE}.{secrets.token_hex(16)}"
    signature = hmac.new(token.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).hexdigest()
    return payload + "." + signature


def valid_session(value, token, timestamp=None):
    """Enforce expiry server-side; token rotation changes the signing key."""
    if not isinstance(value, str) or len(value) > 256:
        return False
    try:
        version, issued, expires, nonce, signature = value.split(".")
        if version != "v1" or len(nonce) != 32 or any(c not in "0123456789abcdef" for c in nonce):
            return False
        if len(signature) != 64 or not issued.isascii() or not expires.isascii():
            return False
        issued_at, expires_at = int(issued), int(expires)
        stamp = int(time.time() if timestamp is None else timestamp)
        if expires_at - issued_at != SESSION_MAX_AGE or not issued_at <= stamp < expires_at:
            return False
        payload = ".".join((version, issued, expires, nonce))
        expected = hmac.new(token.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).hexdigest()
        return secure_equal(signature, expected)
    except (ValueError, TypeError, UnicodeEncodeError):
        return False


def authenticated(request, token):
    if not token:
        return True
    header = request.headers.get("authorization", "")
    return secure_equal(header, "Bearer " + token) or valid_session(
        request.cookies.get("crumble_session", ""), token
    )


def same_origin(request):
    origin = request.headers.get("origin")
    if not origin:
        return True  # CLI clients use bearer authentication.
    try:
        parsed = urlsplit(origin)
        return parsed.scheme in ("http", "https") and parsed.netloc == request.headers.get("host")
    except ValueError:
        return False
