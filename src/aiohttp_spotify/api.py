__all__ = ["SpotifyAuth", "SpotifyClient"]

import asyncio
import json
import time
from typing import Any, Mapping, NamedTuple, Tuple

from aiohttp import ClientSession

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"


class SpotifyAuth(NamedTuple):
    access_token: str
    refresh_token: str
    expires_at: int


class SpotifyResponse(NamedTuple):
    auth_changed: bool
    auth: SpotifyAuth
    status: int
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> Mapping[str, Any]:
        print(self.body)
        return json.loads(self.body)


class SpotifyClient:
    def __init__(self, *, client_id: str, client_secret: str, **kwargs):
        self.client_id = client_id
        self.client_secret = client_secret
        self.kwargs = kwargs

    async def update_auth(
        self, session: ClientSession, auth: SpotifyAuth
    ) -> SpotifyAuth:
        data = dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            grant_type="refresh_token",
            refresh_token=auth.refresh_token,
        )
        async with session.post(SPOTIFY_TOKEN_URL, json=data) as response:
            response.raise_for_status()
            user_data = await response.json()
        return SpotifyAuth(
            access_token=user_data["access_token"],
            refresh_token=auth.refresh_token,
            expires_at=int(time.time()) + int(user_data["expires_in"]),
        )

    async def request(
        self,
        session: ClientSession,
        auth: SpotifyAuth,
        endpoint: str,
        *,
        method: str = "GET",
        **payload,
    ) -> SpotifyResponse:
        # Update the access token if it is to expire soon
        auth_changed = False
        if auth.expires_at - time.time() <= 60:
            auth_changed = True
            auth = await self.update_auth(session, auth)

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {auth.access_token}",
        }
        async with session.request(
            method, SPOTIFY_API_URL + endpoint, headers=headers, data=payload
        ) as response:
            if response.status == 429:
                # We got rate limited!
                await asyncio.sleep(int(response.headers["Retry-After"]))
                return await self.request(
                    session, auth, endpoint, method=method, **payload
                )

            response.raise_for_status()

            return SpotifyResponse(
                auth_changed,
                auth,
                response.status,
                response.headers,
                await response.read(),
            )
