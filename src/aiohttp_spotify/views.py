__all__ = ["routes"]

import secrets
import time
from typing import Optional, Dict, Any

import yarl
import aiohttp_session
from aiohttp import web, ClientSession

from . import api

routes = web.RouteTableDef()


def get_redirect_uri(request: web.Request) -> str:
    """Get the redirect URI that the Spotify API expects"""
    return str(
        request.url.with_path(str(request.app.router["callback"].url_for()))
    )


@routes.get("/auth", name="auth")
async def auth(request: web.Request) -> web.Response:
    session = await aiohttp_session.get_session(request)
    session["spotify_redirect_on_auth"] = request.query.get("redirect")

    # Generate a state token
    state = secrets.token_urlsafe()
    session["spotify_state"] = state

    # Construct the API OAuth2 URL
    args = dict(
        client_id=request.app["spotify_client_id"],
        response_type="code",
        redirect_uri=get_redirect_uri(request),
        state=state,
    )
    scope = request.app.get("spotify_scope")
    if scope is not None:
        args["scope"] = scope
    location = yarl.URL(api.SPOTIFY_AUTH_URL).with_query(*args)

    return web.HTTPTemporaryRedirect(location=str(location))


@routes.get("/callback", name="callback")
async def callback(request: web.Request) -> web.Response:
    error = request.query.get("error")
    if error is not None:
        return await handle_error(request, error)

    code = request.query.get("code")
    if code is None:
        return await handle_error(request)

    session = await aiohttp_session.get_session(request)

    # Check that the 'state' matches
    state = session.pop("spotify_state")
    returned_state = request.query.get("spotify_state")
    if state is None or returned_state is None or state != returned_state:
        return await handle_error(request)

    # Construct the request to get the tokens
    data = dict(
        client_id=request.app.get("spotify_client_id"),
        client_secret=request.app.get("spotify_client_secret"),
        redirect_uri=get_redirect_uri(request),
        grant_type="authorization_code",
        code=request.query["code"],
    )
    async with ClientSession(raise_for_status=True) as client:
        async with client.post(api.SPOTIFY_TOKEN_URL, json=data) as response:
            user_data = await response.json()

    # Expires *at* is more useful than *in* for us...
    user_data["expires_at"] = time.time() + int(user_data["expires_in"])

    return await handle_success(request, user_data)


async def handle_error(
    request: web.Request, error: Optional[str] = None
) -> web.Response:
    if error is None:
        error = "Invalid request"
    handler = request.app.get("spotify_on_error")
    if handler is not None:
        return await handler(request, error)
    raise web.HTTPInternalServerError(
        text=f"Unhandled authorization error {error}"
    )


async def handle_success(
    request: web.Request, user_data: Dict[str, Any]
) -> web.Response:
    handler = request.app.get("spotify_on_success")
    if handler is not None:
        return await handler(request, user_data)
    return web.json_response(user_data)
