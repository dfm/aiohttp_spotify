A trivial example of an app that uses aiohttp_spotify.
To run the test, [register a Spotify app](https://developer.spotify.com/dashboard/applications) with a redirect URI which is something like `http://localhost:5000/spotify/callback` where that `5000` can be a different port if you want.
Then copy the file `config.toml.template` to `config.toml` and add the relevant info for the app that you registered.
Then run:

```bash
python -m pip install -r requirements.txt
python demo.py
```

and navigate to http://localhost:5000/me.
This will ask you to authorize access to the Spotify API and then show you your Spotify user information.
