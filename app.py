import os
import sqlite3
import traceback
from functools import wraps

import requests

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# ============================================================
# MESSIE IA
# ============================================================

app = Flask(
    __name__,
    template_folder="templates"
)

app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024


# ============================================================
# SÉCURITÉ / SESSION
# ============================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "messie-ia-change-this-secret-key"
)


# ============================================================
# OPENROUTER
# ============================================================

OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY"
)

OPENROUTER_URL = "https://openrouter.ai/api/v1"


CHAT_MODEL = os.environ.get(
    "OPENROUTER_CHAT_MODEL",
    "openrouter/free"
)


VISION_MODEL = os.environ.get(
    "OPENROUTER_VISION_MODEL",
    "google/gemini-3-flash-preview"
)


IMAGE_MODEL = os.environ.get(
    "OPENROUTER_IMAGE_MODEL",
    "google/gemini-2.5-flash-image"
)


# ============================================================
# BASE DE DONNÉES
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE = os.path.join(
    BASE_DIR,
    "messie.db"
)


def get_db():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_db()

    cursor = connection.cursor()


    # --------------------------------------------------------
    # UTILISATEURS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            password TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # --------------------------------------------------------
    # CONVERSATIONS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            title TEXT NOT NULL DEFAULT 'Nouvelle conversation',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)


    # --------------------------------------------------------
    # MESSAGES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            conversation_id INTEGER NOT NULL,

            role TEXT NOT NULL,

            content TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
        )
    """)


    connection.commit()

    connection.close()


# Initialisation
init_database()


# ============================================================
# SYSTÈME MESSIE IA
# ============================================================

SYSTEM_PROMPT = """
Tu es Messie IA, l'assistant officiel de l'application Messie IA.

Tu dois toujours te présenter comme « Messie IA » lorsque l'utilisateur
te demande qui tu es.

Messie IA est une application créée par Messie Bernard.

Lorsque l'utilisateur demande « Qui t'a créé ? », « Qui a créé Messie IA ? »
ou une question similaire, réponds clairement que Messie IA a été créé par
Messie Bernard.

Ne prétends pas être Nemotron, ChatGPT, Claude, Gemini, NVIDIA, OpenAI,
OpenRouter ou un autre assistant ou fournisseur lorsque l'utilisateur
demande qui tu es.

Tu peux utiliser un modèle d'intelligence artificielle fourni par un
service externe pour générer tes réponses, mais ce modèle est simplement
le moteur utilisé par Messie IA. Tu dois continuer à te présenter comme
Messie IA.

Tu réponds en français par défaut.

Si l'utilisateur demande une autre langue, utilise cette langue.

Donne des réponses claires, utiles, naturelles et faciles à comprendre.

Pour les questions complexes, explique progressivement.

Ne prétends jamais avoir effectué une action que tu n'as pas réellement
effectuée.

Si tu n'es pas certain d'une information, indique-le clairement.

Tu es l'assistant officiel de l'application Messie IA.
""".strip()




# ============================================================
# OPENROUTER
# ============================================================

def check_api_key():

    return bool(
        OPENROUTER_API_KEY
        and OPENROUTER_API_KEY.strip()
    )


def openrouter_headers():

    headers = {

        "Authorization":
            "Bearer " + OPENROUTER_API_KEY,

        "Content-Type":
            "application/json",

        "X-Title":
            "Messie IA"
    }


    render_url = os.environ.get(
        "RENDER_EXTERNAL_URL"
    )


    if render_url:

        headers["HTTP-Referer"] = render_url


    return headers


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


        if (
            isinstance(
                message,
                str
            )
            and
            message.strip()
        ):

            return message.strip()


    if (
        isinstance(
            error,
            str
        )
        and
        error.strip()
    ):

        return error.strip()


    return "Erreur OpenRouter."


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


        return "\n".join(parts).strip()


    return ""


# ============================================================
# AUTHENTIFICATION
# ============================================================

def current_user():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return None


    connection = get_db()


    user = connection.execute(
        """
        SELECT id, name, email, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()


    connection.close()


    return user


def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not current_user():

            return jsonify({

                "success":
                    False,

                "error":
                    "Connexion requise."

            }), 401


        return function(
            *args,
            **kwargs
        )


    return wrapper


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
            "========== ERREUR INDEX =========="
        )

        traceback.print_exc()

        print(
            "=================================="
        )


        return jsonify({

            "success":
                False,

            "error":
                "Impossible de charger index.html.",

            "details":
                str(error)

        }), 500


# ============================================================
# AUTH - INSCRIPTION
# ============================================================

@app.route(
    "/api/register",
    methods=["POST"]
)
def register():

    try:

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


        name = str(
            data.get(
                "name",
                ""
            )
        ).strip()


        email = str(
            data.get(
                "email",
                ""
            )
        ).strip().lower()


        password = str(
            data.get(
                "password",
                ""
            )
        )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not name:

            return jsonify({

                "success":
                    False,

                "error":
                    "Entre ton nom."

            }), 400


        if len(name) > 80:

            return jsonify({

                "success":
                    False,

                "error":
                    "Le nom est trop long."

            }), 400


        if "@" not in email:

            return jsonify({

                "success":
                    False,

                "error":
                    "Adresse email invalide."

            }), 400


        if len(email) > 200:

            return jsonify({

                "success":
                    False,

                "error":
                    "Adresse email trop longue."

            }), 400


        if len(password) < 6:

            return jsonify({

                "success":
                    False,

                "error":
                    "Le mot de passe doit contenir au moins 6 caractères."

            }), 400


        if len(password) > 200:

            return jsonify({

                "success":
                    False,

                "error":
                    "Mot de passe trop long."

            }), 400


        # ----------------------------------------------------
        # CRÉATION
        # ----------------------------------------------------

        password_hash = generate_password_hash(
            password
        )


        connection = get_db()


        try:

            cursor = connection.execute(
                """
                INSERT INTO users
                (name, email, password)
                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    password_hash
                )
            )


            connection.commit()


            user_id = cursor.lastrowid


        except sqlite3.IntegrityError:

            connection.close()


            return jsonify({

                "success":
                    False,

                "error":
                    "Un compte avec cet email existe déjà."

            }), 409


        connection.close()


        session["user_id"] = user_id


        return jsonify({

            "success":
                True,

            "message":
                "Compte créé avec succès.",

            "user": {

                "id":
                    user_id,

                "name":
                    name,

                "email":
                    email

            }

        })


    except Exception as error:

        print(
            "REGISTER error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
                "Impossible de créer le compte."

        }), 500


# ============================================================
# AUTH - CONNEXION
# ============================================================

@app.route(
    "/api/login",
    methods=["POST"]
)
def login():

    try:

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


        email = str(
            data.get(
                "email",
                ""
            )
        ).strip().lower()


        password = str(
            data.get(
                "password",
                ""
            )
        )


        connection = get_db()


        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        connection.close()


        if not user:

            return jsonify({

                "success":
                    False,

                "error":
                    "Email ou mot de passe incorrect."

            }), 401


        if not check_password_hash(
            user["password"],
            password
        ):

            return jsonify({

                "success":
                    False,

                "error":
                    "Email ou mot de passe incorrect."

            }), 401


        session.clear()


        session["user_id"] = user["id"]


        return jsonify({

            "success":
                True,

            "message":
                "Connexion réussie.",

            "user": {

                "id":
                    user["id"],

                "name":
                    user["name"],

                "email":
                    user["email"]

            }

        })


    except Exception as error:

        print(
            "LOGIN error:",
            error
        )

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
                "Impossible de se connecter."

        }), 500


# ============================================================
# AUTH - DÉCONNEXION
# ============================================================

@app.route(
    "/api/logout",
    methods=["POST"]
)
def logout():

    session.clear()


    return jsonify({

        "success":
            True,

        "message":
            "Déconnexion réussie."

    })


# ============================================================
# AUTH - UTILISATEUR ACTUEL
# ============================================================

@app.route(
    "/api/me",
    methods=["GET"]
)
def me():

    user = current_user()


    if not user:

        return jsonify({

            "success":
                True,

            "logged_in":
                False

        })


    return jsonify({

        "success":
            True,

        "logged_in":
            True,

        "user": {

            "id":
                user["id"],

            "name":
                user["name"],

            "email":
                user["email"],

            "created_at":
                user["created_at"]

        }

    })


# ============================================================
# CONVERSATIONS
# ============================================================

@app.route(
    "/api/conversations",
    methods=["GET"]
)
@login_required
def conversations():

    user = current_user()


    connection = get_db()


    rows = connection.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (user["id"],)
    ).fetchall()


    connection.close()


    result = []


    for row in rows:

        result.append({

            "id":
                row["id"],

            "title":
                row["title"],

            "created_at":
                row["created_at"],

            "updated_at":
                row["updated_at"]

        })


    return jsonify({

        "success":
            True,

        "conversations":
            result

    })


# ============================================================
# CRÉER CONVERSATION
# ============================================================

@app.route(
    "/api/conversations",
    methods=["POST"]
)
@login_required
def create_conversation():

    user = current_user()


    data = request.get_json(
        silent=True
    )


    title = "Nouvelle conversation"


    if isinstance(
        data,
        dict
    ):

        supplied_title = data.get(
            "title"
        )


        if isinstance(
            supplied_title,
            str
        ):

            supplied_title = (
                supplied_title.strip()
            )


            if supplied_title:

                title = supplied_title[:100]


    connection = get_db()


    cursor = connection.execute(
        """
        INSERT INTO conversations
        (user_id, title)
        VALUES (?, ?)
        """,
        (
            user["id"],
            title
        )
    )


    connection.commit()


    conversation_id = cursor.lastrowid


    connection.close()


    return jsonify({

        "success":
            True,

        "conversation": {

            "id":
                conversation_id,

            "title":
                title

        }

    })


# ============================================================
# CHARGER UNE CONVERSATION
# ============================================================

@app.route(
    "/api/conversations/<int:conversation_id>",
    methods=["GET"]
)
@login_required
def get_conversation(
    conversation_id
):

    user = current_user()


    connection = get_db()


    conversation = connection.execute(
        """
        SELECT *
        FROM conversations
        WHERE id = ?
        AND user_id = ?
        """,
        (
            conversation_id,
            user["id"]
        )
    ).fetchone()


    if not conversation:

        connection.close()


        return jsonify({

            "success":
                False,

            "error":
                "Conversation introuvable."

        }), 404


    messages = connection.execute(
        """
        SELECT id, role, content, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,)
    ).fetchall()


    connection.close()


    return jsonify({

        "success":
            True,

        "conversation": {

            "id":
                conversation["id"],

            "title":
                conversation["title"],

            "messages": [

                {

                    "id":
                        row["id"],

                    "role":
                        row["role"],

                    "content":
                        row["content"],

                    "created_at":
                        row["created_at"]

                }

                for row in messages

            ]

        }

    })


# ============================================================
# SUPPRIMER CONVERSATION
# ============================================================

@app.route(
    "/api/conversations/<int:conversation_id>",
    methods=["DELETE"]
)
@login_required
def delete_conversation(
    conversation_id
):

    user = current_user()


    connection = get_db()


    conversation = connection.execute(
        """
        SELECT id
        FROM conversations
        WHERE id = ?
        AND user_id = ?
        """,
        (
            conversation_id,
            user["id"]
        )
    ).fetchone()


    if not conversation:

        connection.close()


        return jsonify({

            "success":
                False,

            "error":
                "Conversation introuvable."

        }), 404


    connection.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )


    connection.execute(
        """
        DELETE FROM conversations
        WHERE id = ?
        AND user_id = ?
        """,
        (
            conversation_id,
            user["id"]
        )
    )


    connection.commit()

    connection.close()


    return jsonify({

        "success":
            True

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

        if not check_api_key():

            return jsonify({

                "success":
                    False,

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

                "success":
                    False,

                "error":
                    "Données invalides."

            }), 400


        message = data.get(
            "message",
            ""
        )


        conversation_id = data.get(
            "conversation_id"
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


        if len(message) > 20000:

            return jsonify({

                "success":
                    False,

                "error":
                    "Le message est trop long."

            }), 400


        # ----------------------------------------------------
        # HISTORIQUE
        # ----------------------------------------------------

        messages = [

            {

                "role":
                    "system",

                "content":
                    SYSTEM_PROMPT

            }

        ]


        # Si un utilisateur est connecté et qu'une conversation
        # existe, on récupère son historique depuis SQLite.

        user = current_user()


        if (
            user
            and
            conversation_id
        ):

            try:

                conversation_id = int(
                    conversation_id
                )


                connection = get_db()


                conversation = connection.execute(
                    """
                    SELECT id
                    FROM conversations
                    WHERE id = ?
                    AND user_id = ?
                    """,
                    (
                        conversation_id,
                        user["id"]
                    )
                ).fetchone()


                if conversation:

                    database_messages = connection.execute(
                        """
                        SELECT role, content
                        FROM messages
                        WHERE conversation_id = ?
                        ORDER BY id DESC
                        LIMIT 20
                        """,
                        (conversation_id,)
                    ).fetchall()


                    database_messages = list(
                        reversed(
                            database_messages
                        )
                    )


                    for item in database_messages:

                        messages.append({

                            "role":
                                item["role"],

                            "content":
                                item["content"]

                        })


                connection.close()


            except Exception:

                traceback.print_exc()


        # ----------------------------------------------------
        # HISTORIQUE ENVOYÉ PAR L'INTERFACE
        # ----------------------------------------------------

        if len(messages) == 1:

            if isinstance(
                history,
                list
            ):

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
                            content[:20000]

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
        # OPENROUTER
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
                    "OpenRouter a renvoyé une réponse invalide."

            }), 502


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


        answer = extract_chat_answer(
            result
        )


        if not answer:

            answer = (
                "Je n'ai pas pu générer une réponse."
            )


        # ----------------------------------------------------
        # SAUVEGARDE HISTORIQUE
        # ----------------------------------------------------

        if user:

            try:

                connection = get_db()


                # Si aucune conversation n'existe,
                # on en crée une automatiquement.

                if not conversation_id:

                    title = message[:60]


                    cursor = connection.execute(
                        """
                        INSERT INTO conversations
                        (user_id, title)
                        VALUES (?, ?)
                        """,
                        (
                            user["id"],
                            title
                        )
                    )


                    conversation_id = cursor.lastrowid


                else:

                    conversation = connection.execute(
                        """
                        SELECT id
                        FROM conversations
                        WHERE id = ?
                        AND user_id = ?
                        """,
                        (
                            int(conversation_id),
                            user["id"]
                        )
                    ).fetchone()


                    if not conversation:

                        conversation_id = None


                if conversation_id:

                    connection.execute(
                        """
                        INSERT INTO messages
                        (conversation_id, role, content)
                        VALUES (?, ?, ?)
                        """,
                        (
                            conversation_id,
                            "user",
                            message
                        )
                    )


                    connection.execute(
                        """
                        INSERT INTO messages
                        (conversation_id, role, content)
                        VALUES (?, ?, ?)
                        """,
                        (
                            conversation_id,
                            "assistant",
                            answer
                        )
                    )


                    connection.execute(
                        """
                        UPDATE conversations
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (conversation_id,)
                    )


                    connection.commit()


                connection.close()


            except Exception:

                print(
                    "Erreur sauvegarde historique"
                )

                traceback.print_exc()


        return jsonify({

            "success":
                True,

            "response":
                answer,

            "model":
                result.get(
                    "model",
                    CHAT_MODEL
                ),

            "conversation_id":
                conversation_id

        })


    except requests.Timeout:

        return jsonify({

            "success":
                False,

            "error":
                "Le délai de réponse d'OpenRouter est dépassé."

        }), 504


    except requests.RequestException as error:

        print(
            "CHAT request error:",
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


        if not isinstance(
            prompt,
            str
        ):

            prompt = (
                "Décris cette image en détail."
            )


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

            return jsonify({

                "success":
                    False,

                "error":
                    get_openrouter_error(
                        result
                    )

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
# GÉNÉRATION IMAGE
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


        if aspect_ratio not in {
            "1:1",
            "16:9",
            "9:16",
            "4:3",
            "3:4"
        }:

            aspect_ratio = "1:1"


        if resolution not in {
            "512",
            "1K",
            "2K",
            "4K"
        }:

            resolution = "1K"


        if quality not in {
            "auto",
            "low",
            "medium",
            "high"
        }:

            quality = "auto"


        if output_format not in {
            "png",
            "jpeg",
            "webp"
        }:

            output_format = "png"


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

            return jsonify({

                "success":
                    False,

                "error":
                    get_openrouter_error(
                        result
                    )

            }), response.status_code


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


            b64 = image.get(
                "b64_json"
            )


            if not b64:

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


        if not images:

            return jsonify({

                "success":
                    False,

                "error":
                    "OpenRouter n'a renvoyé aucune image."

            }), 502


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
                "La génération de l'image prend trop de temps."

        }), 504


    except requests.RequestException:

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
# DIAGNOSTIC
# ============================================================

@app.route(
    "/debug-files"
)
def debug_files():

    try:

        base = os.path.dirname(
            os.path.abspath(__file__)
        )


        templates = os.path.join(
            base,
            "templates"
        )


        index = os.path.join(
            templates,
            "index.html"
        )


        return jsonify({

            "success":
                True,

            "app":
                "Messie IA",

            "base_directory":
                base,

            "files":
                os.listdir(base),

            "templates_exists":
                os.path.isdir(templates),

            "templates_files":
                (
                    os.listdir(templates)
                    if os.path.isdir(templates)
                    else []
                ),

            "index_exists":
                os.path.isfile(index),

            "database_exists":
                os.path.isfile(DATABASE)

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
# ERREURS
# ============================================================

@app.errorhandler(413)
def too_large(error):

    return jsonify({

        "success":
            False,

        "error":
            "La requête est trop volumineuse."

    }), 413


@app.errorhandler(404)
def not_found(error):

    return jsonify({

        "success":
            False,

        "error":
            "La route demandée n'existe pas."

    }), 404


@app.errorhandler(500)
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



