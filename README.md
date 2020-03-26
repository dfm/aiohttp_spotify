An async Python interface to the Spotify API using [aiohttp](https://docs.aiohttp.org).

*Note: This is alpha software. Use at your own risk.*

Installation
------------

To install, use pip:

```bash
python -m pip install aiohttp_spotify
```

It's best if you also install and use [aiohttp-session](https://github.com/aio-libs/aiohttp-session).

Usage
-----

To add the OAuth flow to your app:

```python
from aiohttp import web
import aiohttp_spotify

async def handle_auth(request: web.Request, auth: aiohttp_spotify.SpotifyAuth):
    # Store the `auth` object for use later

app = web.Application()
app["spotify_app"] = aiohttp_spotify.spotify_app(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    handle_auth=handle_auth,
)
app.add_subapp("/spotify", app["spotify_app"])
```

Then you can make calls to the API as follows:

```python
from aiohttp import ClientSession

async def call_api(request: web.Request) -> web.Response:
    async with ClientSession() as session:
        response = app["spotify_app"]["spotify_client"].request(
            session, auth, "/me"
        )
    
    # The auth object will be updated as tokens expire so you should
    # update this however you have it stored:
    if response.auth_changed:
        await handle_auth(request, response.auth)
        
    return web.json_request(response.json())
```

where `auth` is the `SpotifyAuth` object from above.

Take a look at [the demo directory](/demo) for a more complete example.
