import os
import requests
import redis
import schedule
import json
import time
from dotenv import load_dotenv

load_dotenv()

r = redis.from_url(os.environ.get("REDIS_URL"), decode_responses=True)


def refresh_spotify_token():
    refresh_token = r.get(f"spotify:auth:{os.environ.get('SPOTIFY_USER_ID')}:refresh")
    if not refresh_token:
        return

    auth_response = requests.post(
        "https://accounts.spotify.com/api/token",
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": os.environ.get("SPOTIFY_CLIENT_ID"),
            "client_secret": os.environ.get("SPOTIFY_CLIENT_SECRET"),
        },
    )
    auth_response.raise_for_status()
    r.set(
        f"spotify:auth:{os.environ.get('SPOTIFY_USER_ID')}:access",
        auth_response.json()["access_token"],
        ex=3600,
    )

    if auth_response.json().get("refresh_token"):
        r.set(
            f"spotify:auth:{os.environ.get('SPOTIFY_USER_ID')}:refresh",
            auth_response.json()["refresh_token"],
        )


def get_playing():
    try:
        auth_token = r.get(f"spotify:auth:{os.environ.get('SPOTIFY_USER_ID')}:access")

        if not auth_token:
            refresh_spotify_token()
            auth_token = r.get(f"spotify:auth:{os.environ.get('SPOTIFY_USER_ID')}:access")

        if not auth_token:
            return

        playing = requests.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers={"Authorization": f"Bearer {auth_token}", "Accept": "application/json"},
        )
        playing.raise_for_status()

        if playing.status_code == 204:
            r.delete("spotify:playing:id")
            r.delete("spotify:playing:artist")
            r.delete("spotify:playing:album")
            r.delete("spotify:playing:track")
            return

        data = playing.json()
        r.set("spotify:playing:id", data["item"]["id"])
        r.set(
            "spotify:playing:artist",
            json.dumps([artist["name"] for artist in data["item"]["artists"]]),
        )
        r.set("spotify:playing:album", data["item"]["album"]["name"])
        r.set("spotify:playing:track", data["item"]["name"])
    except Exception as e:
        print(e)


schedule.every(15).seconds.do(get_playing)


def get_github_activity():
    try:
        activity = requests.get(
            f"https://api.github.com/users/{os.environ.get('GITHUB_USER_ID')}/events",
        )
        activity.raise_for_status()

        events = activity.json()

        for event in events:
            if event["type"] == "PushEvent":
                r.set("github:push:repo", event["repo"]["name"])
                r.set(
                    "github:push:branch",
                    event["payload"]["ref"].removeprefix("refs/heads/"),
                )
                r.set(
                    "github:push:commit:message", event["payload"]["commits"][0]["message"]
                )
                r.set("github:push:commit:sha", event["payload"]["commits"][0]["sha"])
                r.set(
                    "github:push:commit:url",
                    f"https://github.com/{event['repo']['name']}/commit/{event['payload']['commits'][0]['sha']}",
                )
                break
    except Exception as e:
        print(e)


schedule.every(1).minutes.do(get_github_activity)


def get_tweets():
    try:
        resp = requests.get(
            f"https://tacobelllabs.net/api/v1/accounts/{os.getenv('MASTODON_USER_ID')}/statuses"
        )
        resp.raise_for_status()

        tweets = resp.json()
        tweet = tweets[0]

        r.set("twitter:tweet:id", tweet["id"])
        r.set("twitter:tweet:text", tweet["content"])
        r.set("twitter:tweet:created_at", tweet["created_at"])
    except Exception as e:
        print(e)


schedule.every(1).minutes.do(get_tweets)


while True:
    schedule.run_pending()
    time.sleep(1)
