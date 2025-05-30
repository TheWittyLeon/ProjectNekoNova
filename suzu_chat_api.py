import os
import pyttsx3  # Offline TTS
from gtts import gTTS  # Online TTS
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai  # Gemini API
import requests
import threading

suzu_prompt = """
"You are a helpful and friendly AI assistant designed for a Twitch chat environment. Your name is Suzu. 
You are polite, informative, and always ready to assist users with their questions or requests. 
You respond in a clear and concise manner, providing accurate information and helpful suggestions. 
You maintain a positive and engaging tone, but avoid sounding to much like a robot with responses. 
You are able to handle a variety of requests, including answering questions, providing definitions, giving recommendations, and offering general assistance. 
You are programmed to be helpful and efficient, ensuring a smooth and enjoyable experience for all chat participants.
I want you to have a bit ((((SASSY)))) though still be curtious and keep your messages from being to long."
"""


# Load API Keys from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_2")

# Flask App Setup
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# Create a global variable to store the bot instance
bot_instance = None

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

@app.route('/bot/control-panel')
def bot_control_panel():
    return render_template('bot_control.html')

@app.route('/bot/control', methods=['POST'])
def control_bot():
    global bot_instance
    
    if not bot_instance:
        return jsonify({"error": "Bot is not initialized"}), 400
        
    data = request.json
    action = data.get("action", "")
    
    if action == "start":
        bot_instance.is_active = True
        return jsonify({"status": "Bot activated"})
    elif action == "stop":
        bot_instance.is_active = False
        return jsonify({"status": "Bot deactivated"})
    elif action == "status":
        status = "active" if bot_instance.is_active else "inactive"
        return jsonify({"status": status})
    else:
        return jsonify({"error": "Invalid action. Use 'start', 'stop', or 'status'"}), 400

@app.route('/bot/status', methods=['GET'])
def get_bot_status():
    global bot_instance
    
    if not bot_instance:
        return jsonify({"status": "not_initialized"})
        
    status = "active" if bot_instance.is_active else "inactive"
    return jsonify({"status": status})

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

@app.route('/generate', methods=['POST'])
def generate_text():
    data = request.json
    user_input = data.get("text", "")

    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    try:
        # Gemini API Call
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content([suzi_prompt, user_input])
        ai_response =  response.text.strip()

        return jsonify({"response": ai_response})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    # Search from Python
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
