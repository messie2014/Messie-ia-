import os
import base64
import requests

from flask import Flask, render_template, request, jsonify


# ============================================================
# APPLICATION
# ============================================================

app = Flask(__name__)

# Limite globale des requêtes.
# 25 Mo permet l'envoi d'images raisonnables.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# ============================================================
# CONFIGURATION
# ============================================================

OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    ""
).strip()

OPENROUTER_URL = "https://openrouter.ai/api/v1"


# ============================================================
# MODÈLES
# ============================================================

CHAT_MODEL = os.environ.get(
    "OPENROUTER_CHAT_MODEL",
    "openai/gpt-4o-mini"
).strip()


VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL",
    "google/gemini-2.5-flash"
).strip()


IMAGE_MODEL = os.environ.get(
    "OPENROUTER_IMAGE_MODEL",
    "google/gemini-2.5-flash-image"
).strip()


# ============================================================
# LIMITES
# ============================================================

MAX_HISTORY_MESSAGES = 30

MAX_MESSAGE_LENGTH = 12000

MAX_PROMPT_LENGTH = 12000

MAX_REFERENCE_IMAGE_LENGTH = 20 * 1024 * 1024


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
Tu es Messie IA, un assistant intelligent, utile,
clair, respectueux et chaleureux.

Tu réponds en français par défaut.

Si l'utilisateur demande une autre langue,
réponds dans cette langue.

Donne des réponses précises et faciles à comprendre.

Pour les questions techniques, explique les étapes
clairement.

Lorsque tu n'es pas certain d'une information,
indique-le plutôt que d'inventer.

Ne révèle jamais les clés API, secrets, variables
d'environnement privées ou informations internes
du serveur.
""".strip()


# ============================================================
# OUTILS
# ============================================================

def check_api_key():

    return bool(
        OPENROUTER_API_KEY
    )


def openrouter_headers():

    headers = {

        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "X-Title":
            "Messie IA"

    }

    try:

        referer = request.host_url.rstrip("/")

        if referer:

            headers["HTTP-Referer"] = referer

    except Exception:

        pass

    return headers


# ============================================================
# ERREURS OPENROUTER
# ============================================================

def get_openrouter_error(data):

    if not isinstance(
        data,
        dict
    ):

        return "Erreur OpenRouter."


    error = data.get(
        "error"
    )


    if isinstance(
        error,
        dict
    ):

        message = error.get(
            "message"
        )


        if isinstance(
            message,
            str
        ):

            message = message.strip()


            if message:

                return message


        code = error.get(
            "code"
        )


        if code:

            return (
                f"Erreur OpenRouter "
                f"(code {code})."
            )


    if isinstance(
        error,
        str
    ):

        error = error.strip()


        if error:

            return error


    return "Erreur OpenRouter."


# ============================================================
# EXTRACTION TEXTE
# ============================================================

def extract_chat_response(data):

    if not isinstance(
        data,
        dict
    ):

        return ""


    choices = data.get(
        "choices",
        []
    )


    if not isinstance(
        choices,
        list
    ) or not choices:

        return ""


    first = choices[0]


    if not isinstance(
        first,
        dict
    ):

        return ""


    message = first.get(
        "message",
        {}
    )


    if not isinstance(
        message,
        dict
    ):

        return ""


    content = message.get(
        "content",
        ""
    )


    if isinstance(
        content,
        str
    ):

        return content.strip()


    if isinstance(
        content,
        list
    ):

        parts = []


        for item in content:

            if not isinstance(
                item,
                dict
            ):

                continue


            text = item.get(
                "text"
            )


            if isinstance(
                text,
                str
            ):

                parts.append(
                    text
                )


        return "\n".join(
            parts
        ).strip()


    return ""


# ============================================================
# HISTORIQUE
# ============================================================

def clean_history(history):

    cleaned = []


    if not isinstance(
        history,
        list
    ):

        return cleaned


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


        content = content.strip()


        if not content:

            continue


        if len(content) > MAX_MESSAGE_LENGTH:

            content = content[
                :MAX_MESSAGE_LENGTH
            ]


        cleaned.append({

            "role":
                role,

            "content":
                content

        })


    return cleaned[
        -MAX_HISTORY_MESSAGES:
    ]


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route("/")
def index():

    try:

        return render_template(
            "index.html"
        )

    except Exception as error:

        print(
            "INDEX ERROR:",
            repr(error)
        )


        return jsonify({

            "error":
                "Impossible de charger index.html.",

            "details":
                str(error)

        }), 500


# ============================================================
# CHAT
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
                    "OPENROUTER_API_KEY n'est pas configurée."

            }), 500


        data = request.get_json(
            silent=True
        )


        if not isinstance(
            data,
            dict
        ):

            return jsonify({

                "error":
                    "Données JSON invalides."

            }), 400


        message = data.get(
            "message",
            ""
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


        if len(message) > MAX_MESSAGE_LENGTH:

            return jsonify({

                "error":
                    "Le message est trop long."

            }), 400


        history = clean_history(
            data.get(
                "history",
                []
            )
        )


        messages = [

            {

                "role":
                    "system",

                "content":
                    SYSTEM_PROMPT

            }

        ]


        messages.extend(
            history
        )


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

        except ValueError:

            print(
                "CHAT INVALID RESPONSE:",
                response.text[:1000]
            )


            return jsonify({

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        if not response.ok:

            message_error =
                get_openrouter_error(
                    result
                )


            print(
                "CHAT OPENROUTER ERROR:",
                response.status_code,
                message_error
            )


            return jsonify({

                "error":
                    message_error

            }), response.status_code


        answer =
            extract_chat_response(
                result
            )


        if not answer:

            return jsonify({

                "error":
                    "OpenRouter n'a renvoyé aucune réponse."

            }), 502


        return jsonify({

            "response":
                answer,

            "model":
                CHAT_MODEL

        })


    except requests.Timeout:

        return jsonify({

            "error":
                "Le délai de réponse est dépassé. Réessaie."

        }), 504


    except requests.RequestException as error:

        print(
            "CHAT REQUEST ERROR:",
            repr(error)
        )


        return jsonify({

            "error":
                "Impossible de contacter OpenRouter."

        }), 502


    except Exception as error:

        print(
            "CHAT INTERNAL ERROR:",
            repr(error)
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


        if not isinstance(
            data,
            dict
        ):

            return jsonify({

                "error":
                    "Données JSON invalides."

            }), 400


        image_data = data.get(
            "image",
            ""
        )


        if not isinstance(
            image_data,
            str
        ):

            return jsonify({

                "error":
                    "Image invalide."

            }), 400


        image_data =
            image_data.strip()


        if not image_data.startswith(
            "data:image/"
        ):

            return jsonify({

                "error":
                    "Format d'image non supporté."

            }), 400


        if len(image_data) > MAX_REFERENCE_IMAGE_LENGTH:

            return jsonify({

                "error":
                    "L'image est trop volumineuse."

            }), 400


        prompt = data.get(
            "prompt",
            "Décris cette image en détail."
        )


        if not isinstance(
            prompt,
            str
        ):

            prompt =
                "Décris cette image en détail."


        prompt =
            prompt.strip()


        if not prompt:

            prompt =
                "Décris cette image en détail."


        prompt =
            prompt[
                :MAX_PROMPT_LENGTH
            ]


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

        except ValueError:

            return jsonify({

                "error":
                    "Réponse OpenRouter invalide."

            }), 502


        if not response.ok:

            return jsonify({

                "error":
                    get_openrouter_error(
                        result
                    )

            }), response.status_code


        answer =
            extract_chat_response(
                result
            )


        if not answer:

            return jsonify({

                "error":
                    "Le modèle de vision n'a renvoyé aucune réponse."

            }), 502


        return jsonify({

            "response":
                answer,

            "model":
                VISION_MODEL

        })


    except requests.Timeout:

        return jsonify({

            "error":
                "L'analyse de l'image prend trop de temps."

        }), 504


    except requests.RequestException as error:

        print(
            "VISION REQUEST ERROR:",
            repr(error)
        )


        return jsonify({

            "error":
                "Impossible de contacter OpenRouter."

        }), 502


    except Exception as error:

        print(
            "VISION INTERNAL ERROR:",
            repr(error)
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


        if not isinstance(
            data,
            dict
        ):

            return jsonify({

                "error":
                    "Données JSON invalides."

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


        prompt =
            prompt.strip()


        if not prompt:

            return jsonify({

                "error":
                    "Décris l'image que tu veux créer."

            }), 400


        if len(prompt) > MAX_PROMPT_LENGTH:

            prompt =
                prompt[
                    :MAX_PROMPT_LENGTH
                ]


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


        try:

            n = int(
                data.get(
                    "n",
                    1
                )
            )

        except Exception:

            n = 1


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        allowed_ratios = {

            "1:1",
            "16:9",
            "9:16",
            "4:3",
            "3:4",
            "3:2",
            "2:3",
            "2:1",
            "1:2",
            "21:9",
            "9:21",
            "auto"

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


        # Maximum 4 pour éviter les abus.
        n = max(
            1,
            min(
                n,
                4
            )
        )


        # ----------------------------------------------------
        # PAYLOAD IMAGE
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

        reference_image = data.get(
            "reference_image"
        )


        if isinstance(
            reference_image,
            str
        ):

            reference_image =
                reference_image.strip()


            if reference_image:

                if not reference_image.startswith(
                    "data:image/"
                ):

                    return jsonify({

                        "error":
                            "L'image de référence est invalide."

                    }), 400


                if len(reference_image) > MAX_REFERENCE_IMAGE_LENGTH:

                    return jsonify({

                        "error":
                            "L'image de référence est trop volumineuse."

                    }), 400


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


        # ----------------------------------------------------
        # RÉPONSE
        # ----------------------------------------------------

        try:

            result =
                response.json()

        except ValueError:

            print(
                "IMAGE INVALID RESPONSE:",
                response.text[:1000]
            )


            return jsonify({

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        # ----------------------------------------------------
        # ERREUR
        # ----------------------------------------------------

        if not response.ok:

            message_error =
                get_openrouter_error(
                    result
                )


            print(
                "IMAGE OPENROUTER ERROR:",
                response.status_code,
                message_error
            )


            return jsonify({

                "error":
                    message_error

            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION IMAGES
        # ----------------------------------------------------

        images = []


        image_data_list =
            result.get(
                "data",
                []
            )


        if not isinstance(
            image_data_list,
            list
        ):

            image_data_list = []


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

                media_type =
                    "image/png"


            # Petite vérification du base64.
            try:

                base64.b64decode(
                    b64,
                    validate=True
                )

            except Exception:

                continue


            images.append({

                "data":
                    f"data:{media_type};base64,{b64}",

                "media_type":
                    media_type

            })


        if not images:

            print(
                "IMAGE EMPTY RESULT:",
                result
            )


            return jsonify({

                "error":
                    "OpenRouter n'a renvoyé aucune image."

            }), 502


        # ----------------------------------------------------
        # USAGE / COÛT
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
            "IMAGE REQUEST ERROR:",
            repr(error)
        )


        return jsonify({

            "error":
                "Impossible de contacter le service d'images OpenRouter."

        }), 502


    except Exception as error:

        print(
            "IMAGE INTERNAL ERROR:",
            repr(error)
        )


        return jsonify({

            "error":
                "Erreur interne pendant la génération de l'image."

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/health",
    methods=["GET"]
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

        "chat_model":
            CHAT_MODEL,

        "vision_model":
            VISION_MODEL,

        "image_model":
            IMAGE_MODEL

    })


# ============================================================
# ERREUR 404
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({

        "error":
            "Endpoint introuvable.",

        "path":
            request.path

    }), 404


# ============================================================
# ERREUR 413
# ============================================================

@app.errorhandler(413)
def request_too_large(error):

    return jsonify({

        "error":
            "La requête est trop volumineuse."

    }), 413


# ============================================================
# ERREUR 500
# ============================================================

@app.errorhandler(500)
def internal_server_error(error):

    print(
        "FLASK 500:",
        repr(error)
    )


    return jsonify({

        "error":
            "Erreur interne du serveur Messie IA."

    }), 500


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )


    app.run(

        host=
            "0.0.0.0",

        port=
            port,

        debug=
            False

    )



