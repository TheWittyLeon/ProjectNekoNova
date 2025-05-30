import os
import pyttsx3  # Offline TTS
from gtts import gTTS  # Online TTS
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai  # Gemini API
import requests
from suzu_twitch_api_server import get_bot_instance, set_bot_instance
import ollama

# Load prompts from .env
suzu_prompt = os.getenv("SUZU_PROMPT", "Default Suzu Prompt")
suzu_prompt_2 = os.getenv("SUZU_PROMPT_2")

bot_instance = get_bot_instance()  # Initialize bot instance from suzu_twitch_api_server

# Global variable to track bot's active state
is_bot_active = False

# Load API Keys from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Flask App Setup
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Initialize TTS engine (Offline)
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Adjust speed
engine.setProperty('volume', 1.0)  # Set volume

@app.route('/')
def index():
    return render_template('index.html')

def set_bot_instance(bot):
    global bot_instance
    bot_instance = bot
    print(f"Bot instance set: {bot_instance}") #Debug output

@app.route('/bot/control-panel')
def bot_control_panel():
    return render_template('bot_control.html')

@app.route('/debug/bot-status')
def debug_bot_status():
    global bot_instance
    return jsonify({
        "bot_initialized": bot_instance is not None,
        "bot_type": str(type(bot_instance)) if bot_instance else "None",
        "is_active": bot_instance.is_active if bot_instance else False
    })

@app.route('/debug/init-dummy-bot')
def init_dummy_bot():
    global bot_instance
    if not bot_instance:
        from suzu_twitch_api_server import Bot  # Import the Bot class
        dummy_bot = Bot()  # Create a new bot instance
        set_bot_instance(dummy_bot)  # Set the new bot instance
        bot_instance = dummy_bot  # Update the global bot_instance
        return jsonify({"status": "Dummy bot initialized"})
    return jsonify({"status": "Bot already initialized"})

@app.route('/bot/status', methods=['GET'])
def get_bot_status():
    """Get the bot's active status."""
    global is_bot_active
    status = "active" if is_bot_active else "inactive"
    return jsonify({"status": status})

@app.route('/bot/control', methods=['POST'])
def control_bot():
    """Control the bot's active status."""
    global is_bot_active

    data = request.json
    if not data or "action" not in data:
        return jsonify({"error": "Missing 'action' in request"}), 400

    action = data["action"].lower()
    if action == "start":
        is_bot_active = True
        print("Bot activated via API")  # Debug log
        return jsonify({"status": "Bot activated"})
    elif action == "stop":
        is_bot_active = False
        print("Bot deactivated via API")  # Debug log
        return jsonify({"status": "Bot deactivated"})
    elif action == "status":
        status = "active" if is_bot_active else "inactive"
        return jsonify({"status": status})
    else:
        return jsonify({"error": "Invalid action. Use 'start', 'stop', or 'status'"}), 400

@app.route('/generate', methods=['POST'])
def generate_text():
    data = request.json
    user_input = data.get("text", "")

    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    try:
        # Gemini API Call
        model = genai.GenerativeModel("gemini-2.0-flash")
        # Ensure the combined input does not exceed 500 characters
        max_length = 500
        truncated_prompt = suzu_prompt_2[:max_length // 2]
        truncated_input = user_input[:max_length - len(truncated_prompt)]
        response = model.generate_content([truncated_prompt, truncated_input])
        ai_response =  response.text.strip()

        return jsonify({"response": ai_response})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/twitchgenerate', methods=['POST'])
def generate_twitchtext():
    data = request.json
    user_input = data.get("text", "")

    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    try:
        # Gemini API Call
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content([suzu_prompt_2, user_input])
        ai_response = response.text.strip()

        return jsonify({"response": ai_response})
    
    except Exception as e:
        print(f"Error in twitchgenerate: {str(e)}")
        # Fallback response in case of API failure
        fallback_response = "I'm having trouble thinking right now. Please try again in a moment!"
        return jsonify({"response": fallback_response})

    # Search from Python

@app.route('/localgenerate', methods=['POST'])
def generate_localtext():
    data = request.json
    user_input = data.get("text", "")

    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    try:
        response = get_gemma_response(suzu_prompt_2 + user_input)
        return jsonify({"response": response})
    except Exception as e:
        print(f"Error in localgenerate: {str(e)}")
        # Fallback response in case of API failure
        fallback_response = "I'm having trouble thinking right now. Please try again in a moment!"
        return jsonify({"response": fallback_response})

def get_gemma_response(prompt, model_name="gemma3:4b"): # Or "gemma3:1b"
    try:
        # Ollama expects a 'messages' list for chat
        response = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        return response['message']['content']
    except ollama.ResponseError as e:
        print(f"Error communicating with Ollama: {e}")
        return "I'm having trouble thinking right now. Please try again in a moment!"
    except Exception as e:
        print(f"Error in localgenerate: {str(e)}")
        return "I'm having trouble thinking right now. Please try again in a moment!"

def search_songs(query):
    response = requests.post(
        "http://localhost:8631/search",
        json={"query": query}
    )
    return response.json()["results"]

# Play from Python
def play_selected(device_id, track_uri):
    requests.post(
        "http://localhost:8631/play",
        json={"device_id": device_id, "track_uri": track_uri}
    )

@app.route('/speak', methods=['POST'])
def speak():
    data = request.json
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        use_online_tts = True  # Set to True to use Google TTS instead of pyttsx3

        if use_online_tts:
            tts = gTTS(text=text, lang="en")
            tts.save("static/suzu_tts.mp3")
            return jsonify({"status": "success", "audio_url": "/static/suzu_tts.mp3"})
        else:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            return jsonify({"status": "success", "message": "Speaking..."})

    except Exception as e:
        import traceback
        error_message = traceback.format_exc()  # Get full error details
        print(error_message)  # Print to console
        return jsonify({"error": str(e), "details": error_message}), 500


if __name__ == '__main__':
    app.run(host= "0.0.0.0", port=8080, debug=True)
