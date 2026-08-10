import os
import requests

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")


# =========================================================
# PAGE PRINCIPALE
# =========================================================

@app.route("/")
def home():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "index.html"
    )


# =========================================================
# API CHAT - OPENROUTER
# =========================================================

@app.route("/api/chat", methods=["POST"])
def chat():

    # Récupérer la clé OpenRouter depuis Render
    api_key = os.environ.get("OPENROUTER_API_KEY")

    # Vérifier que la clé existe
    if not api_key:
        return jsonify({
            "error": "La clé OPENROUTER_API_KEY n'est pas configurée sur Render."
        }), 500

    # Récupérer le message envoyé par le site
    data = request.get_json() or {}

    message = data.get("message", "").strip()

    # Vérifier que le message existe
    if not message:
        return jsonify({
            "error": "Message vide."
        }), 400

    # =====================================================
    # REQUÊTE OPENROUTER
    # =====================================================

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",

        # Informations facultatives pour OpenRouter
        "HTTP-Referer": "https://messie-ia.onrender.com",
        "X-Title": "Messie IA"
    }

    payload = {
        "model": "openrouter/free",

        "messages": [
            {
                "role": "system",
                "content": (
                    "Tu es Messie IA, un assistant intelligent, "
                    "utile, respectueux et facile à comprendre. "
                    "Tu réponds principalement en français."
                )
            },
            {
                "role": "user",
                "content": message
            }
        ],

        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        # Transformer la réponse OpenRouter en JSON
        result = response.json()

        # =================================================
        # SI OPENROUTER RENVOIE UNE ERREUR
        # =================================================

        if response.status_code != 200:

            print("Erreur OpenRouter :", result)

            error_message = (
                result.get("error", {})
                .get("message", "Erreur OpenRouter inconnue.")
            )

            return jsonify({
                "error": error_message
            }), response.status_code

        # =================================================
        # RÉCUPÉRER LA RÉPONSE DE L'IA
        # =================================================

        choices = result.get("choices", [])

        if not choices:
            return jsonify({
                "error": "OpenRouter n'a renvoyé aucune réponse."
            }), 500

        ai_message = choices[0].get("message", {})

        answer = ai_message.get("content", "")

        if not answer:
            return jsonify({
                "error": "La réponse de l'IA est vide."
            }), 500

        # =================================================
        # RENVOYER LA RÉPONSE AU SITE
        # =================================================

        return jsonify({
            "response": answer
        })

    except requests.exceptions.Timeout:

        return jsonify({
            "error": "OpenRouter met trop de temps à répondre. Réessaie."
        }), 504

    except requests.exceptions.RequestException as e:

        print("Erreur réseau :", str(e))

        return jsonify({
            "error": "Impossible de contacter OpenRouter."
        }), 500

    except Exception as e:

        print("Erreur serveur :", str(e))

        return jsonify({
            "error": "Une erreur inattendue est survenue."
        }), 500


# =========================================================
# TEST DE L'API
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "Messie IA"
    })


# =========================================================
# DÉMARRAGE DU SERVEUR
# =========================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
