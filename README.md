# Project NekoNova

Project NekoNova is currently a work in progress AI chatbot for twitch and discord. This README will guide you through setup, configuration, and usage.

## Getting Started

You only need the environment variables you want to use to run the app.
so if you just want to use the llm model, you only need to set the environment variables for the llm model.
if you want to use the discord api, you only need to set the environment variables for the discord api.

### Prerequisites

- [Node.js, Python]

### Setup


git clone https://github.com/yourusername/ProjectNekoNova.git
cd ProjectNekoNova
create a .env file
add your environment variables shown below
create your virtual environment
run pip install -r requirements.txt
cd website\suzu-react-site
npm install

### Environment Variables

Create a `.env` file in the project root. Use the template below:

```env
# .env.example

GEMINI_API_KEY=your_gemini_api_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REFRESH_TOKEN=your_spotify_refresh_token
TWITCH_CLIENT_SECRET=your_twitch_client_secret
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_TOKEN=your_twitch_token # This is the access token that you get from running temp.py
TWITCH_CHANNEL=the_channel_you_want_to_run_the_bot_in
DISCORD_TOKEN=your_discord_token
SUZU_PROMPT=the_ai_prompt_you_want_to_use
```

**Note:** Replace the placeholder values with your actual credentials.

### Running the Project

For full fuctionality run the following commands
python suzu_api.py # this is the bot's main api interface
python suzu_twitch_api_server.py # this is the twitch api server that handles twitch
python discord_api.py   # this is the discord api server that handles discord
cd website\suzu-react-site  # this is the react website
npm run dev # this is to run the website which is the frontend and turn the bot on and off for currently just twitch

Refer to the [documentation](docs/) for more details on each module.

## Contributing

Pull requests are welcome. For major changes, open an issue first.
