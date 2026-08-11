import os
import requests

from flask import Flask, render_template, request, jsonify


# ============================================================
# APPLICATION FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIGURATION OPENROUTER
# ============================================================

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1"


# ============================================================
# MODÈLES
# ============================================================

# Modèle pour les conversations normales
CHAT_MODEL = os.environ.get(
    "OPENROUTER_CHAT_MODEL",
    "openai/gpt-4o-mini"
)


# Modèle pour analyser les images
VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL",
    "google/gemini-2.5-flash"
)


# Modèle pour générer et modifier les images
IMAGE_MODEL = os.environ.get(
    "OPENROUTER_IMAGE_MODEL",
    "google/gemini-2.5-flash-image"
)


# ============================================================
# VÉRIFICATION DE LA CLÉ API
# ============================================================

def check_api_key():
    return bool(OPENROUTER_API_KEY)


# ============================================================
# HEADERS OPENROUTER
# ============================================================

def openrouter_headers():

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "Messie IA"
    }

    # HTTP-Referer est facultatif sur OpenRouter.
    # request.host_url peut ne pas être disponible dans certains
    # contextes de test, donc on le protège.
    try:
        headers["HTTP-Referer"] = request.host_url.rstrip("/")
    except Exception:
        pass

    return headers


# ============================================================
# EXTRACTION DES ERREURS OPENROUTER
# ============================================================

def get_openrouter_error(data):

    if not isinstance(data, dict):
        return "Erreur OpenRouter."

    error = data.get("error")

    if isinstance(error, dict):

        message = error.get("message")

        if isinstance(message, str) and message.strip():
            return message

        code = error.get("code")

        if code:
            return f"Erreur OpenRouter (code {code})."

    if isinstance(error, str) and error.strip():
        return error

    return "Erreur OpenRouter."


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
                    "sur le serveur."
                )
            }), 500


        # ----------------------------------------------------
        # DONNÉES
        # ----------------------------------------------------

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "error": "Données invalides."
            }), 400


        message = data.get("message", "")

        history = data.get("history", [])


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
                    "Pour le code, donne des exemples complets "
                    "et faciles à comprendre."
                )
            }

        ]


        # ----------------------------------------------------
        # HISTORIQUE
        # ----------------------------------------------------

        if isinstance(history, list):

            # On limite l'historique pour éviter des requêtes
            # inutilement énormes.
            history = history[-30:]

            for item in history:

                if not isinstance(item, dict):
                    continue


                role = item.get("role")

                content = item.get("content")


                if role not in ("user", "assistant"):
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
        # REQUÊTE OPENROUTER
        # ----------------------------------------------------

        payload = {
            "model": CHAT_MODEL,
            "messages": messages,
            "temperature": 0.7
        }


        response = requests.post(
            f"{OPENROUTER_URL}/chat/completions",
            headers=openrouter_headers(),
            json=payload,
            timeout=120
        )


        # ----------------------------------------------------
        # JSON
        # ----------------------------------------------------

        try:
            result = response.json()

        except ValueError:

            return jsonify({
                "error": (
                    "OpenRouter a renvoyé une réponse "
                    "qui n'est pas un JSON valide."
                )
            }), 502


        # ----------------------------------------------------
        # ERREUR OPENROUTER
        # ----------------------------------------------------

        if not response.ok:

            return jsonify({
                "error": get_openrouter_error(result)
            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION DE LA RÉPONSE
        # ----------------------------------------------------

        answer = ""

        choices = result.get("choices", [])


        if choices and isinstance(choices[0], dict):

            message_data = choices[0].get("message", {})


            if isinstance(message_data, dict):

                content = message_data.get("content", "")


                if isinstance(content, str):

                    answer = content.strip()


        if not answer:

            answer = "Je n'ai pas pu générer une réponse."


        return jsonify({
            "response": answer
        })


    except requests.Timeout:

        return jsonify({
            "error": (
                "Le délai de réponse d'OpenRouter "
                "a été dépassé."
            )
        }), 504


    except requests.RequestException as error:

        print(
            "OpenRouter chat request error:",
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

@app.route("/api/analyze-image", methods=["POST"])
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

        data = request.get_json(silent=True)


        if not data:

            return jsonify({
                "error": "Données invalides."
            }), 400


        image_data = data.get("image", "")


        prompt = data.get(
            "prompt",
            "Décris cette image en détail."
        )


        if not isinstance(image_data, str):

            return jsonify({
                "error": "Image invalide."
            }), 400


        if not image_data.startswith("data:image/"):

            return jsonify({
                "error": (
                    "Format d'image non supporté. "
                    "Utilise une image JPG, PNG ou WEBP."
                )
            }), 400


        if not isinstance(prompt, str):

            prompt = "Décris cette image en détail."


        prompt = prompt.strip()


        if not prompt:

            prompt = "Décris cette image en détail."


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
        # OPENROUTER
        # ----------------------------------------------------

        response = requests.post(

            f"{OPENROUTER_URL}/chat/completions",

            headers=openrouter_headers(),

            json=payload,

            timeout=120
        )


        try:

            result = response.json()

        except ValueError:

            return jsonify({
                "error": (
                    "Réponse invalide d'OpenRouter."
                )
            }), 502


        if not response.ok:

            return jsonify({
                "error": get_openrouter_error(result)
            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION
        # ----------------------------------------------------

        answer = ""

        choices = result.get("choices", [])


        if choices and isinstance(choices[0], dict):

            message_data = choices[0].get(
                "message",
                {}
            )


            if isinstance(message_data, dict):

                content = message_data.get(
                    "content",
                    ""
                )


                if isinstance(content, str):

                    answer = content.strip()


        if not answer:

            answer = (
                "Je n'ai pas pu analyser cette image."
            )


        return jsonify({
            "response": answer
        })


    except requests.Timeout:

        return jsonify({
            "error": (
                "L'analyse de l'image prend "
                "trop de temps. Réessaie."
            )
        }), 504


    except requests.RequestException as error:

        print(
            "Image analysis request error:",
            error
        )

        return jsonify({
            "error": (
                "Impossible de contacter OpenRouter."
            )
        }), 502


    except Exception as error:

        print(
            "Image analysis error:",
            error
        )

        return jsonify({
            "error": (
                "Erreur pendant l'analyse de l'image."
            )
        }), 500


# ============================================================
# GÉNÉRATION / MODIFICATION D'IMAGE
# ============================================================

@app.route("/api/generate-image", methods=["POST"])
def generate_image():

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

        data = request.get_json(silent=True)


        if not data:

            return jsonify({
                "error": "Données invalides."
            }), 400


        # ----------------------------------------------------
        # PROMPT
        # ----------------------------------------------------

        prompt = data.get("prompt", "")


        if not isinstance(prompt, str):

            return jsonify({
                "error": "Le prompt doit être du texte."
            }), 400


        prompt = prompt.strip()


        if not prompt:

            return jsonify({
                "error": (
                    "Décris l'image que tu veux créer "
                    "ou modifier."
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
        # VALIDATION ASPECT RATIO
        # ----------------------------------------------------

        allowed_ratios = {

            "1:1",
            "16:9",
            "9:16",
            "4:3",
            "3:4",
            "2:3",
            "3:2"

        }


        if aspect_ratio not in allowed_ratios:

            aspect_ratio = "1:1"


        # ----------------------------------------------------
        # VALIDATION RÉSOLUTION
        # ----------------------------------------------------

        allowed_resolutions = {

            "512",
            "1K",
            "2K",
            "4K"

        }


        if resolution not in allowed_resolutions:

            resolution = "1K"


        # ----------------------------------------------------
        # VALIDATION QUALITÉ
        # ----------------------------------------------------

        allowed_quality = {

            "auto",
            "low",
            "medium",
            "high"

        }


        if quality not in allowed_quality:

            quality = "auto"


        # ----------------------------------------------------
        # VALIDATION FORMAT
        # ----------------------------------------------------

        allowed_formats = {

            "png",
            "jpeg",
            "webp"

        }


        if output_format not in allowed_formats:

            output_format = "png"


        # ----------------------------------------------------
        # NOMBRE D'IMAGES
        # ----------------------------------------------------

        try:

            n = int(n)

        except (TypeError, ValueError):

            n = 1


        n = max(
            1,
            min(n, 4)
        )


        # ----------------------------------------------------
        # PAYLOAD OPENROUTER IMAGE API
        # ----------------------------------------------------

        payload = {

            "model": IMAGE_MODEL,

            "prompt": prompt,

            "n": n,

            "resolution": resolution,

            "aspect_ratio": aspect_ratio,

            "quality": quality,

            "output_format": output_format

        }


        # ----------------------------------------------------
        # IMAGE DE RÉFÉRENCE
        #
        # Permet de modifier une image existante.
        # ----------------------------------------------------

        reference_image = data.get(
            "reference_image"
        )


        if (
            isinstance(reference_image, str)
            and reference_image.startswith("data:image/")
        ):

            payload["input_references"] = [

                {
                    "type": "image_url",

                    "image_url": {
                        "url": reference_image
                    }
                }

            ]


        # ----------------------------------------------------
        # APPEL OPENROUTER
        # ----------------------------------------------------

        print(
            "Image generation:",
            IMAGE_MODEL
        )


        response = requests.post(

            f"{OPENROUTER_URL}/images",

            headers=openrouter_headers(),

            json=payload,

            timeout=300
        )


        # ----------------------------------------------------
        # LECTURE JSON
        # ----------------------------------------------------

        try:

            result = response.json()

        except ValueError:

            return jsonify({
                "error": (
                    "OpenRouter a renvoyé une réponse "
                    "invalide."
                )
            }), 502


        # ----------------------------------------------------
        # ERREUR OPENROUTER
        # ----------------------------------------------------

        if not response.ok:

            error_message = get_openrouter_error(
                result
            )

            print(
                "OpenRouter image error:",
                error_message
            )

            return jsonify({
                "error": error_message
            }), response.status_code


        # ----------------------------------------------------
        # EXTRACTION DES IMAGES
        # ----------------------------------------------------

        images = []


        image_data_list = result.get(
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


            if not b64.strip():

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


            images.append({

                "data":
                    f"data:{media_type};base64,{b64}",

                "media_type":
                    media_type

            })


        # ----------------------------------------------------
        # AUCUNE IMAGE
        # ----------------------------------------------------

        if not images:

            return jsonify({

                "error": (
                    "OpenRouter n'a renvoyé aucune image."
                ),

                "details": result

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
        # RÉPONSE
        # ----------------------------------------------------

        return jsonify({

            "images": images,

            "usage": {
                "cost": cost
            },

            "model":
                result.get(
                    "model",
                    IMAGE_MODEL
                )

        })


    except requests.Timeout:

        return jsonify({

            "error": (
                "La génération de l'image prend "
                "trop de temps. Réessaie."
            )

        }), 504


    except requests.RequestException as error:

        print(
            "Image request error:",
            error
        )

        return jsonify({

            "error": (
                "Impossible de contacter "
                "le service d'images OpenRouter."
            )

        }), 502


    except Exception as error:

        print(
            "Generate image error:",
            error
        )

        return jsonify({

            "error": (
                "Erreur interne pendant "
                "la génération de l'image."
            )

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "ok",

        "app": "Messie IA",

        "openrouter": bool(
            OPENROUTER_API_KEY
        ),

        "chat_model": CHAT_MODEL,

        "vision_model": VISION_MODEL,

        "image_model": IMAGE_MODEL

    })


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
