import os
import traceback
import requests

from flask import Flask, render_template, request, jsonify


# ============================================================
# MESSIE IA
# Backend Flask + OpenRouter
# ============================================================

app = Flask(
    __name__,
    template_folder="templates"
)

# Limite raisonnable pour éviter les requêtes énormes.
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024


# ============================================================
# CONFIGURATION
# ============================================================

OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY"
)

OPENROUTER_URL = "https://openrouter.ai/api/v1"


# ============================================================
# MODÈLES
# ============================================================

# Chat gratuit.
CHAT_MODEL = os.environ.get(
    "OPENROUTER_CHAT_MODEL",
    "openrouter/free"
)


# Analyse d'image.
#
# Tu peux remplacer cette valeur dans Render si nécessaire.
VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL",
    "openrouter/free"
)


# Génération d'image.
#
# La génération d'image peut nécessiter un modèle compatible
# et éventuellement des crédits selon le modèle disponible.
IMAGE_MODEL = os.environ.get(
    "OPENROUTER_IMAGE_MODEL",
    "google/gemini-2.5-flash-image"
)


# ============================================================
# CONFIGURATION CHAT
# ============================================================

SYSTEM_PROMPT = """
Tu es Messie IA, un assistant intelligent, utile, clair,
respectueux et chaleureux.

Tu réponds en français par défaut.

Si l'utilisateur demande une autre langue, utilise cette langue.

Donne des réponses faciles à comprendre.

Pour les questions complexes, explique progressivement.

Ne prétends jamais avoir effectué une action que tu n'as
pas réellement effectuée.

Si tu n'es pas certain d'une information, indique-le clairement.

Tu es l'assistant officiel de l'application Messie IA.
""".strip()


# ============================================================
# HEADERS OPENROUTER
# ============================================================

def openrouter_headers():

    headers = {
        "Authorization": "Bearer " + str(
            OPENROUTER_API_KEY
        ),

        "Content-Type": "application/json",

        "X-Title": "Messie IA"
    }

    # HTTP-Referer est optionnel.
    # On l'ajoute seulement si Render fournit l'URL.
    render_url = os.environ.get(
        "RENDER_EXTERNAL_URL"
    )

    if render_url:

        headers["HTTP-Referer"] = render_url

    return headers


# ============================================================
# ERREUR OPENROUTER
# ============================================================

def get_openrouter_error(data):

    if not isinstance(data, dict):

        return "Erreur OpenRouter."


    error = data.get("error")


    if isinstance(error, dict):

        message = error.get("message")


        if (
            isinstance(message, str)
            and message.strip()
        ):

            return message.strip()


    if (
        isinstance(error, str)
        and error.strip()
    ):

        return error.strip()


    return "Erreur OpenRouter."


# ============================================================
# VÉRIFICATION CLÉ
# ============================================================

def check_api_key():

    return bool(
        OPENROUTER_API_KEY
        and
        OPENROUTER_API_KEY.strip()
    )


# ============================================================
# EXTRAIRE RÉPONSE CHAT
# ============================================================

def extract_chat_answer(result):

    if not isinstance(
        result,
        dict
    ):

        return ""


    choices = result.get(
        "choices",
        []
    )


    if not isinstance(
        choices,
        list
    ):

        return ""


    if not choices:

        return ""


    first = choices[0]


    if not isinstance(
        first,
        dict
    ):

        return ""


    message_data = first.get(
        "message",
        {}
    )


    if not isinstance(
        message_data,
        dict
    ):

        return ""


    content = message_data.get(
        "content",
        ""
    )


    # Certains modèles peuvent renvoyer une chaîne.
    if isinstance(
        content,
        str
    ):

        return content.strip()


    # Gestion de certaines réponses structurées.
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


        return "\n".join(parts).strip()


    return ""


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def index():

    try:

        return render_template(
            "index.html"
        )

    except Exception as error:

        print(
            "========== ERREUR INDEX =========="
        )

        traceback.print_exc()

        print(
            "=================================="
        )

        return jsonify({

            "success": False,

            "error":
                "Impossible de charger index.html.",

            "details":
                str(error)

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
            check_api_key(),

        "chat_model":
            CHAT_MODEL,

        "vision_model":
            VISION_MODEL,

        "image_model":
            IMAGE_MODEL

    })


# ============================================================
# DIAGNOSTIC DES FICHIERS
# ============================================================

@app.route(
    "/debug-files",
    methods=["GET"]
)
def debug_files():

    try:

        base_directory = os.path.dirname(
            os.path.abspath(__file__)
        )


        templates_directory = os.path.join(
            base_directory,
            "templates"
        )


        index_file = os.path.join(
            templates_directory,
            "index.html"
        )


        templates_files = []


        if os.path.isdir(
            templates_directory
        ):

            templates_files = os.listdir(
                templates_directory
            )


        return jsonify({

            "success":
                True,

            "app":
                "Messie IA",

            "base_directory":
                base_directory,

            "files":
                os.listdir(
                    base_directory
                ),

            "templates_exists":
                os.path.isdir(
                    templates_directory
                ),

            "templates_files":
                templates_files,

            "index_exists":
                os.path.isfile(
                    index_file
                )

        })


    except Exception as error:

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
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

        # ----------------------------------------------------
        # CLÉ API
        # ----------------------------------------------------

        if not check_api_key():

            return jsonify({

                "success":
                    False,

                "error":
                    (
                        "OPENROUTER_API_KEY "
                        "n'est pas configurée dans Render."
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

                "success":
                    False,

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


        # ----------------------------------------------------
        # VALIDATION MESSAGE
        # ----------------------------------------------------

        if not isinstance(
            message,
            str
        ):

            return jsonify({

                "success":
                    False,

                "error":
                    "Le message doit être du texte."

            }), 400


        message = message.strip()


        if not message:

            return jsonify({

                "success":
                    False,

                "error":
                    "Le message est vide."

            }), 400


        # Protection contre les messages énormes.
        if len(message) > 20000:

            return jsonify({

                "success":
                    False,

                "error":
                    "Le message est trop long."

            }), 400


        # ----------------------------------------------------
        # MESSAGES
        # ----------------------------------------------------

        messages = [

            {

                "role":
                    "system",

                "content":
                    SYSTEM_PROMPT

            }

        ]


        # ----------------------------------------------------
        # HISTORIQUE
        # ----------------------------------------------------

        if isinstance(
            history,
            list
        ):

            # On garde seulement les 20 derniers messages.
            history = history[-20:]


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


                # Protection contre un historique énorme.
                if len(content) > 20000:

                    content = content[:20000]


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


        # ----------------------------------------------------
        # PAYLOAD
        # ----------------------------------------------------

        payload = {

            "model":
                CHAT_MODEL,

            "messages":
                messages,

            "temperature":
                0.7

        }


        print(
            "Messie IA CHAT - modèle:",
            CHAT_MODEL
        )


        # ----------------------------------------------------
        # APPEL OPENROUTER
        # ----------------------------------------------------

        response = requests.post(

            OPENROUTER_URL +
            "/chat/completions",

            headers=
                openrouter_headers(),

            json=
                payload,

            timeout=
                120

        )


        # ----------------------------------------------------
        # RÉPONSE JSON
        # ----------------------------------------------------

        try:

            result = response.json()

        except Exception:

            print(
                "Réponse OpenRouter non JSON."
            )


            return jsonify({

                "success":
                    False,

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        # ----------------------------------------------------
        # ERREUR OPENROUTER
        # ----------------------------------------------------

        if not response.ok:

            error_message = (
                get_openrouter_error(
                    result
                )
            )


            print(
                "OpenRouter CHAT error:",
                error_message
            )


            return jsonify({

                "success":
                    False,

                "error":
                    error_message

            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION
        # ----------------------------------------------------

        answer = extract_chat_answer(
            result
        )


        if not answer:

            answer = (
                "Je n'ai pas pu générer une réponse."
            )


        used_model = result.get(
            "model",
            CHAT_MODEL
        )


        return jsonify({

            "success":
                True,

            "response":
                answer,

            "model":
                used_model

        })


    except requests.Timeout:

        return jsonify({

            "success":
                False,

            "error":
                (
                    "Le délai de réponse "
                    "d'OpenRouter est dépassé."
                )

        }), 504


    except requests.RequestException as error:

        print(
            "OpenRouter CHAT request error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
                "Impossible de contacter OpenRouter."

        }), 502


    except Exception as error:

        print(
            "CHAT error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success":
                False,

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

                "success":
                    False,

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

                "success":
                    False,

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


        # ----------------------------------------------------
        # VALIDATION IMAGE
        # ----------------------------------------------------

        if not isinstance(
            image_data,
            str
        ):

            return jsonify({

                "success":
                    False,

                "error":
                    "Image invalide."

            }), 400


        if not image_data.startswith(
            "data:image/"
        ):

            return jsonify({

                "success":
                    False,

                "error":
                    "Format d'image non supporté."

            }), 400


        # Protection supplémentaire.
        if len(image_data) > 10 * 1024 * 1024:

            return jsonify({

                "success":
                    False,

                "error":
                    "L'image est trop volumineuse."

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


        print(
            "Messie IA VISION - modèle:",
            VISION_MODEL
        )


        response = requests.post(

            OPENROUTER_URL +
            "/chat/completions",

            headers=
                openrouter_headers(),

            json=
                payload,

            timeout=
                120

        )


        try:

            result = response.json()

        except Exception:

            return jsonify({

                "success":
                    False,

                "error":
                    "Réponse OpenRouter invalide."

            }), 502


        if not response.ok:

            error_message = (
                get_openrouter_error(
                    result
                )
            )


            print(
                "OpenRouter VISION error:",
                error_message
            )


            return jsonify({

                "success":
                    False,

                "error":
                    error_message

            }), response.status_code


        answer = extract_chat_answer(
            result
        )


        if not answer:

            answer = (
                "Je n'ai pas pu analyser cette image."
            )


        return jsonify({

            "success":
                True,

            "response":
                answer,

            "model":
                result.get(
                    "model",
                    VISION_MODEL
                )

        })


    except requests.Timeout:

        return jsonify({

            "success":
                False,

            "error":
                "Le délai d'analyse de l'image est dépassé."

        }), 504


    except requests.RequestException as error:

        print(
            "VISION request error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
                "Impossible de contacter OpenRouter."

        }), 502


    except Exception as error:

        print(
            "VISION error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
                "Erreur pendant l'analyse de l'image."

        }), 500


# ============================================================
# GÉNÉRATION D'IMAGE
# ============================================================

@app.route(
    "/api/generate-image",
    methods=["POST"]
)
def generate_image():

    try:

        if not check_api_key():

            return jsonify({

                "success":
                    False,

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

                "success":
                    False,

                "error":
                    "Données invalides."

            }), 400


        prompt = data.get(
            "prompt",
            ""
        )


        if not isinstance(
            prompt,
            str
        ):

            return jsonify({

                "success":
                    False,

                "error":
                    "Le prompt doit être du texte."

            }), 400


        prompt = prompt.strip()


        if not prompt:

            return jsonify({

                "success":
                    False,

                "error":
                    "Décris l'image que tu veux créer."

            }), 400


        if len(prompt) > 10000:

            return jsonify({

                "success":
                    False,

                "error":
                    "La description de l'image est trop longue."

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

            aspect_ratio = "1:1"


        allowed_resolutions = {

            "512",
            "1K",
            "2K",
            "4K"

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


        # ----------------------------------------------------
        # PAYLOAD
        # ----------------------------------------------------

        payload = {

            "model":
                IMAGE_MODEL,

            "prompt":
                prompt,

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

            if len(reference_image) <= (
                10 * 1024 * 1024
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


        print(
            "Messie IA IMAGE - modèle:",
            IMAGE_MODEL
        )


        # ----------------------------------------------------
        # REQUÊTE
        # ----------------------------------------------------

        response = requests.post(

            OPENROUTER_URL +
            "/images",

            headers=
                openrouter_headers(),

            json=
                payload,

            timeout=
                300

        )


        try:

            result = response.json()

        except Exception:

            return jsonify({

                "success":
                    False,

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        if not response.ok:

            error_message = (
                get_openrouter_error(
                    result
                )
            )


            print(
                "OpenRouter IMAGE error:",
                error_message
            )


            return jsonify({

                "success":
                    False,

                "error":
                    error_message

            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION IMAGES
        # ----------------------------------------------------

        images = []


        image_list = result.get(
            "data",
            []
        )


        if isinstance(
            image_list,
            list
        ):

            for image in image_list:

                if not isinstance(
                    image,
                    dict
                ):

                    continue


                b64 = image.get(
                    "b64_json"
                )


                if (
                    not isinstance(
                        b64,
                        str
                    )
                    or
                    not b64
                ):

                    continue


                media_type = image.get(
                    "media_type",
                    "image/png"
                )


                images.append({

                    "data":
                        (
                            "data:"
                            + media_type
                            + ";base64,"
                            + b64
                        ),

                    "media_type":
                        media_type

                })


        # ----------------------------------------------------
        # AUCUNE IMAGE
        # ----------------------------------------------------

        if not images:

            return jsonify({

                "success":
                    False,

                "error":
                    "OpenRouter n'a renvoyé aucune image."

            }), 502


        # ----------------------------------------------------
        # UTILISATION
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


        return jsonify({

            "success":
                True,

            "images":
                images,

            "usage": {

                "cost":
                    cost

            },

            "model":
                result.get(
                    "model",
                    IMAGE_MODEL
                )

        })


    except requests.Timeout:

        return jsonify({

            "success":
                False,

            "error":
                (
                    "La génération de l'image "
                    "prend trop de temps. Réessaie."
                )

        }), 504


    except requests.RequestException as error:

        print(
            "IMAGE request error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
                "Impossible de contacter le service d'images."

        }), 502


    except Exception as error:

        print(
            "IMAGE error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
                "Erreur interne pendant la génération."

        }), 500


# ============================================================
# ERREURS HTTP
# ============================================================

@app.errorhandler(
    413
)
def request_too_large(error):

    return jsonify({

        "success":
            False,

        "error":
            "La requête est trop volumineuse."

    }), 413


@app.errorhandler(
    404
)
def not_found(error):

    return jsonify({

        "success":
            False,

        "error":
            "La route demandée n'existe pas."

    }), 404


@app.errorhandler(
    500
)
def internal_error(error):

    print(
        "========== ERREUR 500 =========="
    )

    traceback.print_exc()

    print(
        "================================"
    )


    return jsonify({

        "success":
            False,

        "error":
            "Erreur interne du serveur."

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

        host="0.0.0.0",

        port=port,

        debug=False

    )



