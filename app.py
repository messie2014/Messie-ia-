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

    api_key = os.environ.get(
        "OPENROUTER_API_KEY"
    )

    if not api_key:

        return jsonify({
            "error":
                "La clé OPENROUTER_API_KEY n'est pas configurée."
        }), 500


    # --------------------------------------------------------
    # Récupérer les données
    # --------------------------------------------------------

    data = request.get_json(
        silent=True
    ) or {}


    message = data.get(
        "message",
        ""
    )


    if not isinstance(message, str):

        message = ""


    message = message.strip()


    # --------------------------------------------------------
    # Vérifier le message
    # --------------------------------------------------------

    if not message:

        return jsonify({
            "error": "Message vide."
        }), 400


    # --------------------------------------------------------
    # Récupérer l'historique
    # --------------------------------------------------------

    history = data.get(
        "history",
        []
    )


    if not isinstance(history, list):

        history = []


    # --------------------------------------------------------
    # Limiter l'historique
    # --------------------------------------------------------

    history = history[-20:]


    # --------------------------------------------------------
    # Préparer le contexte
    # --------------------------------------------------------

    messages = [

        {
            "role": "system",

            "content": (
                "Tu es Messie IA, un assistant intelligent "
                "utile, respectueux, naturel et précis. "

                "Tu réponds principalement en français. "

                "Tu dois utiliser le contexte de la "
                "conversation lorsqu'il est disponible. "

                "Lorsque l'utilisateur pose une question "
                "qui dépend d'un message précédent, "
                "utilise les messages précédents pour "
                "comprendre sa demande. "

                "Réponds directement à la question. "

                "Évite les réponses inutiles ou répétitives. "

                "Si l'utilisateur écrit dans une autre "
                "langue, réponds dans cette langue. "

                "Ne prétends pas avoir accès à des informations "
                "que tu n'as pas."
            )
        }

    ]


    # --------------------------------------------------------
    # Ajouter l'historique
    # --------------------------------------------------------

    for item in history:

        if not isinstance(
            item,
            dict
        ):
            continue


        role = item.get(
            "role"
        )


        content = item.get(
            "content"
        )


        # Vérifier le rôle

        if role not in [
            "user",
            "assistant"
        ]:

            continue


        # Vérifier le contenu

        if not isinstance(
            content,
            str
        ):

            continue


        content = content.strip()


        if not content:

            continue


        messages.append({

            "role": role,

            "content": content

        })


    # --------------------------------------------------------
    # Éviter de doubler le dernier message utilisateur
    # --------------------------------------------------------

    if not messages or messages[-1].get(
        "role"
    ) != "user" or messages[-1].get(
        "content"
    ) != message:

        messages.append({

            "role": "user",

            "content": message

        })


    # --------------------------------------------------------
    # OpenRouter
    # --------------------------------------------------------

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )


    # --------------------------------------------------------
    # Headers
    # --------------------------------------------------------

    headers = {

        "Authorization":
            f"Bearer {api_key}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://messie-ia.onrender.com",

        "X-Title":
            "Messie IA"

    }


    # --------------------------------------------------------
    # Requête OpenRouter
    # --------------------------------------------------------

    payload = {

        "model":
            "openrouter/free",

        "messages":
            messages,

        "temperature":
            0.7,

        "max_tokens":
            1000

    }


    # --------------------------------------------------------
    # Envoyer la requête
    # --------------------------------------------------------

    try:

        response = requests.post(

            url,

            headers=headers,

            json=payload,

            timeout=60

        )


        # ----------------------------------------------------
        # Lire le JSON
        # ----------------------------------------------------

        try:

            result = response.json()

        except ValueError:

            print(
                "Réponse OpenRouter invalide :",
                response.text
            )

            return jsonify({

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        # ----------------------------------------------------
        # Gestion des erreurs OpenRouter
        # ----------------------------------------------------

        if response.status_code != 200:

            print(
                "Erreur OpenRouter :",
                result
            )


            error_data = result.get(
                "error",
                {}
            )


            if isinstance(
                error_data,
                dict
            ):

                error_message = error_data.get(

                    "message",

                    "Une erreur est survenue avec OpenRouter."

                )

            else:

                error_message = (
                    "Une erreur est survenue "
                    "avec OpenRouter."
                )


            return jsonify({

                "error":
                    error_message

            }), response.status_code


        # ----------------------------------------------------
        # Récupérer les choix
        # ----------------------------------------------------

        choices = result.get(
            "choices",
            []
        )


        if not choices:

            print(
                "OpenRouter n'a renvoyé aucun choix :",
                result
            )

            return jsonify({

                "error":
                    "OpenRouter n'a renvoyé aucune réponse."

            }), 500


        # ----------------------------------------------------
        # Récupérer le message IA
        # ----------------------------------------------------

        ai_message = choices[0].get(

            "message",

            {}

        )


        answer = ai_message.get(

            "content",

            ""

        )


        # ----------------------------------------------------
        # Vérifier la réponse
        # ----------------------------------------------------

        if not answer:

            return jsonify({

                "error":
                    "La réponse de Messie IA est vide."

            }), 500


        # ----------------------------------------------------
        # Réponse au navigateur
        # ----------------------------------------------------

        return jsonify({

            "response":
                answer

        })


    # --------------------------------------------------------
    # Timeout
    # --------------------------------------------------------

    except requests.exceptions.Timeout:

        return jsonify({

            "error":
                "OpenRouter met trop de temps à répondre."

        }), 504


    # --------------------------------------------------------
    # Erreur réseau
    # --------------------------------------------------------

    except requests.exceptions.RequestException as e:

        print(
            "Erreur réseau :",
            str(e)
        )


        return jsonify({

            "error":
                "Impossible de contacter OpenRouter."

        }), 500


    # --------------------------------------------------------
    # Autre erreur
    # --------------------------------------------------------

    except Exception as e:

        print(
            "Erreur serveur :",
            str(e)
        )


        return jsonify({

            "error":
                "Une erreur inattendue est survenue."

        }), 500


# ============================================================
# TEST DU SERVEUR
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
            "ok",

        "service":
            "Messie IA"

    })


# ============================================================
# DÉMARRAGE
# ============================================================

if __name__ == "__main__":

    port = int(

        os.environ.get(

            "PORT",

            10000

        )

    )


    app.run(

        host="0.0.0.0",

        port=port

    )
