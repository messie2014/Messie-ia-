import os
import base64
import requests

from flask import Flask, render_template, request, jsonify


app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1"


# ------------------------------------------------------------
# MODÈLES
# ------------------------------------------------------------

# Modèle utilisé pour les conversations normales.
CHAT_MODEL = os.environ.get(
    "OPENROUTER_CHAT_MODEL",
    "openai/gpt-4o-mini"
)


# Modèle utilisé pour analyser les images.
VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL",
    "google/gemini-2.5-flash"
)


# Modèle utilisé pour générer / modifier les images.
#
# Tu peux le changer depuis les variables d'environnement
# Render sans modifier le code.
#
# Exemple :
# google/gemini-2.5-flash-image
#
IMAGE_MODEL = os.environ.get(
    "OPENROUTER_IMAGE_MODEL",
    "google/gemini-2.5-flash-image"
)


# ============================================================
# VÉRIFICATION API KEY
# ============================================================

def check_api_key():

    if not OPENROUTER_API_KEY:

        return False

    return True


# ============================================================
# HEADERS OPENROUTER
# ============================================================

def openrouter_headers():

    return {

        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            request.host_url.rstrip("/"),

        "X-Title":
            "Messie IA"

    }


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route("/")
def index():

    return render_template("index.html")


# ============================================================
# CHAT TEXTE
# ============================================================

@app.route(
    "/api/chat",
    methods=["POST"]
)
def chat():

    try:

        if not check_api_key():

            return jsonify({

                "error":
                    "OPENROUTER_API_KEY n'est pas configurée sur le serveur."

            }), 500


        data = request.get_json(
            silent=True
        )


        if not data:

            return jsonify({

                "error":
                    "Données invalides."

            }), 400


        message = data.get(
            "message",
            ""
        )


        history = data.get(
            "history",
            []
        )


        if not isinstance(
            message,
            str
        ):

            return jsonify({

                "error":
                    "Le message doit être du texte."

            }), 400


        message = message.strip()


        if not message:

            return jsonify({

                "error":
                    "Le message est vide."

            }), 400


        # ----------------------------------------------------
        # HISTORIQUE
        # ----------------------------------------------------

        messages = [

            {

                "role":
                    "system",

                "content":
                    (
                        "Tu es Messie IA, "
                        "un assistant intelligent, "
                        "utile, clair et respectueux. "
                        "Réponds en français sauf si "
                        "l'utilisateur demande une autre langue. "
                        "N'affiche jamais d'informations techniques "
                        "internes de sécurité ou de modération."
                    )

            }

        ]


        if isinstance(
            history,
            list
        ):

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


                if role not in (
                    "user",
                    "assistant"
                ):

                    continue


                if not isinstance(
                    content,
                    str
                ):

                    continue


                if not content.strip():

                    continue


                messages.append({

                    "role":
                        role,

                    "content":
                        content

                })


        # ----------------------------------------------------
        # MESSAGE ACTUEL
        # ----------------------------------------------------

        messages.append({

            "role":
                "user",

            "content":
                message

        })


        payload = {

            "model":
                CHAT_MODEL,

            "messages":
                messages,

            "temperature":
                0.7

        }


        response = requests.post(

            f"{OPENROUTER_URL}/chat/completions",

            headers=
                openrouter_headers(),

            json=
                payload,

            timeout=
                120

        )


        try:

            result =
                response.json()

        except Exception:

            return jsonify({

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        if not response.ok:

            error_message = (

                result
                    .get("error", {})
                    .get(
                        "message",
                        "Erreur OpenRouter."
                    )

                if isinstance(
                    result.get("error"),
                    dict
                )

                else

                "Erreur OpenRouter."

            )


            return jsonify({

                "error":
                    error_message

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

            first =
                choices[0]


            if isinstance(
                first,
                dict
            ):

                message_data =
                    first.get(
                        "message",
                        {}
                    )


                if isinstance(
                    message_data,
                    dict
                ):

                    content =
                        message_data.get(
                            "content",
                            ""
                        )


                    if isinstance(
                        content,
                        str
                    ):

                        answer =
                            content


        if not answer:

            answer =
                "Je n'ai pas pu générer une réponse."


        return jsonify({

            "response":
                answer

        })


    except requests.Timeout:

        return jsonify({

            "error":
                "Le délai de réponse d'OpenRouter a été dépassé."

        }), 504


    except requests.RequestException as error:

        print(
            "OpenRouter request error:",
            error
        )


        return jsonify({

            "error":
                "Impossible de contacter OpenRouter."

        }), 502


    except Exception as error:

        print(
            "Chat error:",
            error
        )


        return jsonify({

            "error":
                "Une erreur interne est survenue."

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

        if not check_api_key():

            return jsonify({

                "error":
                    "OPENROUTER_API_KEY n'est pas configurée."

            }), 500


        data = request.get_json(
            silent=True
        )


        if not data:

            return jsonify({

                "error":
                    "Données invalides."

            }), 400


        image_data =
            data.get(
                "image",
                ""
            )


        prompt =
            data.get(
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


        payload = {

            "model":
                VISION_MODEL,

            "messages": [

                {

                    "role":
                        "user",

                    "content": [

                        {

                            "type":
                                "text",

                            "text":
                                prompt

                        },

                        {

                            "type":
                                "image_url",

                            "image_url": {

                                "url":
                                    image_data

                            }

                        }

                    ]

                }

            ]

        }


        response = requests.post(

            f"{OPENROUTER_URL}/chat/completions",

            headers=
                openrouter_headers(),

            json=
                payload,

            timeout=
                120

        )


        try:

            result =
                response.json()

        except Exception:

            return jsonify({

                "error":
                    "Réponse invalide d'OpenRouter."

            }), 502


        if not response.ok:

            return jsonify({

                "error":
                    get_openrouter_error(
                        result
                    )

            }), response.status_code


        answer = ""


        choices =
            result.get(
                "choices",
                []
            )


        if choices:

            answer =
                choices[0] \
                    .get(
                        "message",
                        {}
                    ) \
                    .get(
                        "content",
                        ""
                    )


        return jsonify({

            "response":
                answer

        })


    except requests.RequestException:

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

    try:

        if not check_api_key():

            return jsonify({

                "error":
                    "OPENROUTER_API_KEY n'est pas configurée."

            }), 500


        data = request.get_json(
            silent=True
        )


        if not data:

            return jsonify({

                "error":
                    "Données invalides."

            }), 400


        prompt =
            data.get(
                "prompt",
                ""
            )


        prompt =
            prompt.strip()


        if not prompt:

            return jsonify({

                "error":
                    "Décris l'image que tu veux créer ou modifier."

            }), 400


        # ----------------------------------------------------
        # OPTIONS
        # ----------------------------------------------------

        aspect_ratio =
            data.get(
                "aspect_ratio",
                "1:1"
            )


        resolution =
            data.get(
                "resolution",
                "1K"
            )


        quality =
            data.get(
                "quality",
                "auto"
            )


        output_format =
            data.get(
                "output_format",
                "png"
            )


        n =
            data.get(
                "n",
                1
            )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        allowed_ratios = {

            "1:1",
            "16:9",
            "9:16",
            "4:3",
            "3:4"

        }


        if aspect_ratio not in allowed_ratios:

            aspect_ratio =
                "1:1"


        allowed_resolutions = {

            "512",
            "1K",
            "2K",
            "4K"

        }


        if resolution not in allowed_resolutions:

            resolution =
                "1K"


        allowed_quality = {

            "auto",
            "low",
            "medium",
            "high"

        }


        if quality not in allowed_quality:

            quality =
                "auto"


        allowed_formats = {

            "png",
            "jpeg",
            "webp"

        }


        if output_format not in allowed_formats:

            output_format =
                "png"


        try:

            n =
                int(n)

        except Exception:

            n =
                1


        n =
            max(
                1,
                min(
                    n,
                    4
                )
            )


        # ----------------------------------------------------
        # PAYLOAD
        # ----------------------------------------------------

        payload = {

            "model":
                IMAGE_MODEL,

            "prompt":
                prompt,

            "n":
                n,

            "resolution":
                resolution,

            "aspect_ratio":
                aspect_ratio,

            "quality":
                quality,

            "output_format":
                output_format

        }


        # ----------------------------------------------------
        # IMAGE DE RÉFÉRENCE
        # ----------------------------------------------------

        reference_image =
            data.get(
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

            payload[
                "input_references"
            ] = [

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
        # APPEL OPENROUTER
        # ----------------------------------------------------

        response = requests.post(

            f"{OPENROUTER_URL}/images",

            headers=
                openrouter_headers(),

            json=
                payload,

            timeout=
                300

        )


        try:

            result =
                response.json()

        except Exception:

            return jsonify({

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        if not response.ok:

            return jsonify({

                "error":
                    get_openrouter_error(
                        result
                    )

            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION DES IMAGES
        # ----------------------------------------------------

        images = []


        for image in result.get(
            "data",
            []
        ):

            if not isinstance(
                image,
                dict
            ):

                continue


            b64 =
                image.get(
                    "b64_json"
                )


            if not b64:

                continue


            media_type =
                image.get(
                    "media_type",
                    "image/png"
                )


            images.append({

                "data":
                    f"data:{media_type};base64,{b64}",

                "media_type":
                    media_type

            })


        if not images:

            return jsonify({

                "error":
                    "OpenRouter n'a renvoyé aucune image."

            }), 502


        # ----------------------------------------------------
        # COÛT
        # ----------------------------------------------------

        usage =
            result.get(
                "usage",
                {}
            )


        cost = None


        if isinstance(
            usage,
            dict
        ):

            cost =
                usage.get(
                    "cost"
                )


        return jsonify({

            "images":
                images,

            "usage": {

                "cost":
                    cost

            },

            "model":
                IMAGE_MODEL

        })


    except requests.Timeout:

        return jsonify({

            "error":
                "La génération de l'image prend trop de temps. Réessaie."

        }), 504


    except requests.RequestException as error:

        print(
            "Image request error:",
            error
        )


        return jsonify({

            "error":
                "Impossible de contacter le service d'images OpenRouter."

        }), 502


    except Exception as error:

        print(
            "Generate image error:",
            error
        )


        return jsonify({

            "error":
                "Erreur interne pendant la génération."

        }), 500


# ============================================================
# ERREUR OPENROUTER
# ============================================================

def get_openrouter_error(data):

    if not isinstance(
        data,
        dict
    ):

        return "Erreur OpenRouter."


    error =
        data.get(
            "error"
        )


    if isinstance(
        error,
        dict
    ):

        message =
            error.get(
                "message"
            )


        if isinstance(
            message,
            str
        ):

            return message


    if isinstance(
        error,
        str
    ):

        return error


    return "Erreur OpenRouter."


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
            )

    })


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    port =
        int(
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
