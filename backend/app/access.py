"""Optional HTTP Basic gate for a private, single-user deployment."""
import base64
import binascii
import os
import secrets

from starlette.responses import JSONResponse


class AccessGate:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'] == '/api/health':
            return await self.app(scope, receive, send)
        password = os.getenv('APP_PASSWORD', '')
        if not password:
            if os.getenv('REQUIRE_AUTH') == '1':
                response = JSONResponse({'detail': 'Deployment authentication is not configured'}, status_code=503)
                return await response(scope, receive, send)
            return await self.app(scope, receive, send)
        authorized = False
        try:
            header = dict(scope['headers']).get(b'authorization', b'')
            scheme, value = header.split(None, 1)
            if scheme.lower() == b'basic':
                username, supplied = base64.b64decode(value, validate=True).decode('utf-8').split(':', 1)
                authorized = secrets.compare_digest(username.encode(), os.getenv('APP_USERNAME', 'kun').encode()) and secrets.compare_digest(supplied.encode(), password.encode())
        except (ValueError, UnicodeDecodeError, binascii.Error):
            pass
        if not authorized:
            response = JSONResponse({'detail': 'Authentication required'}, status_code=401, headers={
                'WWW-Authenticate': 'Basic realm="Pickleball Kun AI", charset="UTF-8"',
                'Cache-Control': 'no-store',
            })
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)
