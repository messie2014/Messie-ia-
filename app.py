import os
import traceback
import requests

from flask import Flask, render_template, request, jsonify


# ============================================================
# APPLICATION
# ============================================================

app = Flask(
    __name__,
    template_folder="templates"
)


# ============================================================
# CONFIGURATION
# ============================================================

OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY"
)

OPENROUTER_URL = "https://openrouter.ai/api/v1"


CHAT_MODEL = os.environ.get(
    "OPENROUTER_CHAT_MODEL",
    "openai/gpt-4o-mini"
)


VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL",
    "google/gemini-2.5-flash"
)


IMAGE_MODEL = os.environ.get(
    "OPENROUTER_IMAGE_MODEL",
    "google/gemini-2.5-flash-image"
)


# ============================================================
# HEADERS OPENROUTER
# ============================================================

def openrouter_headers():

    return {
        "Authorization": "Bearer " + str(OPENROUTER_API_KEY),
        "Content-Type": "application/json",
        "X-Title": "Messie IA"
    }


# ============================================================
# ERREUR OPENROUTER
# ============================================================

def get_openrouter_error(data):

    if not isinstance(data, dict):
        return "Erreur OpenRouter."


    error = data.get("error")


    if isinstance(error, dict):

        message = error.get("message")


        if isinstance(message, str) and message.strip():

            return message


    if isinstance(error, str) and error.strip():

        return error


    return "Erreur OpenRouter."


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route("/", methods=["GET"])
def index():

    try:

        return render_template("index.html")

    except Exception as error:

        print("========== ERREUR INDEX ==========")
        traceback.print_exc()
        print("==================================")

        return jsonify({
            "success": False,
            "error": "Impossible de charger index.html.",
            "details": str(error)
        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "ok",
        "app": "Messie IA",
        "openrouter": bool(OPENROUTER_API_KEY)
    })


# ============================================================
# DIAGNOSTIC FICHIERS
# ============================================================

@app.route("/debug-files", methods=["GET"])
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


        return jsonify({

            "app": "Messie IA",

            "base_directory":
                base_directory,

            "files":
                os.listdir(base_directory),

            "templates_exists":
                os.path.isdir(
                    templates_directory
                ),

            "templates_files":
                (
                    os.listdir(
                        templates_directory
                    )
                    if os.path.isdir(
                        templates_directory
                    )
                    else []
                ),

            "index_exists":
                os.path.isfile(
                    index_file
                )

        })


    except Exception as error:

        traceback.print_exc()


        return jsonify({

            "success": False,

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

        if not OPENROUTER_API_KEY:

            return jsonify({

                "success": False,

                "error":
                    "OPENROUTER_API_KEY n'est pas configurée dans Render."

            }), 500


        data = request.get_json(
            silent=True
        )


        if not isinstance(
            data,
            dict
        ):

            return jsonify({

                "success": False,

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

                "success": False,

                "error":
                    "Le message doit être du texte."

            }), 400


        message = message.strip()


        if not message:

            return jsonify({

                "success": False,

                "error":
                    "Le message est vide."

            }), 400


        messages = [

            {
                "role": "system",

                "content":
                    (
                        "Tu es Messie IA, "
                        "un assistant intelligent, "
                        "utile, clair et respectueux. "
                        "Réponds en français sauf si "
                        "l'utilisateur demande une autre langue."
                    )
            }

        ]


        # ----------------------------------------------------
        # HISTORIQUE
        # ----------------------------------------------------

        if isinstance(
            history,
            list
        ):

            # Limite l'historique pour éviter
            # des requêtes excessivement grandes.

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

            "role": "user",

            "content": message

        })


        # ----------------------------------------------------
        # REQUÊTE
        # ----------------------------------------------------

        payload = {

            "model": CHAT_MODEL,

            "messages": messages,

            "temperature": 0.7

        }


        response = requests.post(

            OPENROUTER_URL + "/chat/completions",

            headers=openrouter_headers(),

            json=payload,

            timeout=120

        )


        # ----------------------------------------------------
        # JSON
        # ----------------------------------------------------

        try:

            result = response.json()

        except Exception:

            return jsonify({

                "success": False,

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        # ----------------------------------------------------
        # ERREUR
        # ----------------------------------------------------

        if not response.ok:

            return jsonify({

                "success": False,

                "error":
                    get_openrouter_error(
                        result
                    )

            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION
        # ----------------------------------------------------

        answer = ""


        choices = result.get(
            "choices",
            []
        )


        if isinstance(
            choices,
            list
        ) and choices:

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

                        answer = content


        if not answer:

            answer = (
                "Je n'ai pas pu générer une réponse."
            )


        return jsonify({

            "success": True,

            "response": answer

        })


    except requests.Timeout:

        return jsonify({

            "success": False,

            "error":
                "Le délai de réponse d'OpenRouter est dépassé."

        }), 504


    except requests.RequestException as error:

        print(
            "OpenRouter request error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success": False,

            "error":
                "Impossible de contacter OpenRouter."

        }), 502


    except Exception as error:

        print(
            "Chat error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success": False,

            "error":
                "Erreur interne du serveur."

        }), 500


# ============================================================
# ANALYSE IMAGE
# ============================================================

@app.route(
    "/api/analyze-image",
    methods=["POST"]
)
def analyze_image():

    try:

        if not OPENROUTER_API_KEY:

            return jsonify({

                "success": False,

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

                "success": False,

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

                "success": False,

                "error":
                    "Image invalide."

            }), 400


        if not image_data.startswith(
            "data:image/"
        ):

            return jsonify({

                "success": False,

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


        response = requests.post(

            OPENROUTER_URL + "/chat/completions",

            headers=openrouter_headers(),

            json=payload,

            timeout=120

        )


        try:

            result = response.json()

        except Exception:

            return jsonify({

                "success": False,

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        if not response.ok:

            return jsonify({

                "success": False,

                "error":
                    get_openrouter_error(
                        result
                    )

            }), response.status_code


        answer = ""


        choices = result.get(
            "choices",
            []
        )


        if isinstance(
            choices,
            list
        ) and choices:

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

                        answer = content


        if not answer:

            answer = (
                "Je n'ai pas pu analyser cette image."
            )


        return jsonify({

            "success": True,

            "response": answer

        })


    except requests.Timeout:

        return jsonify({

            "success": False,

            "error":
                "Le délai d'analyse de l'image est dépassé."

        }), 504


    except requests.RequestException as error:

        print(
            "Vision request error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success": False,

            "error":
                "Impossible de contacter OpenRouter."

        }), 502


    except Exception as error:

        print(
            "Image analysis error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success": False,

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

        if not OPENROUTER_API_KEY:

            return jsonify({

                "success": False,

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

                "success": False,

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

                "success": False,

                "error":
                    "Le prompt doit être du texte."

            }), 400


        prompt = prompt.strip()


        if not prompt:

            return jsonify({

                "success": False,

                "error":
                    "Décris l'image que tu veux créer."

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

            "model": IMAGE_MODEL,

            "prompt": prompt,

            "resolution": resolution,

            "aspect_ratio": aspect_ratio,

            "quality": quality,

            "output_format": output_format

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

            payload["input_references"] = [

                {

                    "type": "image_url",

                    "image_url": {

                        "url":
                            reference_image

                    }

                }

            ]


        # ----------------------------------------------------
        # REQUÊTE
        # ----------------------------------------------------

        response = requests.post(

            OPENROUTER_URL + "/images",

            headers=openrouter_headers(),

            json=payload,

            timeout=300

        )


        try:

            result = response.json()

        except Exception:

            return jsonify({

                "success": False,

                "error":
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


        if not response.ok:

            return jsonify({

                "success": False,

                "error":
                    get_openrouter_error(
                        result
                    )

            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION DES IMAGES
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


                if isinstance(
                    b64,
                    str
                ) and b64:

                    media_type = image.get(
                        "media_type",
                        "image/png"
                    )


                    images.append({

                        "data":
                            "data:" +
                            media_type +
                            ";base64," +
                            b64,

                        "media_type":
                            media_type

                    })


        if not images:

            return jsonify({

                "success": False,

                "error":
                    "OpenRouter n'a renvoyé aucune image."

            }), 502


        # ----------------------------------------------------
        # UTILISATION / COÛT
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

            "success": True,

            "images": images,

            "usage": {

                "cost": cost

            },

            "model": IMAGE_MODEL

        })


    except requests.Timeout:

        return jsonify({

            "success": False,

            "error":
                "La génération de l'image prend trop de temps."

        }), 504


    except requests.RequestException as error:

        print(
            "Image request error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success": False,

            "error":
                "Impossible de contacter le service d'images."

        }), 502


    except Exception as error:

        print(
            "Generate image error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success": False,

            "error":
                "Erreur interne pendant la génération."

        }), 500


# ============================================================
# LANCEMENT LOCAL
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



