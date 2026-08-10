import os
import requests

from flask import Flask, request, jsonify, send_from_directory


# ============================================================
# CONFIGURATION
# ============================================================

app = Flask(__name__, static_folder="static")


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route("/")
def home():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "index.html"
    )


# ============================================================
# API CHAT - OPENROUTER
# ============================================================

@app.route("/api/chat", methods=["POST"])
def chat():

    # --------------------------------------------------------
    # Récupérer la clé OpenRouter
    # --------------------------------------------------------

    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        return jsonify({
            "error": "La clé OPENROUTER_API_KEY n'est pas configurée."
        }), 500

    # --------------------------------------------------------
    # Récupérer le message envoyé par le site
    # --------------------------------------------------------

    data = request.get_json(silent=True) or {}

    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "error": "Message vide."
        }), 400

    # --------------------------------------------------------
    # URL OpenRouter
    # --------------------------------------------------------

    url = "https://openrouter.ai/api/v1/chat/completions"

    # --------------------------------------------------------
    # En-têtes
    # --------------------------------------------------------

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",

        # Informations facultatives
        "HTTP-Referer": "https://messie-ia.com",
        "X-Title": "Messie IA"
    }

    # --------------------------------------------------------
    # Requête envoyée à l'IA
    # --------------------------------------------------------

    payload = {
        "model": "openrouter/free",

        "messages": [
            {
                "role": "system",
                "content": (
                    "Tu es Messie IA, un assistant intelligent, "
                    "utile, respectueux et précis. "
                    "Tu réponds principalement en français. "
                    "Réponds de manière claire et naturelle. "
                    "Si l'utilisateur écrit dans une autre langue, "
                    "tu peux répondre dans cette langue."
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

    # --------------------------------------------------------
    # Contacter OpenRouter
    # --------------------------------------------------------

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        # ----------------------------------------------------
        # Transformer la réponse OpenRouter en JSON
        # ----------------------------------------------------

        try:
            result = response.json()

        except ValueError:
            return jsonify({
                "error": "OpenRouter a renvoyé une réponse invalide."
            }), 502

        # ----------------------------------------------------
        # Si OpenRouter renvoie une erreur
        # ----------------------------------------------------

        if response.status_code != 200:

            print("Erreur OpenRouter :", result)

            error_message = (
                result
                .get("error", {})
                .get(
                    "message",
                    "Une erreur est survenue avec OpenRouter."
                )
            )

            return jsonify({
                "error": error_message
            }), response.status_code

        # ----------------------------------------------------
        # Récupérer la réponse de l'IA
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Renvoyer la réponse au site
        # ----------------------------------------------------

        return jsonify({
            "response": answer
        })

    # --------------------------------------------------------
    # Gestion du délai d'attente
    # --------------------------------------------------------

    except requests.exceptions.Timeout:

        return jsonify({
            "error": "OpenRouter met trop de temps à répondre."
        }), 504

    # --------------------------------------------------------
    # Gestion des erreurs réseau
    # --------------------------------------------------------

    except requests.exceptions.RequestException as e:

        print("Erreur réseau :", str(e))

        return jsonify({
            "error": "Impossible de contacter OpenRouter."
        }), 500

    # --------------------------------------------------------
    # Gestion des autres erreurs
    # --------------------------------------------------------

    except Exception as e:

        print("Erreur serveur :", str(e))

        return jsonify({
            "error": "Une erreur inattendue est survenue."
        }), 500


# ============================================================
# TEST DE L'API
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "Messie IA"
    })


# ============================================================
# DÉMARRAGE DU SERVEUR
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
