from flask import Flask, request, jsonify
import requests
import os
import logging
import urllib.parse
from dotenv import load_dotenv
from flask import render_template

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN", "")

if not SPOTIFY_REFRESH_TOKEN:
    raise ValueError("SPOTIFY_REFRESH_TOKEN is not set. Ensure it is securely stored.")

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Spotify API Token Endpoint
TOKEN_URL = "https://accounts.spotify.com/api/token"
BASE_URL = "https://api.spotify.com/v1"

@app.route("/")
def test_interface():
    return render_template("test_interface.html")

def get_access_token():
    response = requests.post(TOKEN_URL, {
        "grant_type": "refresh_token",
        "refresh_token": SPOTIFY_REFRESH_TOKEN,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    })
    if response.status_code != 200:
        logging.error(f"Failed to refresh token: {response.status_code} - {response.text}")
        return None
    return response.json().get("access_token")

@app.route("/devices", methods=["GET"])
def get_devices():
    token = get_access_token()
    if not token:
        return jsonify({"error": "Could not refresh token"}), 401
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/me/player/devices", headers=headers)
    if response.status_code != 200:
        return jsonify({"error": "Failed to get devices"}), response.status_code
    return jsonify(response.json())

@app.route("/play", methods=["POST"])
def play_song():
    data = request.json
    token = get_access_token()
    
    # Validate access token first
    if not token:
        return jsonify({"error": "Could not refresh token"}), 401

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # New: Direct URI playback
    if data.get("track_uri"):
        play_url = f"{BASE_URL}/me/player/play"
        if data.get("device_id"):
            play_url += f"?device_id={data['device_id']}"
        
        play_response = requests.put(
            play_url,
            headers=headers,
            json={"uris": [data["track_uri"]]}
        )
        
        if play_response.status_code in [200, 204]:
            return jsonify({
                "message": "Song playing",
                "uri": data["track_uri"]
            })
        
        error_message = play_response.json().get("error", {}).get("message", "Unknown error")
        return jsonify({
            "error": "Failed to play song",
            "details": error_message
        }), 400

    # Existing search-based playback (maintained for AI compatibility)
    # Validate input
    if not data or "song_name" not in data or "artist" not in data:
        return jsonify({"error": "Missing required fields: song_name and artist"}), 400
    
    song_name = data.get("song_name")
    artist = data.get("artist")
    device_id = data.get("device_id")
    
    # Build search query with both track and artist
    search_query = f"track:{song_name} artist:{artist}"
    encoded_query = urllib.parse.quote(search_query)
    
    # Search for track
    search_response = requests.get(
        f"{BASE_URL}/search?q={encoded_query}&type=track",
        headers=headers
    )
    
    if search_response.status_code != 200:
        return jsonify({"error": "Failed to search for song"}), 400
    
    tracks = search_response.json().get("tracks", {}).get("items", [])
    if not tracks:
        return jsonify({"error": f"Song '{song_name}' by {artist} not found"}), 404
    
    # Get the most popular match if multiple results
    sorted_tracks = sorted(tracks, key=lambda x: x["popularity"], reverse=True)
    song_uri = sorted_tracks[0]["uri"]
    
    # Play on specific device
    play_url = f"{BASE_URL}/me/player/play"
    if device_id:
        play_url += f"?device_id={device_id}"
    
    play_response = requests.put(
        play_url,
        headers=headers,
        json={"uris": [song_uri]}
    )
    
    if play_response.status_code not in [200, 204]:
        error_message = play_response.json().get("error", {}).get("message", "Unknown error")
        return jsonify({
            "error": "Failed to play song",
            "details": error_message
        }), 400
    
    return jsonify({
        "message": "Song playing",
        "song": song_name,
        "artist": artist,
        "uri": song_uri
    })

@app.route("/search", methods=["POST"])
def search_tracks():
    data = request.json
    if not data or "query" not in data:
        return jsonify({"error": "Missing search query"}), 400
    
    token = get_access_token()
    if not token:
        return jsonify({"error": "Could not refresh token"}), 401
    
    headers = {"Authorization": f"Bearer {token}"}
    encoded_query = urllib.parse.quote(data["query"])
    
    search_response = requests.get(
        f"{BASE_URL}/search?q={encoded_query}&type=track&limit=5",
        headers=headers
    )
    
    if search_response.status_code != 200:
        return jsonify({"error": "Search failed"}), 400
    
    tracks = []
    for item in search_response.json().get("tracks", {}).get("items", []):
        track = {
            "name": item["name"],
            "artist": ", ".join([a["name"] for a in item["artists"]]),
            "uri": item["uri"],
            "album_art": item["album"]["images"][0]["url"] if item["album"]["images"] else None,
            "preview_url": item["preview_url"]
        }
        tracks.append(track)
    
    return jsonify({"results": tracks})


@app.route("/authorize")
def authorize():
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": "http://localhost:8631/callback",
        "scope": "user-modify-playback-state user-read-playback-state user-read-currently-playing",
        "show_dialog": "true"
    })
    return f'<a href="{auth_url}">Authorize Spotify</a>'
@app.route("/callback")
def callback():
    code = request.args.get("code")
    response = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:8631/callback",
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }).json()
    
    refresh_token = response.get("refresh_token")
    return f"Refresh Token: {refresh_token} (Save this in your .env file as SPOTIFY_REFRESH_TOKEN)"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8631, debug=True)
