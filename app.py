import os
import traceback
import requests

from flask import Flask, render_template, request, jsonify


# ============================================================
# MESSIE IA
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

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1"
)

CHAT_MODEL = os.environ.get(
    "OPENROUTER_CHAT_MODEL",
    "openai/gpt-4o-mini"
)

VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL",
    "google/gemini-2.5-flash"
)


# ============================================================
# HEADERS OPENROUTER
# ============================================================

def openrouter_headers():

    return {
        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "X-Title":
            "Messie IA"
    }


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route("/", methods=["GET"])
def index():

    try:

        return render_template(
            "index.html"
        )

    except Exception as error:

        print(
            "\n========== ERREUR INDEX =========="
        )

        traceback.print_exc()

        print(
            "==================================\n"
        )

        return jsonify({

            "success": False,

            "error":
                "Impossible de charger index.html.",

            "details":
                str(error)

        }), 500


# ============================================================
# DIAGNOSTIC DES FICHIERS
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

            "success": True,

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
                ),

            "index_path":
                index_file

        })


    except Exception as error:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error":
                str(error)

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health", methods=["GET"])
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
# TEST API
# ============================================================

@app.route("/api/test", methods=["GET"])
def api_test():

    return jsonify({

        "success":
            True,

        "message":
            "Messie IA fonctionne correctement."

    })


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

                "success":
                    False,

                "error":
                    (
                        "OPENROUTER_API_KEY "
                        "n'est pas configurée "
                        "dans Render."
                    )

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

                "success":
                    False,

                "error":
                    "Réponse invalide d'OpenRouter."

            }), 502


        if not response.ok:

            return jsonify({

                "success":
                    False,

                "error":
                    get_openrouter_error(
                        result
                    )

            }), response.status_code


        choices =
            result.get(
                "choices",
                []
            )


        answer = ""


        if (
            isinstance(
                choices,
                list
            )
            and
            choices
        ):

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

            "success":
                True,

            "response":
                answer

        })


    except requests.Timeout:

        return jsonify({

            "success":
                False,

            "error":
                "Le délai de réponse est dépassé."

        }), 504


    except requests.RequestException as error:

        print(
            "OpenRouter request error:",
            error
        )


        return jsonify({

            "success":
                False,

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

            "success":
                False,

            "error":
                "Erreur interne du serveur."

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

        if not OPENROUTER_API_KEY:

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

                "success":
                    False,

                "error":
                    "Réponse invalide d'OpenRouter."

            }), 502


        if not response.ok:

            return jsonify({

                "success":
                    False,

                "error":
                    get_openrouter_error(
                        result
                    )

            }), response.status_code


        choices =
            result.get(
                "choices",
                []
            )


        answer = ""


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


        return jsonify({

            "success":
                True,

            "response":
                answer

        })


    except requests.Timeout:

        return jsonify({

            "success":
                False,

            "error":
                "Le délai d'analyse est dépassé."

        }), 504


    except requests.RequestException as error:

        print(
            "Vision request error:",
            error
        )


        return jsonify({

            "success":
                False,

            "error":
                "Impossible de contacter OpenRouter."

        }), 502


    except Exception as error:

        print(
            "Analyze image error:",
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
# ERREUR GLOBALE
# ============================================================

@app.errorhandler(Exception)
def global_error(error):

    print(
        "\n================================"
    )

    print(
        "ERREUR GLOBALE MESSIE IA"
    )

    print(
        "================================"
    )


    traceback.print_exc()


    print(
        "================================\n"
    )


    return jsonify({

        "success":
            False,

        "error":
            str(error),

        "type":
            type(error).__name__

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


    print(
        "================================"
    )

    print(
        "MESSIE IA"
    )

    print(
        "PORT:",
        port
    )

    print(
        "OPENROUTER:",
        bool(
            OPENROUTER_API_KEY
        )
    )

    print(
        "================================"
    )


    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )



