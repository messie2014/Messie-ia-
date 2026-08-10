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

    # Récupérer le message envoyé par le site
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    # Vérifier que le message existe
    if not message:
        return jsonify({
            "error": "Message vide."
        }), 400


    # ==========================================
    # RÉCUPÉRER LA CLÉ OPENAI
    # ==========================================

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return jsonify({
            "error": "La clé OPENAI_API_KEY n'est pas configurée sur Render."
        }), 500


    # ==========================================
    # API OPENAI
    # ==========================================

    url = "https://api.openai.com/v1/responses"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


    # ==========================================
    # INSTRUCTIONS DE MESSIE IA
    # ==========================================

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


    # ==========================================
    # DONNÉES ENVOYÉES À OPENAI
    # ==========================================

    payload = {
        "model": "gpt-5",
        "instructions": instructions,
        "input": message
    }


    # ==========================================
    # ENVOYER LA DEMANDE
    # ==========================================

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )


        # ==========================================
        # GESTION DES ERREURS OPENAI
        # ==========================================

        if not response.ok:

            try:
                error_data = response.json()
            except Exception:
                error_data = {
                    "message": response.text
                }

            # IMPORTANT :
            # On renvoie maintenant le détail complet
            # de l'erreur au site.

            return jsonify({
                "error": "Erreur OpenAI",
                "status": response.status_code,
                "details": error_data
            }), response.status_code


        # ==========================================
        # RÉCUPÉRER LA RÉPONSE
        # ==========================================

        try:
            result = response.json()
        except Exception as e:

            return jsonify({
                "error": "OpenAI a envoyé une réponse invalide.",
                "details": str(e),
                "raw_response": response.text
            }), 500


        # ==========================================
        # RÉCUPÉRER LE TEXTE DE MESSIE IA
        # ==========================================

        answer = result.get("output_text")


        # Si aucun texte n'est trouvé
        if not answer:

            return jsonify({
                "error": "OpenAI n'a pas retourné de texte.",
                "details": result
            }), 500


        # ==========================================
        # ENVOYER LA RÉPONSE AU SITE
        # ==========================================

        return jsonify({
            "answer": answer
        })


    # ==========================================
    # TIMEOUT
    # ==========================================

    except requests.exceptions.Timeout:

        return jsonify({
            "error": "OpenAI met trop de temps à répondre."
        }), 504


    # ==========================================
    # ERREUR DE CONNEXION
    # ==========================================

    except requests.exceptions.RequestException as e:

        return jsonify({
            "error": "Erreur de connexion à OpenAI.",
            "details": str(e)
        }), 500


    # ==========================================
    # AUTRE ERREUR SERVEUR
    # ==========================================

    except Exception as e:

        return jsonify({
            "error": "Erreur serveur.",
            "details": str(e)
        }), 500


# ==========================================
# DÉMARRAGE DU SERVEUR
# ==========================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
