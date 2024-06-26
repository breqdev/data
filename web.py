import os
import redis
import time
import json
import requests
from flask import Flask, jsonify, redirect, request, send_file
from dotenv import load_dotenv

load_dotenv()

r = redis.from_url(os.environ.get("REDIS_URL"), decode_responses=True)

app = Flask(__name__)

@app.route("/")
def index():
    return send_file("static/index.html")

@app.route("/data")
def data():
    response = jsonify(
        {
            "name": "Brooke Chalmers",
            "music": {
                "id": r.get("spotify:playing:id"),
                "artist": json.loads(r.get("spotify:playing:artist") or "null"),
                "album": r.get("spotify:playing:album"),
                "track": r.get("spotify:playing:track"),
            },
            "git": {
                "repo": r.get("github:push:repo"),
                "branch": r.get("github:push:branch"),
                "commit": {
                    "message": r.get("github:push:commit:message"),
                    "sha": r.get("github:push:commit:sha"),
                    "url": r.get("github:push:commit:url"),
                },
            },
            "posts": {
                "id": r.get("twitter:tweet:id"),
                "text": r.get("twitter:tweet:text"),
                "created_at": r.get("twitter:tweet:created_at"),
            },
            "beacon": {
                "last_seen": r.get("beacon:last_seen"),
                "asn": r.get("beacon:asn"),
                "timezone": r.get("beacon:timezone"),
                "country": r.get("beacon:country"),
                "region": r.get("beacon:region"),
                "city": r.get("beacon:city"),
            },
            "battery": {
                "source": r.get("battery:source"),
                "percentage": r.get("battery:percentage"),
                "time_remaining": r.get("battery:time_remaining"),
            },
            "volume": r.get("volume"),
            "focused_app": r.get("focused_app"),
        }
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/login/spotify")
def spotify():
    return redirect(
        f"https://accounts.spotify.com/authorize?client_id={os.environ.get('SPOTIFY_CLIENT_ID')}&response_type=code&redirect_uri={os.environ.get('PUBLIC_URL')}/login/spotify/callback&scope=user-read-currently-playing%20user-read-playback-state"
    )


@app.route("/login/spotify/callback")
def spotify_callback():
    code = request.args.get("code")
    auth_response = requests.post(
        "https://accounts.spotify.com/api/token",
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"{os.environ.get('PUBLIC_URL')}/login/spotify/callback",
            "client_id": os.environ.get("SPOTIFY_CLIENT_ID"),
            "client_secret": os.environ.get("SPOTIFY_CLIENT_SECRET"),
        },
    )
    auth_response.raise_for_status()
    auth_token = auth_response.json()["access_token"]

    # see who it belongs to
    profile = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    profile.raise_for_status()
    user_id = profile.json()["id"]

    r.set(f"spotify:auth:{user_id}:access", auth_token, ex=3600)
    r.set(f"spotify:auth:{user_id}:refresh", auth_response.json()["refresh_token"])

    return "OK"


@app.route("/beacon", methods=["POST"])
def beacon():
    data = request.get_json()
    if data["token"] != os.environ.get("BEACON_TOKEN"):
        return "Unauthorized", 401

    r.set("beacon:last_seen", time.time())
    r.set("battery:source", data["battery"]["source"])
    r.set("battery:percentage", data["battery"]["percentage"])
    r.set("battery:time_remaining", data["battery"]["time_remaining"])
    r.set("volume", data["volume"])
    r.set("focused_app", data["focused_app"])

    # IP address tracking
    # trust that if the token's right, we're kind and aren't forging XFF :)
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        ip = xff.split(",")[0]
    else:
        ip = request.remote_addr

    resp = requests.get(f"http://ip-api.com/json/{ip}")
    resp.raise_for_status()

    ip_data = resp.json()

    r.set("beacon:asn", ip_data["as"])
    r.set("beacon:timezone", ip_data["timezone"])
    r.set("beacon:country", ip_data["countryCode"])
    r.set("beacon:region", ip_data["region"])
    r.set("beacon:city", ip_data["city"])

    return "OK"


if __name__ == "__main__":
    app.run()
