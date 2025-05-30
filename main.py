import threading
from suzu_twitch_api_server import Bot
from suzu_api import app, set_bot_instance  # Import Flask app and set_bot_instance function

def run_flask():
    """
    Run the Flask app on port 9001.
    """
    app.run(host='0.0.0.0', port=9001)

def run_twitch_bot():
    """
    Initialize and run the Twitch bot.
    """
    bot = Bot()  # Create an instance of the Twitch bot
    set_bot_instance(bot)  # Set the bot instance in the Flask app for control panel integration
    bot.run()  # Start the bot

if __name__ == "__main__":
    # Start the Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True  # Ensure the Flask thread exits when the main program exits
    flask_thread.start()
    
    # Run the Twitch bot in the main thread
    run_twitch_bot()