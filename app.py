import os
import requests

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")


# ==========================================
# PAGE PRINCIPALE
# ==========================================

@app.route("/")
def home():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "index.html"
    )


# ==========================================
# API CHAT
# ==========================================

@app.route("/api/chat", methods=["POST"])
def chat():

    # Récupérer le message
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "error": "Message vide."
        }), 400


    # Récupérer la clé OpenAI depuis Render
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return jsonify({
            "error": "La clé OPENAI_API_KEY n'est pas configurée sur Render."
        }), 500


    # Adresse de l'API OpenAI
    url = "https://api.openai.com/v1/responses"


    # En-têtes
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


    # Personnalité de Messie IA
    instructions = """
Tu es Messie IA, un assistant intelligent.

Tu réponds toujours de manière :
- utile
- claire
- polie
- naturelle
- concise lorsque la question est simple

Tu réponds en français par défaut.

Si l'utilisateur parle dans une autre langue,
tu peux lui répondre dans cette langue.

Tu dois être honnête.
Si tu ne connais pas une information, dis-le clairement.
"""


    # Requête envoyée à OpenAI
    payload = {
        "model": "gpt-5",
        "instructions": instructions,
        "input": message
    }


    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )


        # Si OpenAI renvoie une erreur,
        # afficher le détail exact
        if not response.ok:

            try:
                error_data = response.json()
            except Exception:
                error_data = {
                    "message": response.text
                }

            return jsonify({
                "error": "Erreur OpenAI",
                "details": error_data
            }), response.status_code


        # Convertir la réponse en JSON
        result = response.json()


        # Récupérer le texte
        answer = result.get("output_text")


        if not answer:

            return jsonify({
                "error": "OpenAI n'a pas retourné de texte.",
                "details": result
            }), 500


        # Envoyer la réponse au site
        return jsonify({
            "answer": answer
        })


    except requests.exceptions.Timeout:

        return jsonify({
            "error": "OpenAI met trop de temps à répondre."
        }), 504


    except requests.exceptions.RequestException as e:

        return jsonify({
            "error": f"Erreur de connexion à OpenAI : {str(e)}"
        }), 500


    except Exception as e:

        return jsonify({
            "error": f"Erreur serveur : {str(e)}"
        }), 500


# ==========================================
# DÉMARRAGE DU SERVEUR
# ==========================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
