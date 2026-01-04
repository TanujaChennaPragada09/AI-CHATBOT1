from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import subprocess
import json
import os
from googletrans import Translator

app = Flask(__name__)
CORS(app)

HISTORY_FILE = "chat_history.json"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

translator = Translator()

# ===============================
# ROOT CHECK
# ===============================
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "API is running"})

# ===============================
# HISTORY FUNCTIONS
# ===============================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_history(username, role, message):
    data = load_history()
    data.setdefault(username, []).append({"role": role, "message": message})
    save_history(data)

# ===============================
# OLLAMA CHAT STREAM
# ===============================
def ollama_stream(prompt):
    """Stream AI response from Ollama"""
    process = subprocess.Popen(
        ["ollama", "run", "llama3.2:1b"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    process.stdin.write(prompt)
    process.stdin.close()
    for line in process.stdout:
        yield line

# ===============================
# CHAT STREAM API WITH TRANSLATE
# ===============================
@app.route("/chat-stream", methods=["POST"])
def chat_stream():
    data = request.json
    user_msg = data.get("message", "")
    username = data.get("username", "guest")
    file_content = data.get("file_content", "")

    add_history(username, "user", user_msg)

    text_lower = user_msg.lower()
    target_lang_code = None

    # Detect translation requests
    if "translate" in text_lower:
        if "hindi" in text_lower:
            target_lang_code = "hi"
        elif "telugu" in text_lower:
            target_lang_code = "te"
        elif "spanish" in text_lower:
            target_lang_code = "es"
        elif "french" in text_lower:
            target_lang_code = "fr"

    if target_lang_code:
        sentence = user_msg.lower().replace("translate", "").replace("in hindi", "").replace("in telugu", "").replace("in spanish", "").replace("in french", "").strip()
        if file_content:
            sentence += f"\n\nFile Content:\n{file_content}"
        try:
            translated_text = translator.translate(sentence, dest=target_lang_code).text
        except Exception as e:
            translated_text = f"Error translating: {str(e)}"

        def generate_translation():
            yield json.dumps({"text": translated_text}) + "\n"
            add_history(username, "bot", translated_text)
        return Response(generate_translation(), mimetype="application/json")

    full_prompt = user_msg
    if file_content:
        full_prompt += f"\n\nFile Content:\n{file_content}"

    def generate_chat():
        full = ""
        for chunk in ollama_stream(full_prompt):
            full += chunk
            yield json.dumps({"text": chunk}) + "\n"
        add_history(username, "bot", full.strip())

    return Response(generate_chat(), mimetype="application/json")

# ===============================
# HISTORY APIs
# ===============================
@app.route("/history", methods=["GET"])
def history():
    user = request.args.get("user")
    data = load_history()
    return jsonify(data.get(user, []))

@app.route("/clear-history", methods=["POST"])
def clear_history():
    user = request.json.get("username")
    data = load_history()
    data[user] = []
    save_history(data)
    return jsonify({"status": "cleared"})

# ===============================
# FILE UPLOAD WITH PROMPT
# ===============================
@app.route("/upload-with-prompt", methods=["POST"])
def upload_with_prompt():
    file = request.files["file"]
    prompt = request.form.get("prompt", "")
    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    file_content = ""
    if file.filename.endswith(('.txt', '.md', '.csv', '.docx')):
        try:
            if file.filename.endswith('.docx'):
                from docx import Document
                doc = Document(path)
                file_content = "\n".join([p.text for p in doc.paragraphs])[:1000]
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    file_content = f.read(1000)
        except Exception as e:
            file_content = f"Could not read file content: {str(e)}"

    full_prompt = f"{prompt}\n\nFile Content:\n{file_content}"

    ai_response = ""
    for chunk in ollama_stream(full_prompt):
        ai_response += chunk

    return jsonify({
        "status": "uploaded",
        "filename": file.filename,
        "ai_response": ai_response
    })

# ===============================
# IMAGE GENERATION
# ===============================
@app.route("/generate-image", methods=["POST"])
def generate_image():
    data = request.json
    prompt = data.get("prompt", "AI image")
    url = f"https://via.placeholder.com/512?text={prompt.replace(' ', '+')}"
    return jsonify({"image": url})

# ===============================
# TRANSLATE API
# ===============================
@app.route("/translate", methods=["POST"])
def translate_api():
    data = request.json
    text = data.get("text", "")
    target_lang = data.get("lang", "")

    if not text or not target_lang:
        return jsonify({"error": "Provide 'text' and 'lang'"}), 400

    try:
        translated = translator.translate(text, dest=target_lang)
        return jsonify({"translation": translated.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
