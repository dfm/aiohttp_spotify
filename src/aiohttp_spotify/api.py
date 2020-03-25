import time
from contextlib import asynccontextmanager
from typing import Any, Optional, Callable, Awaitable

import asyncio
from aiohttp import ClientSession

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"


class SpotifyAuth:
    def __init__(
        self,
        *,
        user_id: Any,
        access_token: str,
        refresh_token: str,
        expires_at: float,
        update_handler: Optional[
            Callable[[Any, str, float], Awaitable]
        ] = None,
    ):
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at
        self.update_handler = update_handler

    async def update(self, *, access_token: str, expires_at: float):
        self.access_token = access_token
        self.expires_at = expires_at
        if self.update_handler is not None:
            await self.update_handler(
                self.user_id, self.access_token, self.expires_at
            )


class SpotifyClient:
    def __init__(self, *, client_id: str, client_secret: str, **kwargs):
        self.client_id = client_id
        self.client_secret = client_secret
        self._client_session = None
        self.kwargs = kwargs

    async def __aenter__(self):
        self._client_session = ClientSession(**self.kwargs)
        return self

    async def __aexit__(self):
        await self.client_session.close()
        self.client_session = None

    @property
    def client_session(self) -> ClientSession:
        if self._client_session is None:
            raise AttributeError(
                "SpotifyClient must be run as a context manager"
            )
        return self._client_session

    async def refresh(self, auth: SpotifyAuth) -> str:
        data = dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            grant_type="refresh_token",
            refresh_token=auth.refresh_token,
        )
        async with self.client_session.post(
            SPOTIFY_TOKEN_URL, json=data
        ) as response:
            response.raise_for_status()
            user_data = await response.json()
        token = user_data["access_token"]
        expires_at = time.time() + int(user_data["expires_in"])
        await auth.update(access_token=token, expires_at=expires_at)
        return token

    async def get_token(self, auth: SpotifyAuth) -> str:
        current_time = time.time()

        if auth.expires_at - current_time <= 60:
            return await self.refresh(auth)

        return auth.access_token

    @asynccontextmanager
    async def request(
        self,
        auth: SpotifyAuth,
        endpoint: str,
        *,
        method: str = "GET",
        **payload,
    ):
        token = await self.get_token(auth)
        headers = {"Authorization": f"Bearer {token}"}
        async with self.client_session.request(
            method, SPOTIFY_API_URL + endpoint, headers=headers, json=payload
        ) as response:
            if response.status != 429:
                response.raise_for_status()
                yield response
                return

        # If we got here, we were rate limited!
        await asyncio.sleep(int(response.headers["Retry-After"]))
        async with self.request(
            auth, endpoint, method=method, **payload
        ) as response:
            yield response
