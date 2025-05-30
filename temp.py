import requests
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
REDIRECT_URI = "http://localhost"  # Or your redirect URI
AUTHORIZATION_CODE = os.getenv("AUTHORIZATION_CODE")#"YOUR_AUTHORIZATION_CODE"  # Replace with the code you received

token_url = f"https://id.twitch.tv/oauth2/token?client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&code={AUTHORIZATION_CODE}&grant_type=authorization_code&redirect_uri={REDIRECT_URI}"

print(f"Authorization Code URL: https://id.twitch.tv/oauth2/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=chat:read+chat:edit")

response = requests.post(token_url)
#response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
access_token = response.json().get("access_token")

if access_token:
    print(f"Twitch Access Token: {access_token}")
    # Store the access_token in your environment variables.
else:
    print("Failed to obtain access token.")