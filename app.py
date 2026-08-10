import os
import requests

from flask import Flask, request, jsonify, send_from_directory


app = Flask(__name__, static_folder="static")


# =========================
# PAGE PRINCIPALE
# =========================

@app.route("/")
def home():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "index.html"
    )


# =========================
# API CHAT
# =========================

@app.route("/api/chat", methods=["POST"])
def chat():

    # Récupérer le message envoyé par le site
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    # Vérifier que le message existe
    if not message:
        return jsonify({
            "error": "Message vide."
        }), 400


    # Récupérer la clé OpenAI depuis Render
    api_key = os.environ.get("OPENAI_API_KEY")

    # Vérifier que la clé existe
    if not api_key:
        return jsonify({
            "error": "La clé OpenAI n'est pas configurée."
        }), 500


    # Adresse de l'API OpenAI
    url = "https://api.openai.com/v1/responses"


    # En-têtes de la requête
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


    # Instructions de Messie IA
    instructions = """
Tu es Messie IA, un assistant intelligent.

Tu réponds toujours de manière :
- utile
- claire
- polie
- naturelle
- concise lorsque la question est simple

Tu réponds en français par défaut.

Si l'utilisateur te parle dans une autre langue,
tu peux lui répondre dans cette langue.

Ne prétends pas être humain.
Tu es Messie IA.
"""


    # Données envoyées à OpenAI
    payload = {
        "model": "gpt-5",
        "instructions": instructions,
        "input": message
    }


    try:

        # Envoyer la demande à OpenAI
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )


        # Vérifier les erreurs HTTP
        response.raise_for_status()


        # Convertir la réponse en JSON
        result = response.json()


        # Récupérer le texte de la réponse
        answer = result.get("output_text")


        # Vérification supplémentaire
        if not answer:
            return jsonify({
                "error": "OpenAI n'a pas retourné de réponse."
            }), 500


        # Envoyer la réponse à ton site
        return jsonify({
            "answer": answer
        })


    except requests.exceptions.HTTPError:

        # Afficher l'erreur renvoyée par OpenAI
        try:
            error_data = response.json()
        except Exception:
            error_data = {
                "error": response.text
            }

        return jsonify({
            "error": "Erreur OpenAI.",
            "details": error_data
        }), response.status_code


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


# =========================
# DÉMARRAGE DU SERVEUR
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
