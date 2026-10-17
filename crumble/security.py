# SPDX-License-Identifier: Apache-2.0
import hashlib
import hmac
from urllib.parse import urlsplit

from starlette.responses import JSONResponse


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


def session_value(token):
    return hmac.new(token.encode(), b"crumble-browser-session/1", hashlib.sha256).hexdigest()


def authenticated(request, token):
    if not token:
        return True
    header = request.headers.get("authorization", "")
    return hmac.compare_digest(header, "Bearer " + token) or hmac.compare_digest(
        request.cookies.get("crumble_session", ""), session_value(token)
    )


def same_origin(request):
    origin = request.headers.get("origin")
    if not origin:
        return True  # CLI clients use bearer authentication.
    parsed = urlsplit(origin)
    return parsed.scheme in ("http", "https") and parsed.netloc == request.headers.get("host")
