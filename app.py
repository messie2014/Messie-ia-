import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")


@app.route("/")
def home():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "index.html"
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message vide"}), 400

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return jsonify({
            "error": "La clé Gemini n'est pas configurée."
        }), 500

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent"
        f"?key={api_key}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Tu es Messie IA, un assistant intelligent, "
                            "utile, poli et clair. Réponds en français "
                            "sauf si l'utilisateur demande une autre langue.\n\n"
                            f"Utilisateur : {message}"
                        )
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        answer = (
            result["candidates"][0]
            ["content"]["parts"][0]["text"]
        )

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
            )
