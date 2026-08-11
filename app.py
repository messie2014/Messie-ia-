import os
import time
import requests

from flask import Flask, render_template, request, jsonify


# ============================================================
# APPLICATION
# ============================================================

app = Flask(__name__)

# Taille maximale des requêtes.
# 25 MB permet notamment d'envoyer des images assez grandes.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# ============================================================
# CONFIGURATION OPENROUTER
# ============================================================

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

OPENROUTER_URL = "https://openrouter.ai/api/v1"


# ============================================================
# MODÈLES
# ============================================================

# Modèle pour le chat normal.
CHAT_MODEL = os.environ.get(
    "OPENROUTER_CHAT_MODEL",
    "openai/gpt-4o-mini"
)


# Modèle pour analyser les images.
VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL",
    "google/gemini-3.1-flash-lite"
)


# Modèle de génération/modification d'images.
#
# Nano Banana 2 Lite est choisi par défaut pour privilégier
# la vitesse.
#
# Tu peux toujours changer ce modèle dans Render avec :
#
# OPENROUTER_IMAGE_MODEL
#
IMAGE_MODEL = os.environ.get(
    "OPENROUTER_IMAGE_MODEL",
    "google/gemini-3.1-flash-lite-image"
)


# ============================================================
# SESSION HTTP
# ============================================================

# Réutiliser une connexion HTTP permet d'éviter de recréer
# une connexion à chaque requête.
http = requests.Session()


# ============================================================
# OUTILS
# ============================================================

def check_api_key():
    """
    Vérifie que la clé OpenRouter existe.
    """
    return bool(OPENROUTER_API_KEY)


def openrouter_headers():
    """
    Headers utilisés pour OpenRouter.
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Title": "Messie IA",
    }

    # HTTP-Referer est facultatif.
    # On l'ajoute seulement lorsqu'il est disponible.
    try:
        host_url = request.host_url.rstrip("/")

        if host_url:
            headers["HTTP-Referer"] = host_url

    except Exception:
        pass

    return headers


def get_openrouter_error(data):
    """
    Transforme les erreurs OpenRouter en message lisible.
    """

    if not isinstance(data, dict):
        return "Erreur OpenRouter."


    error = data.get("error")


    if isinstance(error, dict):

        message = error.get("message")

        if isinstance(message, str) and message.strip():
            return message.strip()


        code = error.get("code")

        if code:
            return f"Erreur OpenRouter ({code})."


    if isinstance(error, str) and error.strip():
        return error.strip()


    message = data.get("message")

    if isinstance(message, str) and message.strip():
        return message.strip()


    return "Erreur OpenRouter."


def parse_json_response(response):
    """
    Essaie de récupérer le JSON renvoyé par OpenRouter.
    """

    try:
        return response.json()

    except ValueError:

        return None


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route("/")
def index():

    return render_template("index.html")


# ============================================================
# CHAT TEXTE
# ============================================================

@app.route("/api/chat", methods=["POST"])
def chat():

    try:

        # ----------------------------------------------------
        # API KEY
        # ----------------------------------------------------

        if not check_api_key():

            return jsonify({
                "error": (
                    "OPENROUTER_API_KEY n'est pas configurée "
                    "sur le serveur Render."
                )
            }), 500


        # ----------------------------------------------------
        # DONNÉES
        # ----------------------------------------------------

        data = request.get_json(silent=True)


        if not isinstance(data, dict):

            return jsonify({
                "error": "Données invalides."
            }), 400


        message = data.get("message", "")


        history = data.get(
            "history",
            []
        )


        if not isinstance(message, str):

            return jsonify({
                "error": "Le message doit être du texte."
            }), 400


        message = message.strip()


        if not message:

            return jsonify({
                "error": "Le message est vide."
            }), 400


        # ----------------------------------------------------
        # MESSAGES
        # ----------------------------------------------------

        messages = [

            {
                "role": "system",

                "content": (
                    "Tu es Messie IA, un assistant intelligent, "
                    "utile, clair et respectueux. "
                    "Réponds en français sauf si l'utilisateur "
                    "demande une autre langue. "
                    "Donne des réponses utiles et compréhensibles."
                )
            }

        ]


        # ----------------------------------------------------
        # HISTORIQUE
        # ----------------------------------------------------

        if isinstance(history, list):

            # On limite l'historique pour éviter d'envoyer
            # énormément de données à OpenRouter.
            history = history[-30:]


            for item in history:

                if not isinstance(item, dict):
                    continue


                role = item.get("role")
                content = item.get("content")


                if role not in (
                    "user",
                    "assistant"
                ):
                    continue


                if not isinstance(content, str):
                    continue


                content = content.strip()


                if not content:
                    continue


                messages.append({
                    "role": role,
                    "content": content
                })


        # ----------------------------------------------------
        # MESSAGE ACTUEL
        # ----------------------------------------------------

        messages.append({

            "role": "user",

            "content": message

        })


        # ----------------------------------------------------
        # PAYLOAD
        # ----------------------------------------------------

        payload = {

            "model": CHAT_MODEL,

            "messages": messages,

            "temperature": 0.7

        }


        # ----------------------------------------------------
        # APPEL
        # ----------------------------------------------------

        response = http.post(

            f"{OPENROUTER_URL}/chat/completions",

            headers=openrouter_headers(),

            json=payload,

            timeout=(15, 120)

        )


        result = parse_json_response(response)


        if result is None:

            return jsonify({
                "error": (
                    "OpenRouter a renvoyé une réponse "
                    "qui n'est pas du JSON."
                )
            }), 502


        # ----------------------------------------------------
        # ERREUR
        # ----------------------------------------------------

        if not response.ok:

            return jsonify({

                "error": get_openrouter_error(result)

            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION
        # ----------------------------------------------------

        answer = ""


        choices = result.get(
            "choices",
            []
        )


        if choices and isinstance(
            choices[0],
            dict
        ):

            message_data = choices[0].get(
                "message",
                {}
            )


            if isinstance(
                message_data,
                dict
            ):

                content = message_data.get(
                    "content",
                    ""
                )


                if isinstance(
                    content,
                    str
                ):

                    answer = content.strip()


        if not answer:

            answer = (
                "Je n'ai pas pu générer une réponse."
            )


        return jsonify({

            "response": answer,

            "model": CHAT_MODEL

        })


    except requests.Timeout:

        return jsonify({

            "error": (
                "OpenRouter met trop de temps à répondre."
            )

        }), 504


    except requests.RequestException as error:

        print(
            "Chat OpenRouter error:",
            error
        )


        return jsonify({

            "error": (
                "Impossible de contacter OpenRouter."
            )

        }), 502


    except Exception as error:

        print(
            "Chat error:",
            error
        )


        return jsonify({

            "error": (
                "Une erreur interne est survenue."
            )

        }), 500


# ============================================================
# ANALYSE D'IMAGE
# ============================================================

@app.route(
    "/api/analyze-image",
    methods=["POST"]
)
def analyze_image():

    try:

        # ----------------------------------------------------
        # API KEY
        # ----------------------------------------------------

        if not check_api_key():

            return jsonify({

                "error": (
                    "OPENROUTER_API_KEY n'est pas configurée."
                )

            }), 500


        # ----------------------------------------------------
        # DONNÉES
        # ----------------------------------------------------

        data = request.get_json(
            silent=True
        )


        if not isinstance(
            data,
            dict
        ):

            return jsonify({

                "error":
                    "Données invalides."

            }), 400


        image_data = data.get(
            "image",
            ""
        )


        prompt = data.get(

            "prompt",

            "Décris cette image en détail."

        )


        if not isinstance(
            image_data,
            str
        ):

            return jsonify({

                "error":
                    "Image invalide."

            }), 400


        if not image_data.startswith(
            "data:image/"
        ):

            return jsonify({

                "error":
                    "Format d'image non supporté."

            }), 400


        if not isinstance(
            prompt,
            str
        ):

            prompt = (
                "Décris cette image en détail."
            )


        prompt = prompt.strip()


        if not prompt:

            prompt = (
                "Décris cette image en détail."
            )


        # ----------------------------------------------------
        # PAYLOAD
        # ----------------------------------------------------

        payload = {

            "model": VISION_MODEL,

            "messages": [

                {

                    "role": "user",

                    "content": [

                        {

                            "type": "text",

                            "text": prompt

                        },

                        {

                            "type": "image_url",

                            "image_url": {

                                "url": image_data

                            }

                        }

                    ]

                }

            ]

        }


        # ----------------------------------------------------
        # APPEL
        # ----------------------------------------------------

        response = http.post(

            f"{OPENROUTER_URL}/chat/completions",

            headers=openrouter_headers(),

            json=payload,

            timeout=(15, 120)

        )


        result = parse_json_response(response)


        if result is None:

            return jsonify({

                "error":
                    "Réponse invalide d'OpenRouter."

            }), 502


        # ----------------------------------------------------
        # ERREUR
        # ----------------------------------------------------

        if not response.ok:

            return jsonify({

                "error":
                    get_openrouter_error(result)

            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION
        # ----------------------------------------------------

        answer = ""


        choices = result.get(
            "choices",
            []
        )


        if choices:

            first = choices[0]


            if isinstance(
                first,
                dict
            ):

                message_data = first.get(
                    "message",
                    {}
                )


                if isinstance(
                    message_data,
                    dict
                ):

                    content = message_data.get(
                        "content",
                        ""
                    )


                    if isinstance(
                        content,
                        str
                    ):

                        answer = content.strip()


        if not answer:

            answer = (
                "Je n'ai pas pu analyser cette image."
            )


        return jsonify({

            "response": answer,

            "model": VISION_MODEL

        })


    except requests.Timeout:

        return jsonify({

            "error":
                "L'analyse de l'image prend trop de temps."

        }), 504


    except requests.RequestException as error:

        print(
            "Vision OpenRouter error:",
            error
        )


        return jsonify({

            "error":
                "Impossible de contacter OpenRouter."

        }), 502


    except Exception as error:

        print(
            "Image analysis error:",
            error
        )


        return jsonify({

            "error":
                "Erreur pendant l'analyse de l'image."

        }), 500


# ============================================================
# GÉNÉRATION / MODIFICATION D'IMAGE
# ============================================================

@app.route(
    "/api/generate-image",
    methods=["POST"]
)
def generate_image():

    start_time = time.time()


    try:

        # ----------------------------------------------------
        # API KEY
        # ----------------------------------------------------

        if not check_api_key():

            return jsonify({

                "error": (
                    "OPENROUTER_API_KEY n'est pas configurée "
                    "sur Render."
                )

            }), 500


        # ----------------------------------------------------
        # DONNÉES
        # ----------------------------------------------------

        data = request.get_json(
            silent=True
        )


        if not isinstance(
            data,
            dict
        ):

            return jsonify({

                "error":
                    "Données invalides."

            }), 400


        # ----------------------------------------------------
        # PROMPT
        # ----------------------------------------------------

        prompt = data.get(
            "prompt",
            ""
        )


        if not isinstance(
            prompt,
            str
        ):

            return jsonify({

                "error":
                    "Le prompt doit être du texte."

            }), 400


        prompt = prompt.strip()


        if not prompt:

            return jsonify({

                "error":
                    (
                        "Décris l'image que tu veux "
                        "créer ou modifier."
                    )

            }), 400


        # ----------------------------------------------------
        # OPTIONS
        # ----------------------------------------------------

        aspect_ratio = data.get(
            "aspect_ratio",
            "1:1"
        )


        resolution = data.get(
            "resolution",
            "1K"
        )


        quality = data.get(
            "quality",
            "auto"
        )


        output_format = data.get(
            "output_format",
            "png"
        )


        n = data.get(
            "n",
            1
        )


        # ----------------------------------------------------
        # VALIDATION RAPIDE
        # ----------------------------------------------------

        allowed_ratios = {

            "1:1",
            "16:9",
            "9:16",
            "4:3",
            "3:4"

        }


        if aspect_ratio not in allowed_ratios:

            aspect_ratio = "1:1"


        # Le modèle rapide est optimisé pour 1K.
        allowed_resolutions = {

            "1K"

        }


        if resolution not in allowed_resolutions:

            resolution = "1K"


        allowed_quality = {

            "auto",
            "low",
            "medium",
            "high"

        }


        if quality not in allowed_quality:

            quality = "auto"


        allowed_formats = {

            "png",
            "jpeg",
            "webp"

        }


        if output_format not in allowed_formats:

            output_format = "png"


        try:

            n = int(n)

        except (TypeError, ValueError):

            n = 1


        # Une image par défaut = beaucoup plus rapide.
        n = max(
            1,
            min(
                n,
                1
            )
        )


        # ----------------------------------------------------
        # PAYLOAD MINIMAL
        # ----------------------------------------------------
        #
        # On n'envoie pas inutilement des paramètres qui
        # peuvent ne pas être supportés par tous les modèles.
        #
        # OpenRouter indique que les paramètres d'image
        # disponibles dépendent du modèle.
        # ----------------------------------------------------

        payload = {

            "model": IMAGE_MODEL,

            "prompt": prompt,

            "n": n,

            "aspect_ratio": aspect_ratio,

            "resolution": resolution

        }


        # ----------------------------------------------------
        # QUALITÉ
        # ----------------------------------------------------

        # Certains modèles ne supportent pas quality.
        #
        # On ne l'envoie que si elle a été explicitement
        # demandée autrement que "auto".
        if quality != "auto":

            payload["quality"] = quality


        # ----------------------------------------------------
        # IMAGE DE RÉFÉRENCE
        # ----------------------------------------------------

        reference_image = data.get(
            "reference_image"
        )


        if (
            isinstance(
                reference_image,
                str
            )
            and
            reference_image.startswith(
                "data:image/"
            )
        ):

            payload["input_references"] = [

                {

                    "type":
                        "image_url",

                    "image_url": {

                        "url":
                            reference_image

                    }

                }

            ]


        # ----------------------------------------------------
        # GÉNÉRATION
        # ----------------------------------------------------

        print(
            f"[IMAGE] Début génération | "
            f"model={IMAGE_MODEL} | "
            f"ratio={aspect_ratio} | "
            f"resolution={resolution}"
        )


        response = http.post(

            f"{OPENROUTER_URL}/images",

            headers=openrouter_headers(),

            json=payload,

            timeout=(20, 180)

        )


        elapsed = round(
            time.time() - start_time,
            2
        )


        print(
            f"[IMAGE] Réponse OpenRouter "
            f"en {elapsed}s | "
            f"status={response.status_code}"
        )


        # ----------------------------------------------------
        # JSON
        # ----------------------------------------------------

        result = parse_json_response(
            response
        )


        if result is None:

            return jsonify({

                "error": (
                    "OpenRouter a renvoyé une "
                    "réponse invalide."
                ),

                "generating": False,

                "elapsed": elapsed

            }), 502


        # ----------------------------------------------------
        # ERREUR
        # ----------------------------------------------------

        if not response.ok:

            return jsonify({

                "error":
                    get_openrouter_error(
                        result
                    ),

                "generating":
                    False,

                "elapsed":
                    elapsed

            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION DES IMAGES
        # ----------------------------------------------------

        images = []


        image_data_list = result.get(
            "data",
            []
        )


        if isinstance(
            image_data_list,
            list
        ):

            for image in image_data_list:

                if not isinstance(
                    image,
                    dict
                ):
                    continue


                b64 = image.get(
                    "b64_json"
                )


                if not isinstance(
                    b64,
                    str
                ):
                    continue


                if not b64:
                    continue


                media_type = image.get(
                    "media_type",
                    "image/png"
                )


                if not isinstance(
                    media_type,
                    str
                ):

                    media_type = "image/png"


                # Nettoyage du type MIME.
                if not media_type.startswith(
                    "image/"
                ):

                    media_type = "image/png"


                images.append({

                    "data":
                        (
                            f"data:{media_type};"
                            f"base64,{b64}"
                        ),

                    "media_type":
                        media_type

                })


        # ----------------------------------------------------
        # AUCUNE IMAGE
        # ----------------------------------------------------

        if not images:

            return jsonify({

                "error": (
                    "OpenRouter n'a renvoyé "
                    "aucune image."
                ),

                "generating": False,

                "elapsed": elapsed,

                "model": IMAGE_MODEL

            }), 502


        # ----------------------------------------------------
        # USAGE / COÛT
        # ----------------------------------------------------

        usage = result.get(
            "usage",
            {}
        )


        cost = None


        if isinstance(
            usage,
            dict
        ):

            cost = usage.get(
                "cost"
            )


        # ----------------------------------------------------
        # RÉPONSE FINALE
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "generating": False,

            "images": images,

            "usage": {

                "cost":
                    cost

            },

            "model":
                IMAGE_MODEL,

            "elapsed":
                elapsed

        })


    except requests.Timeout:

        elapsed = round(
            time.time() - start_time,
            2
        )


        print(
            f"[IMAGE] Timeout après {elapsed}s"
        )


        return jsonify({

            "error": (
                "La génération prend trop de temps. "
                "Réessaie avec une image 1K."
            ),

            "generating": False,

            "elapsed":
                elapsed

        }), 504


    except requests.RequestException as error:

        elapsed = round(
            time.time() - start_time,
            2
        )


        print(
            "[IMAGE] Request error:",
            error
        )


        return jsonify({

            "error": (
                "Impossible de contacter "
                "le service d'images OpenRouter."
            ),

            "generating": False,

            "elapsed":
                elapsed

        }), 502


    except Exception as error:

        elapsed = round(
            time.time() - start_time,
            2
        )


        print(
            "[IMAGE] Internal error:",
            error
        )


        return jsonify({

            "error": (
                "Erreur interne pendant "
                "la génération."
            ),

            "generating": False,

            "elapsed":
                elapsed

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/health"
)
def health():

    return jsonify({

        "status":
            "ok",

        "app":
            "Messie IA",

        "openrouter":
            bool(
                OPENROUTER_API_KEY
            ),

        "image_model":
            IMAGE_MODEL,

        "vision_model":
            VISION_MODEL,

        "chat_model":
            CHAT_MODEL

    })


# ============================================================
# PAGE 404
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({

        "error":
            "Page ou route introuvable."

    }), 404


# ============================================================
# ERREUR 413
# ============================================================

@app.errorhandler(413)
def request_too_large(error):

    return jsonify({

        "error":
            "Le fichier envoyé est trop volumineux."

    }), 413


# ============================================================
# LANCEMENT LOCAL
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

        )
