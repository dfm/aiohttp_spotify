__all__ = ["mock_api_app"]

import secrets

import yarl
from aiohttp import web


async def authorize(request: web.Request) -> web.Response:
    client_id = request.query.get("client_id")
    response_type = request.query.get("response_type")
    redirect_uri = request.query.get("redirect_uri")
    state = request.query.get("state")
    request.app["scope"] = request.query.get("scope")
    # show_dialog = request.query.get("show_dialog")

    if (
        client_id != request.app["client_id"]
        or response_type != "code"
        or redirect_uri != request.app["redirect_uri"]
    ):
        raise web.HTTPBadRequest(body="bad request")

    data = {}
    if state is not None:
        data["state"] = state

    if request.app.get("deny_access"):
        data["error"] = "access_denied"
    else:
        code = secrets.token_urlsafe()
        data["code"] = request.app["code"] = code

    return web.HTTPTemporaryRedirect(
        location=yarl.URL(redirect_uri).with_query(data)
    )


async def token(request: web.Request) -> web.Response:
    data = await request.post()
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")
    grant_type = data.get("grant_type")

    if (
        client_id != request.app["client_id"]
        or client_secret != request.app["client_secret"]
    ):
        raise web.HTTPBadRequest(body="bad request")

    if grant_type == "authorization_code":
        redirect_uri = data.get("redirect_uri")
        if redirect_uri != request.app["redirect_uri"]:
            raise web.HTTPBadRequest(body="invalid redirect")
        code = data.get("code")
        if code != request.app["code"]:
            raise web.HTTPBadRequest(body="invalid code")
        access_token = request.app["access_token"] = secrets.token_urlsafe()
        refresh_token = request.app["refresh_token"] = secrets.token_urlsafe()
        return web.json_response(
            dict(
                access_token=access_token,
                token_type="Bearer",
                scope=request.app["scope"],
                expires_in=3600,
                refresh_token=refresh_token,
            )
        )
    elif grant_type == "refresh_token":
        this_refresh_token = data.get("refresh_token")
        if this_refresh_token != request.app["refresh_token"]:
            raise web.HTTPBadRequest(body="invalid refresh_token")
        access_token = request.app["access_token"] = secrets.token_urlsafe()
        return web.json_response(
            dict(
                access_token=access_token,
                token_type="Bearer",
                scope=request.app["scope"],
                expires_in=3600,
            )
        )

    raise web.HTTPBadRequest(body="invalid grant type")


async def api(request: web.Request) -> web.Response:
    pass


def mock_api_app(
    client_id: str, client_secret: str, redirect_uri: str
) -> web.Application:
    app = web.Application()

    app["client_id"] = client_id
    app["client_secret"] = client_secret
    app["redirect_uri"] = redirect_uri

    app.router.add_routes(
        [
            web.get("/authorize", authorize, name="authorize"),
            web.post("/token", token, name="token"),
            web.route("*", "/api/{endpoint}", api, name="api"),
        ]
    )

    return app
